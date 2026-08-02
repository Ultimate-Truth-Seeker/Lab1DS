"""
Generacion de figuras. Es el unico modulo que toca matplotlib.

Regla: aca no se produce ningun numero que el informe cite. La descomposicion
estacional se calcula en decomposition.py y llega ya resuelta como parametro,
precisamente porque su fuerza de estacionalidad y su pendiente si se citan.
"""

import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
import matplotlib.ticker as mticker
import numpy as np
import pandas as pd
from statsmodels.graphics.tsaplots import plot_acf, plot_pacf
import seaborn as sns

from src import config

plt.rcParams["figure.dpi"] = config.DPI
plt.rcParams["font.size"] = config.FONT_SIZE


def _miles(x, _):
    return f"{x/1000:.0f}k"


def _guardar(fig, ruta):
    config.FIGDIR.mkdir(parents=True, exist_ok=True)
    fig.tight_layout()
    fig.savefig(ruta)
    plt.close(fig)


def temporal_total(serie_mensual: pd.Series, ruta):
    """Serie total de todo el periodo, con pandemia y quiebre metodologico."""
    fig, ax = plt.subplots(figsize=(9, 4))
    ax.plot(serie_mensual.index, serie_mensual.values, color=config.TEAL, linewidth=1.2)
    ax.set_title("Total mensual de viajeros internacionales a Guatemala (2009-2026)")
    ax.set_ylabel("Viajeros")
    ax.axvspan(pd.Timestamp(config.PANDEMIA_INICIO), pd.Timestamp(config.PANDEMIA_FIN),
               color="red", alpha=0.08, label="Pandemia")
    ax.axvline(pd.Timestamp(config.QUIEBRE_METODOLOGICO), color="orange", linestyle="--",
               linewidth=1, label="Quiebre metodológico 2023")
    ax.yaxis.set_major_formatter(mticker.FuncFormatter(_miles))
    ax.legend()
    _guardar(fig, ruta)


def temporal_comparable(serie_mensual: pd.Series, ruta):
    """Turista + Excursionista: la unica combinacion comparable en todo el rango."""
    fig, ax = plt.subplots(figsize=(9, 4))
    ax.plot(serie_mensual.index, serie_mensual.values, color=config.AZUL, linewidth=1.2)
    ax.set_title("Turista + Excursionista mensual (serie comparable 2009-2026)")
    ax.set_ylabel("Viajeros")
    ax.axvspan(pd.Timestamp(config.PANDEMIA_INICIO), pd.Timestamp(config.PANDEMIA_FIN),
               color="red", alpha=0.08, label="Pandemia")
    ax.yaxis.set_major_formatter(mticker.FuncFormatter(_miles))
    ax.legend()
    _guardar(fig, ruta)


def serie_periodo_completo(s: pd.Series, nombre: str, ruta, corte_train=None):
    """
    Una serie sobre TODO el periodo, no solo el tramo de entrenamiento.

    Sirve para ver la recuperacion pos-pandemia, que en las series de train
    (que terminan en mar-2021) no se alcanza a ver. Es exploratoria: el
    modelado sigue usando solo entrenamiento.
    """
    fig, ax = plt.subplots(figsize=(9, 3.6))
    ax.plot(s.index, s.values, color=config.TEAL, linewidth=1.1)
    ax.set_title(f"{nombre} — periodo completo")
    ax.set_ylabel("Viajeros")

    if corte_train is not None:
        ax.axvspan(s.index.min(), pd.Timestamp(corte_train),
                   color="grey", alpha=0.10, label="Entrenamiento")
    ax.axvspan(pd.Timestamp(config.PANDEMIA_INICIO), pd.Timestamp(config.PANDEMIA_FIN),
               color="red", alpha=0.08, label="Pandemia")
    ax.axvline(pd.Timestamp(config.QUIEBRE_METODOLOGICO), color="orange", linestyle="--",
               linewidth=1, label="Quiebre metodológico 2023")
    ax.yaxis.set_major_formatter(mticker.FuncFormatter(_miles))
    ax.legend(fontsize=7.5)
    _guardar(fig, ruta)


def top_paises(acumulado: pd.Series, ruta):
    fig, ax = plt.subplots(figsize=(8, 5))
    acumulado.head(15).sort_values().plot(kind="barh", ax=ax, color=config.TEAL)
    ax.set_title("Top 15 países/agrupaciones por viajeros acumulados (2009-2026)")
    ax.set_xlabel("Viajeros acumulados")
    _guardar(fig, ruta)


