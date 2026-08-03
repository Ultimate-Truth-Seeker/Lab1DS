"""
Modelos LSTM para las series de tiempo (Laboratorio 2).

Misma disciplina que models.py: aca solo se ajustan redes y se devuelven sus
resultados. No se imprime, no se escriben archivos y no se conoce el pipeline.

Convenciones que comparte con models.py:
  - recibe la serie YA transformada (log1p) y devuelve el forecast en esa misma
    escala; el expm1 lo aplica el pipeline. Asi no hay doble inversion.
  - devuelve un dict con las mismas 7 claves que models._resultado.

El z-score que se hace aca adentro es distinto: es un requisito de la red (una
LSTM no entrena bien con valores en el orden de 12), no una decision de analisis,
asi que se aplica y se revierte internamente.
"""

from __future__ import annotations

from dataclasses import dataclass, asdict

import numpy as np
import pandas as pd
import torch
import torch.nn as nn

from src import config
from src.models import pronostico_index


@dataclass(frozen=True)
class ConfigLSTM:
    """Una configuracion de red. Es lo unico que hay que agregar para sumar un modelo."""
    nombre: str
    ventana: int
    unidades: int
    capas: int
    dropout: float
    epochs: int = config.LSTM_EPOCHS
    lr: float = config.LSTM_LR


CONFIGS: dict[str, ConfigLSTM] = {
    # Config 1 (Diego): red chica, ventana de un ciclo estacional.
    "lstm_c1": ConfigLSTM(nombre="lstm_c1", ventana=12, unidades=32, capas=1, dropout=0.1),

    # Config 2 (Nelson):
    "lstm_c2": ConfigLSTM(nombre="lstm_c2", ventana=24, unidades=64, capas=2, dropout=0.3),
}


# ---------------------------------------------------------------------------
# escalado
# ---------------------------------------------------------------------------

def _ajustar_escalador(serie: pd.Series) -> tuple[float, float]:
    """Media y desviacion para el z-score. Se ajusta SOLO con lo que la red vera."""
    valores = serie.to_numpy(dtype="float64")
    sd = float(valores.std())
    return float(valores.mean()), (sd if sd > 0 else 1.0)


def _escalar(valores: np.ndarray, media: float, sd: float) -> np.ndarray:
    return (valores - media) / sd


def _desescalar(valores: np.ndarray, media: float, sd: float) -> np.ndarray:
    return valores * sd + media


# ---------------------------------------------------------------------------
# ventaneo
# ---------------------------------------------------------------------------

def _ventanas(valores: np.ndarray, ventana: int) -> tuple[np.ndarray, np.ndarray]:
    """
    Convierte la serie en pares (ventana de N meses -> mes siguiente).

    Con 147 observaciones y ventana 12 salen 135 muestras, que es poquisimo para
    una red neuronal. Es una limitacion del dataset, no del enfoque.
    """
    if len(valores) <= ventana:
        raise ValueError(f"La serie necesita mas de {ventana} observaciones.")

    x = np.stack([valores[i:i + ventana] for i in range(len(valores) - ventana)])
    y = valores[ventana:]
    return x[:, :, None].astype("float32"), y.astype("float32")


# ---------------------------------------------------------------------------
# la red
# ---------------------------------------------------------------------------

class RedLSTM(nn.Module):
    """
    LSTM que lee una ventana de meses y predice el siguiente.

    El dropout va en una capa aparte y no en nn.LSTM a proposito: PyTorch ignora
    el dropout de nn.LSTM cuando num_layers=1 (y avisa con un warning), asi que
    con una sola capa no tendria ningun efecto.
    """

    def __init__(self, unidades: int, capas: int, dropout: float) -> None:
        super().__init__()
        self.lstm = nn.LSTM(input_size=1, hidden_size=unidades,
                            num_layers=capas, batch_first=True)
        self.dropout = nn.Dropout(dropout)
        self.salida = nn.Linear(unidades, 1)

    def forward(self, x: torch.Tensor) -> torch.Tensor:
        secuencia, _ = self.lstm(x)
        return self.salida(self.dropout(secuencia[:, -1])).squeeze(-1)


# ---------------------------------------------------------------------------
# entrenamiento y prediccion
# ---------------------------------------------------------------------------