def top_regiones(acumulado: pd.Series, ruta):
    fig, ax = plt.subplots(figsize=(8, 4.5))
    acumulado.sort_values().plot(kind="barh", ax=ax, color=config.NARANJA_OSCURO)
    ax.set_title("Viajeros acumulados por región (Región dos), 2009-2026")
    ax.set_xlabel("Viajeros acumulados")
    _guardar(fig, ruta)


def vias_fronteras(via_tot: pd.Series, frontera_tot: pd.Series, ruta):
    fig, axes = plt.subplots(1, 2, figsize=(11, 4.5))
    via_tot.sort_values().plot(kind="barh", ax=axes[0], color=config.AZUL_MEDIO)
    axes[0].set_title("Viajeros acumulados por vía de ingreso")
    frontera_tot.head(10).sort_values().plot(kind="barh", ax=axes[1], color=config.VERDE)
    axes[1].set_title("Top 10 fronteras por viajeros acumulados")
    _guardar(fig, ruta)


def distribuciones(viajero: pd.Series, tipo_tot: pd.Series, ruta):
    """Histograma en log1p (la variable es de conteo, muy sesgada) + total por tipo."""
    fig, axes = plt.subplots(1, 2, figsize=(11, 4))
    np.log1p(viajero).plot(kind="hist", bins=50, ax=axes[0], color=config.MORADO)
    axes[0].set_title("Distribución de 'Viajero' por registro (log1p)")
    axes[0].set_xlabel("log(1 + viajeros por registro)")

    tipo_tot.plot(kind="bar", ax=axes[1], color=config.DURAZNO)
    axes[1].set_title("Viajeros acumulados por tipo de viajero")
    axes[1].tick_params(axis="x", rotation=30)
    _guardar(fig, ruta)


def panel_serie(s: pd.Series, nombre: str, ruta, dec=None):
    """
    Serie + tendencia + estacionalidad + residuo.

    'dec' es el resultado de decomposition.descomponer(). Si viene en None
    (descomposicion fallida) el panel queda con el primer subplot dibujado y los
    otros tres vacios: preferimos una figura degradada a perder la corrida.
    """
    fig, axes = plt.subplots(4, 1, figsize=(9, 9), sharex=True)
    axes[0].plot(s.index, s.values, color=config.TEAL)
    axes[0].set_title(f"{nombre} — serie mensual (train)")

    if dec is not None:
        axes[1].plot(dec.trend, color=config.NARANJA_OSCURO)
        axes[1].set_title("Tendencia")
        axes[2].plot(dec.seasonal, color=config.AZUL_MEDIO)
        axes[2].set_title("Estacionalidad")
        axes[3].plot(dec.resid, color=config.VERDE, marker="o", markersize=2, linestyle="None")
        axes[3].set_title("Residuo")

    _guardar(fig, ruta)


def acf_serie(s: pd.Series, nombre: str, ruta, lags: int = config.LAGS_ACF):
    fig, ax = plt.subplots(figsize=(6, 3.2))
    plot_acf(s, lags=lags, ax=ax)
    ax.set_title(f"ACF — {nombre}")
    _guardar(fig, ruta)