def _entrenar(red: nn.Module, x: torch.Tensor, y: torch.Tensor,
              epochs: int, lr: float, checkpoints: tuple[int, ...] = ()) -> dict:
    """
    Entrena a full-batch (con ~135 muestras no hace falta un DataLoader).

    Si se pasan 'checkpoints', guarda una copia del estado de la red en esas
    epocas. Sirve para tunear el numero de epocas con UN solo entrenamiento en
    vez de uno por cada valor de la rejilla.
    """
    opt = torch.optim.Adam(red.parameters(), lr=lr)
    perdida = nn.MSELoss()
    historial: list[float] = []
    estados: dict[int, dict] = {}

    for epoca in range(1, epochs + 1):
        red.train()
        opt.zero_grad()
        error = perdida(red(x), y)
        error.backward()
        opt.step()
        historial.append(float(error.item()))

        if epoca in checkpoints:
            estados[epoca] = {k: v.clone() for k, v in red.state_dict().items()}

    return {"historial": historial, "estados": estados}


def _predecir_recursivo(red: nn.Module, ultima_ventana: np.ndarray,
                        horizon: int) -> np.ndarray:
    """
    Predice 'horizon' pasos reinyectando cada prediccion como entrada.

    Es lo comparable con ARIMA, que tambien pronostica de forma recursiva. El
    costo conocido es que el error se acumula y la serie puede converger a un
    punto fijo; eso se mide aparte con diagnostico_aplanamiento().
    """
    red.eval()
    ventana = list(ultima_ventana)
    predicciones = []

    with torch.no_grad():
        for _ in range(horizon):
            entrada = np.array(ventana[-len(ultima_ventana):], dtype="float32")
            valor = float(red(torch.from_numpy(entrada[None, :, None])).item())
            predicciones.append(valor)
            ventana.append(valor)

    return np.array(predicciones)


def _predecir_un_paso(red: nn.Module, x: torch.Tensor) -> np.ndarray:
    """Prediccion a un paso sobre el propio entrenamiento, para sacar residuos."""
    red.eval()
    with torch.no_grad():
        return red(x).numpy()


# ---------------------------------------------------------------------------
# diagnostico
# ---------------------------------------------------------------------------

def diagnostico_aplanamiento(forecast: pd.Series,
                             meses_cola: int = config.LSTM_COLA_APLANAMIENTO,
                             umbral_cv: float = config.LSTM_CV_APLANADO,
                             escala: str = "log1p") -> dict:
    """
    Mide si el pronostico se aplano al final.

    Una prediccion recursiva puede converger a un valor fijo y perder toda la
    estacionalidad. Se reporta como metrica porque es un resultado del modelo,
    no un fallo del codigo.

    Se mide sobre la escala en que trabaja la red (log1p), no en viajeros: el
    coeficiente de variacion es adimensional, asi que el diagnostico vale igual,
    pero 'media_cola' y 'rango_cola' quedan en esa escala. Por eso se declara en
    la clave 'escala' -- reportar esos dos numeros como viajeros seria enganoso.
    """
    cola = forecast.tail(meses_cola)
    media = float(cola.mean())
    sd = float(cola.std(ddof=1)) if len(cola) > 1 else 0.0
    cv = abs(sd / media) if media else float("inf")

    return {
        "meses_cola": int(len(cola)),
        "escala": escala,
        "media_cola": media,
        "sd_cola": sd,
        "cv_cola": cv,
        "rango_cola": float(cola.max() - cola.min()),
        "umbral_cv": umbral_cv,
        "aplanado": bool(cv < umbral_cv),
    }


# ---------------------------------------------------------------------------
# tuneo
# ---------------------------------------------------------------------------

def tunear_epochs(serie: pd.Series, cfg: ConfigLSTM,
                  rejilla: tuple[int, ...] = config.LSTM_REJILLA_EPOCHS,
                  val_meses: int = config.LSTM_VAL_MESES,
                  semilla: int = config.LSTM_SEMILLA) -> dict:
    """
    Elige el numero de epocas validando contra la cola del entrenamiento.

    El conjunto de prueba NO se usa aca: seria fuga de datos y las metricas
    finales dejarian de ser honestas. Se reservan los ultimos 'val_meses' del
    entrenamiento, se entrena con el resto y se pronostica esa cola.

    Limitacion que hay que tener presente al leer el resultado: con 147
    observaciones, esos 12 meses de validacion caen justo en el colapso
    pandemico, asi que el numero de epocas elegido esta sesgado a predecir bien
    una caida.

    El error se mide en la escala transformada (log1p). Es monotono respecto al
    error en viajeros y evita que este modulo dependa de transform.py.
    """
    _fijar_semilla(semilla)

    interno = serie.iloc[:-val_meses]
    validacion = serie.iloc[-val_meses:]

    # el escalador se ajusta solo con el tramo interno: si se ajusta con toda la
    # serie, la validacion se filtra por la media y la desviacion
    media, sd = _ajustar_escalador(interno)
    z = _escalar(interno.to_numpy(dtype="float64"), media, sd)
    x, y = _ventanas(z, cfg.ventana)

    red = RedLSTM(cfg.unidades, cfg.capas, cfg.dropout)
    entreno = _entrenar(red, torch.from_numpy(x), torch.from_numpy(y),
                        epochs=max(rejilla), lr=cfg.lr, checkpoints=tuple(rejilla))

    real = validacion.to_numpy(dtype="float64")
    resultados = []
    for epocas in rejilla:
        red.load_state_dict(entreno["estados"][epocas])
        pred_z = _predecir_recursivo(red, z[-cfg.ventana:], val_meses)
        pred = _desescalar(pred_z, media, sd)
        rmse = float(np.sqrt(np.mean((real - pred) ** 2)))
        resultados.append({"epochs": int(epocas), "rmse_val": rmse})

    mejor = min(resultados, key=lambda r: r["rmse_val"])

    return {
        "hiperparametro": "epochs",
        "rejilla": [int(e) for e in rejilla],
        "criterio": "rmse_validacion",
        "escala_criterio": "log1p",
        "val_meses": int(val_meses),
        "val_inicio": validacion.index.min().strftime("%Y-%m"),
        "val_fin": validacion.index.max().strftime("%Y-%m"),
        "n_muestras_interno": int(len(y)),
        "resultados": resultados,
        "mejor": mejor["epochs"],
        "rmse_val_mejor": mejor["rmse_val"],
        "nota": ("la validacion es la cola del entrenamiento; el conjunto de prueba "
                 "nunca se usa para elegir hiperparametros"),
    }


# ---------------------------------------------------------------------------
# API publica
# ---------------------------------------------------------------------------

def _fijar_semilla(semilla: int) -> None:
    """
    Reproducibilidad, que el enunciado pide de forma explicita.

    Va dentro de las funciones y no a nivel de modulo: importar lstm.py no
    deberia cambiarle el estado aleatorio a nadie mas. El hilo unico es para que
    la reduccion en CPU sea determinista.
    """
    torch.manual_seed(semilla)
    np.random.seed(semilla)
    torch.set_num_threads(1)


def ajustar_lstm(serie: pd.Series, horizon: int, cfg: ConfigLSTM,
                 semilla: int = config.LSTM_SEMILLA,
                 epochs_override: int | None = None,
                 tuneo: dict | None = None) -> dict:
    """
    Ajusta una LSTM y pronostica 'horizon' meses de forma recursiva.

    Devuelve las mismas 7 claves que models._resultado, para que el pipeline lo
    trate igual que a cualquier modelo del laboratorio anterior. aic y bic van en
    None porque una red no se estima por maxima verosimilitud; las metricas
    propias (perdida, aplanamiento, tuneo) viajan en 'parametros'.
    """
    _fijar_semilla(semilla)
    epochs = epochs_override or cfg.epochs

    media, sd = _ajustar_escalador(serie)
    z = _escalar(serie.to_numpy(dtype="float64"), media, sd)
    x, y = _ventanas(z, cfg.ventana)
    xt, yt = torch.from_numpy(x), torch.from_numpy(y)

    red = RedLSTM(cfg.unidades, cfg.capas, cfg.dropout)
    entreno = _entrenar(red, xt, yt, epochs=epochs, lr=cfg.lr)

    # pronostico recursivo, de vuelta a la escala de la serie recibida
    pred = _desescalar(_predecir_recursivo(red, z[-cfg.ventana:], horizon), media, sd)
    forecast = pd.Series(pred, index=pronostico_index(serie, horizon), name="forecast")

    # residuos: prediccion a un paso sobre el entrenamiento. Es el analogo del
    # .resid de statsmodels, asi el Ljung-Box es comparable con el del Lab 1.
    ajustado = _desescalar(_predecir_un_paso(red, xt), media, sd)
    residuos = pd.Series(serie.to_numpy(dtype="float64")[cfg.ventana:] - ajustado,
                         index=serie.index[cfg.ventana:], name="residuos")

    parametros = {
        "config": cfg.nombre,
        **{k: v for k, v in asdict(cfg).items() if k != "nombre"},
        "epochs_usadas": int(epochs),
        "semilla": int(semilla),
        "n_muestras_train": int(len(y)),
        "loss_inicial": entreno["historial"][0],
        "loss_final": entreno["historial"][-1],
        "escalado": "z-score sobre la serie transformada",
        "prediccion": "recursiva a un paso",
        "aplanamiento": diagnostico_aplanamiento(forecast),
        "tuneo": tuneo,
    }

    return {
        "modelo": cfg.nombre,
        "parametros": parametros,
        "forecast": forecast,
        "residuos": residuos,
        "aic": None,   # una red no tiene verosimilitud; se compara por RMSE
        "bic": None,
        "fit": None,   # el nn.Module no es serializable y el pipeline no lo usa
    }