def pacf_serie(s: pd.Series, nombre: str, ruta, lags: int = config.LAGS_PACF,
               subtitulo: str = ""):
    """
    Autocorrelacion parcial, sobre la serie ya transformada y diferenciada.

    Se grafica asi a proposito: el PACF de una serie no estacionaria no es
    interpretable, y su lectura sirve para proponer el orden p del modelo.
    """
    # con 147 obs y d/D aplicados la serie se acorta; plot_pacf exige lags < n/2
    lags = min(lags, max(1, len(s.dropna()) // 2 - 1))

    fig, ax = plt.subplots(figsize=(6, 3.2))
    plot_pacf(s.dropna(), lags=lags, ax=ax, method="ywm")
    titulo = f"PACF — {nombre}"
    if subtitulo:
        titulo += f"\n{subtitulo}"
    ax.set_title(titulo, fontsize=8.5)
    _guardar(fig, ruta)


# Un color/estilo fijo por modelo para que la misma familia se identifique
# igual en las 7 figuras.
_ESTILO_MODELO = {
    "sarima": dict(color=config.NARANJA_OSCURO, linestyle="-"),
    "holt_winters": dict(color=config.AZUL_MEDIO, linestyle="-"),
    "simple_exponential": dict(color=config.MORADO, linestyle="--"),
    "seasonal_naive": dict(color=config.VERDE, linestyle=":"),
    "prophet": dict(color=config.DURAZNO, linestyle="-."),
    # Lab 2. Nelson: agrega "lstm_c2" en la linea siguiente con otro color.
    "lstm_c1": dict(color=config.TEAL, linestyle="-"),
    "lstm_c2": dict(color=config.AZUL, linestyle="--"),
}


def forecast_vs_real(serie_train: pd.Series, serie_test: pd.Series,
                     forecasts: dict, nombre: str, ruta,
                     cola_train: int = 24):
    """
    Cola del entrenamiento + serie de prueba real + pronostico de cada modelo.

    'forecasts' es {nombre_modelo: pd.Series}. Un modelo sin pronostico
    valido (serie vacia, p. ej. prophet no instalado) simplemente no se
    dibuja -- no es un error de la figura, es un dato de la comparacion.
    """
    fig, ax = plt.subplots(figsize=(9, 4.2))

    cola = serie_train.iloc[-cola_train:]
    ax.plot(cola.index, cola.values, color="#888888", linewidth=1.2, label="Train (cola)")
    ax.plot(serie_test.index, serie_test.values, color="black", linewidth=1.6, label="Real (prueba)")

    for modelo, s in forecasts.items():
        if s is None or len(s.dropna()) == 0:
            continue
        estilo = _ESTILO_MODELO.get(modelo, dict(color="#333333", linestyle="-"))
        ax.plot(s.index, s.values, linewidth=1.3, label=modelo, **estilo)

    ax.axvline(serie_test.index.min(), color="grey", linestyle=":", linewidth=0.8)
    ax.set_title(f"{nombre} — pronóstico vs. real (conjunto de prueba)")
    ax.set_ylabel("Viajeros")
    ax.legend(fontsize=7, ncol=2)
    _guardar(fig, ruta)


# ---------------------------------------------------------------------
# Lab 2 - catch22
# ---------------------------------------------------------------------

def plot_pca(
    proyeccion: dict,
    ruta,
):
    """
    Proyección PCA de las series.
    """

    fig, ax = plt.subplots(figsize=(6, 5))

    for nombre, (x, y) in proyeccion.items():

        ax.scatter(
            x,
            y,
            s=50,
        )

        ax.text(
            x,
            y,
            nombre,
            fontsize=8,
        )

    ax.set_xlabel("PC1")

    ax.set_ylabel("PC2")

    ax.set_title("PCA de las características catch22")

    ax.grid(alpha=0.3)

    _guardar(fig, ruta)


def plot_clusters(
    proyeccion: dict,
    clusters: dict,
    ruta,
):
    """
    Clustering sobre la proyección PCA.
    """

    fig, ax = plt.subplots(figsize=(6, 5))

    for nombre, (x, y) in proyeccion.items():

        ax.scatter(
            x,
            y,
            s=60,
            label=f"Grupo {clusters[nombre]}",
        )

        ax.text(
            x,
            y,
            nombre,
            fontsize=8,
        )

    handles, labels = ax.get_legend_handles_labels()

    unico = dict(zip(labels, handles))

    ax.legend(
        unico.values(),
        unico.keys(),
        fontsize=8,
    )

    ax.set_xlabel("PC1")

    ax.set_ylabel("PC2")

    ax.set_title("Clustering de las series")

    ax.grid(alpha=0.3)

    _guardar(fig, ruta)

def plot_heatmap(
    matriz,
    series,
    features,
    ruta,
):
    """
    Heatmap de las 22 características.
    """

    fig, ax = plt.subplots(
        figsize=(12, 5)
    )

    sns.heatmap(
        matriz,
        cmap="coolwarm",
        xticklabels=features,
        yticklabels=series,
        ax=ax,
    )

    ax.set_title(
        "Heatmap de características catch22"
    )

    plt.xticks(
        rotation=90,
        fontsize=7,
    )

    _guardar(fig, ruta)


def plot_correlaciones(
    correlaciones,
    features,
    ruta,
):
    """
    Matriz de correlaciones entre características.
    """

    fig, ax = plt.subplots(
        figsize=(10, 8)
    )

    sns.heatmap(
        correlaciones,
        cmap="coolwarm",
        center=0,
        xticklabels=features,
        yticklabels=features,
        ax=ax,
    )

    ax.set_title(
        "Correlación entre características catch22"
    )

    plt.xticks(
        rotation=90,
        fontsize=6,
    )

    plt.yticks(
        fontsize=6,
    )

    _guardar(fig, ruta)


def plot_distancias(
    distancias,
    series,
    ruta,
):
    """
    Matriz de distancias entre series.
    """

    fig, ax = plt.subplots(
        figsize=(6, 5)
    )

    sns.heatmap(
        distancias,
        cmap="viridis",
        xticklabels=series,
        yticklabels=series,
        annot=True,
        fmt=".2f",
        ax=ax,
    )

    ax.set_title(
        "Distancias entre series"
    )

    _guardar(fig, ruta)