def ajustar_todas_configs(serie: pd.Series, horizon: int,
                          configs: dict[str, ConfigLSTM] | None = None,
                          tunear: bool = True) -> dict:
    """
    Ajusta todas las configuraciones registradas sobre una serie.

    Devuelve {nombre_config: resultado}. Agregar una entrada a CONFIGS es todo lo
    que hace falta para que un modelo nuevo entre al pipeline y al comparativo.
    """
    registro = configs if configs is not None else CONFIGS
    resultados = {}

    for nombre, cfg in registro.items():
        tuneo = tunear_epochs(serie, cfg) if tunear else None
        resultados[nombre] = ajustar_lstm(
            serie, horizon, cfg,
            epochs_override=(tuneo["mejor"] if tuneo else None),
            tuneo=tuneo,
        )

    return resultados

# ---------------------------------------------------------------------------
# config y red para lstm_catch22
# ---------------------------------------------------------------------------

@dataclass(frozen=True)
class ConfigLSTMCatch22:
    """
    Analoga a ConfigLSTM, pero para la red que recibe el vector catch22.

    No hereda de ConfigLSTM a proposito: comparten campos por convencion, no
    por sustitucion (una ConfigLSTM no le sirve a esta red sin un vector
    catch22, asi que mezclarlas en el mismo tipo invitaria a pasar la una por
    la otra).
    """
    nombre: str = "lstm_catch22"
    ventana: int = 12
    unidades: int = 32
    capas: int = 1
    dropout: float = 0.1
    epochs: int = config.LSTM_EPOCHS
    lr: float = config.LSTM_LR


class RedLSTMCatch22(nn.Module):
    """
    LSTM sobre la ventana temporal + vector catch22 concatenado al final.

    El vector catch22 NO entra en cada paso de tiempo (no es una secuencia,
    es un resumen de toda la serie): se concatena una sola vez, al estado
    oculto final, junto antes de la capa lineal. Con eso la red aprende un
    ajuste/calibracion condicionado en la "forma" global de la serie, no un
    insumo que varie mes a mes.
    """

    def __init__(self, unidades: int, capas: int, dropout: float, n_catch22: int = 22) -> None:
        super().__init__()
        self.lstm = nn.LSTM(input_size=1, hidden_size=unidades,
                            num_layers=capas, batch_first=True)
        self.dropout = nn.Dropout(dropout)
        self.salida = nn.Linear(unidades + n_catch22, 1)

    def forward(self, x: torch.Tensor, catch22_vec: torch.Tensor) -> torch.Tensor:
        secuencia, _ = self.lstm(x)
        h = self.dropout(secuencia[:, -1])
        combinado = torch.cat([h, catch22_vec], dim=1)
        return self.salida(combinado).squeeze(-1)


# ---------------------------------------------------------------------------
# ventaneo + vector catch22 repetido por muestra
# ---------------------------------------------------------------------------

def _ventanas_catch22(valores: np.ndarray, ventana: int,
                      catch22_vec: np.ndarray) -> tuple[np.ndarray, np.ndarray, np.ndarray]:
    """
    Igual que _ventanas(), y ademas repite el vector catch22 una vez por
    cada muestra (es constante para todas: son features de LA MISMA serie).
    """
    x, y = _ventanas(valores, ventana)
    c = np.repeat(catch22_vec[None, :], x.shape[0], axis=0).astype("float32")
    return x, c, y


# ---------------------------------------------------------------------------
# entrenamiento y prediccion (misma forma que _entrenar/_predecir_*, con
# el argumento extra 'catch22')
# ---------------------------------------------------------------------------

def _entrenar_catch22(red: nn.Module, x: torch.Tensor, c: torch.Tensor, y: torch.Tensor,
                      epochs: int, lr: float, checkpoints: tuple[int, ...] = ()) -> dict:
    opt = torch.optim.Adam(red.parameters(), lr=lr)
    perdida = nn.MSELoss()
    historial: list[float] = []
    estados: dict[int, dict] = {}

    for epoca in range(1, epochs + 1):
        red.train()
        opt.zero_grad()
        error = perdida(red(x, c), y)
        error.backward()
        opt.step()
        historial.append(float(error.item()))

        if epoca in checkpoints:
            estados[epoca] = {k: v.clone() for k, v in red.state_dict().items()}

    return {"historial": historial, "estados": estados}


def _predecir_recursivo_catch22(red: nn.Module, ultima_ventana: np.ndarray,
                                catch22_vec: np.ndarray, horizon: int) -> np.ndarray:
    """Identico a _predecir_recursivo(), pero el vector catch22 (constante)
    se pasa en cada paso junto con la ventana que se va reinyectando."""
    red.eval()
    ventana = list(ultima_ventana)
    c = torch.from_numpy(catch22_vec[None, :].astype("float32"))
    predicciones = []

    with torch.no_grad():
        for _ in range(horizon):
            entrada = np.array(ventana[-len(ultima_ventana):], dtype="float32")
            valor = float(red(torch.from_numpy(entrada[None, :, None]), c).item())
            predicciones.append(valor)
            ventana.append(valor)

    return np.array(predicciones)


def _predecir_un_paso_catch22(red: nn.Module, x: torch.Tensor, c: torch.Tensor) -> np.ndarray:
    red.eval()
    with torch.no_grad():
        return red(x, c).numpy()


# ---------------------------------------------------------------------------
# tuneo de epocas (misma logica que tunear_epochs, con el vector catch22)
# ---------------------------------------------------------------------------

def tunear_epochs_catch22(serie: pd.Series, catch22_vec,
                          cfg: ConfigLSTMCatch22 = ConfigLSTMCatch22(),
                          rejilla: tuple[int, ...] = config.LSTM_REJILLA_EPOCHS,
                          val_meses: int = config.LSTM_VAL_MESES,
                          semilla: int = config.LSTM_SEMILLA) -> dict:
    """
    Igual criterio que tunear_epochs(): valida contra la cola del
    entrenamiento, nunca contra prueba. Misma limitacion documentada alla
    (los 12 meses de validacion caen en el colapso pandemico).
    """
    _fijar_semilla(semilla)
    catch22_vec = np.asarray(catch22_vec, dtype="float64")

    interno = serie.iloc[:-val_meses]
    validacion = serie.iloc[-val_meses:]

    media, sd = _ajustar_escalador(interno)
    z = _escalar(interno.to_numpy(dtype="float64"), media, sd)
    x, c, y = _ventanas_catch22(z, cfg.ventana, catch22_vec)

    red = RedLSTMCatch22(cfg.unidades, cfg.capas, cfg.dropout, n_catch22=len(catch22_vec))
    entreno = _entrenar_catch22(red, torch.from_numpy(x), torch.from_numpy(c),
                                torch.from_numpy(y), epochs=max(rejilla), lr=cfg.lr,
                                checkpoints=tuple(rejilla))

    real = validacion.to_numpy(dtype="float64")
    resultados = []
    for epocas in rejilla:
        red.load_state_dict(entreno["estados"][epocas])
        pred_z = _predecir_recursivo_catch22(red, z[-cfg.ventana:], catch22_vec, val_meses)
        pred = _desescalar(pred_z, media, sd)
        rmse = float(np.sqrt(np.mean((real - pred) ** 2)))
        resultados.append({"epochs": int(epocas), "rmse_val": rmse})

    mejor = min(resultados, key=lambda r: r["rmse_val"])

    return {
        "hiperparametro": "epochs",
        "rejilla": [int(e) for e in rejilla],
        "criterio": "rmse_validacion",
        "escala_criterio": "log1p",
        "val_meses": int(val_meses),
        "val_inicio": validacion.index.min().strftime("%Y-%m"),
        "val_fin": validacion.index.max().strftime("%Y-%m"),
        "n_muestras_interno": int(len(y)),
        "resultados": resultados,
        "mejor": mejor["epochs"],
        "rmse_val_mejor": mejor["rmse_val"],
        "nota": ("la validacion es la cola del entrenamiento; el conjunto de prueba "
                 "nunca se usa para elegir hiperparametros"),
    }


# ---------------------------------------------------------------------------
# API publica: ajustar_lstm_catch22
# ---------------------------------------------------------------------------

def ajustar_lstm_catch22(serie: pd.Series, horizon: int, catch22_vec,
                         cfg: ConfigLSTMCatch22 = ConfigLSTMCatch22(),
                         semilla: int = config.LSTM_SEMILLA,
                         epochs_override: int | None = None,
                         tuneo: dict | None = None) -> dict:
    """
    Ajusta la LSTM con catch22 como entrada extra y pronostica 'horizon'
    meses de forma recursiva.

    'catch22_vec' es la fila de matriz_estandarizada (results/catch22.json)
    correspondiente a esta serie -- ya viene z-scoreada entre las 7 series,
    no hace falta re-estandarizarla aca.

    Devuelve las mismas 7 claves que models._resultado / ajustar_lstm(), para
    que pipeline.py y comparison.py lo traten igual que cualquier otro
    modelo.
    """
    _fijar_semilla(semilla)
    epochs = epochs_override or cfg.epochs
    catch22_vec = np.asarray(catch22_vec, dtype="float64")

    media, sd = _ajustar_escalador(serie)
    z = _escalar(serie.to_numpy(dtype="float64"), media, sd)
    x, c, y = _ventanas_catch22(z, cfg.ventana, catch22_vec)
    xt, ct, yt = torch.from_numpy(x), torch.from_numpy(c), torch.from_numpy(y)

    red = RedLSTMCatch22(cfg.unidades, cfg.capas, cfg.dropout, n_catch22=len(catch22_vec))
    entreno = _entrenar_catch22(red, xt, ct, yt, epochs=epochs, lr=cfg.lr)

    pred = _desescalar(_predecir_recursivo_catch22(red, z[-cfg.ventana:], catch22_vec, horizon),
                       media, sd)
    forecast = pd.Series(pred, index=pronostico_index(serie, horizon), name="forecast")

    ajustado = _desescalar(_predecir_un_paso_catch22(red, xt, ct), media, sd)
    residuos = pd.Series(serie.to_numpy(dtype="float64")[cfg.ventana:] - ajustado,
                         index=serie.index[cfg.ventana:], name="residuos")

    parametros = {
        "config": cfg.nombre,
        **{k: v for k, v in asdict(cfg).items() if k != "nombre"},
        "epochs_usadas": int(epochs),
        "semilla": int(semilla),
        "n_muestras_train": int(len(y)),
        "n_catch22_features": int(len(catch22_vec)),
        "loss_inicial": entreno["historial"][0],
        "loss_final": entreno["historial"][-1],
        "escalado": "z-score sobre la serie transformada; catch22 llega ya "
                    "estandarizado desde catch22.json (matriz_estandarizada)",
        "prediccion": "recursiva a un paso",
        "entrada_extra": "vector catch22 (22) concatenado al ultimo estado "
                         "oculto de la LSTM antes de la capa lineal",
        "aplanamiento": diagnostico_aplanamiento(forecast),
        "tuneo": tuneo,
    }

    return {
        "modelo": cfg.nombre,
        "parametros": parametros,
        "forecast": forecast,
        "residuos": residuos,
        "aic": None,
        "bic": None,
        "fit": None,
    }
