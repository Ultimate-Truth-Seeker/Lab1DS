"""
Estacionariedad en varianza: diagnostico y transformacion.

Separado de stationarity.py porque son responsabilidades distintas: alla se
contrastan hipotesis (ADF, KPSS), aca se decide y aplica la transformacion.

'invertir' es parte del contrato con el resto del equipo: los modelos se ajustan
sobre la serie transformada, asi que las predicciones hay que revertirlas antes
de calcular cualquier metrica de error, o los MAE/RMSE quedan en unidades
logaritmicas y no se pueden interpretar.
"""

import numpy as np
import pandas as pd

from src import config


def chequeo_varianza(s: pd.Series,
                     tramo: int = config.TRAMO_VARIANZA,
                     fin_pre_pandemia: str = config.PRE_PANDEMIA_FIN,
                     umbral: float = config.CORR_VARIANZA_UMBRAL) -> dict:
    """
    ¿La dispersion de la serie crece con su nivel?

    Se parte la serie en tramos de 'tramo' meses, y se mide la correlacion entre
    la desviacion estandar y la media de cada tramo. Si es alta, la varianza
    depende del nivel y conviene transformar.

    El diagnostico se hace sobre el tramo PRE-PANDEMIA. Medido sobre la serie
    completa la correlacion sale baja o incluso negativa en 6 de las 7 series,
    porque el colapso de 2020-2021 agrega un tramo de nivel bajo y dispersion
    alta que rompe la relacion monotona y tapa el diagnostico real.
    """
    def corr(x: pd.Series) -> float | None:
        grupos = [x.iloc[i:i + tramo] for i in range(0, len(x) - tramo + 1, tramo)]
        medias, desvs = [], []
        for g in grupos:
            m = g.mean()
            if m > 0:                 # un tramo entero en cero no aporta informacion
                medias.append(m)
                desvs.append(g.std(ddof=1))
        if len(medias) < 4:
            return None
        c = np.corrcoef(medias, desvs)[0, 1]
        return None if np.isnan(c) else float(c)

    pre = s[s.index < pd.Timestamp(fin_pre_pandemia)]
    corr_pre = corr(pre)
    corr_completo = corr(s)
    necesita = corr_pre is not None and corr_pre > umbral

    return {
        "necesita_transformacion": bool(necesita),
        "criterio": (f"corr(sd, media) de tramos de {tramo} meses sobre el tramo "
                     f"pre-pandemia; se transforma si supera {umbral}"),
        "tramo_evaluado": {
            "inicio": pre.index.min().strftime("%Y-%m") if len(pre) else None,
            "fin": pre.index.max().strftime("%Y-%m") if len(pre) else None,
            "n_meses": int(len(pre)),
        },
        "umbral_corr": umbral,
        "corr_nivel_pre_pandemia": corr_pre,
        "corr_nivel_completo": corr_completo,
        "nota_pandemia": ("medida sobre la serie completa la correlacion baja o cambia de signo: "
                          "el colapso de 2020-2021 enmascara la dependencia varianza-nivel"),
        "corr_post_transformacion": None,   # lo llena decidir()
    }


def aplicar(s: pd.Series, nombre: str = config.TRANSFORMACION) -> pd.Series:
    """log1p = log(1+x). Definida en 0, asi que admite los ceros reales."""
    if nombre == "log1p":
        return np.log1p(s)
    if nombre in (None, "none"):
        return s
    raise ValueError(f"transformacion no soportada: {nombre}")


def invertir(s: pd.Series, nombre: str = config.TRANSFORMACION) -> pd.Series:
    """
    Inversa de 'aplicar'. Necesaria para devolver las predicciones a viajeros.

    Ojo: expm1 de la media de la serie transformada da la MEDIANA, no la media,
    de la distribucion original (desigualdad de Jensen). Para pronosticos
    puntuales el sesgo es a la baja y se corrige multiplicando por
    (1 + sigma^2/2) con sigma^2 la varianza residual del modelo.
    """
    if nombre == "log1p":
        return np.expm1(s)
    if nombre in (None, "none"):
        return s
    raise ValueError(f"transformacion no soportada: {nombre}")


def decidir(s: pd.Series, nombre: str = config.TRANSFORMACION, **kwargs):
    """
    Diagnostica la varianza y aplica la transformacion si hace falta.

    Devuelve (serie_resultante, dict_varianza, dict_transformacion).
    """
    varianza = chequeo_varianza(s, **kwargs)

    if varianza["necesita_transformacion"]:
        s_out = aplicar(s, nombre)
        elegida = nombre
        motivo = (f"corr(sd, media) pre-pandemia = {varianza['corr_nivel_pre_pandemia']:.2f} "
                  f"> {varianza['umbral_corr']}: la dispersion crece con el nivel")
    else:
        s_out = s
        elegida = "none"
        c = varianza["corr_nivel_pre_pandemia"]
        motivo = (f"corr(sd, media) pre-pandemia = {c:.2f} <= {varianza['umbral_corr']}: "
                  f"la varianza no depende del nivel" if c is not None
                  else "no hay suficientes tramos para diagnosticar; se deja en nivel")

    # se vuelve a medir sobre el resultado, para mostrar que la transformacion sirvio
    post = chequeo_varianza(s_out, **kwargs)
    varianza["corr_post_transformacion"] = post["corr_nivel_pre_pandemia"]

    transformacion = {
        "nombre": elegida,
        "inversa": "expm1" if elegida == "log1p" else "ninguna",
        "motivo": motivo,
        "boxcox_descartado": True,
        "boxcox_motivo": (
            "el lambda optimo es inestable segun se incluya o no la pandemia (pre-pandemia da "
            "-0.41 a 0.54; con pandemia da 0.36 a 1.26, o sea 'casi no transformar', contrario "
            "a la evidencia), y scipy.stats.boxcox_normmax con su metodo por defecto falla con "
            "BracketError en 5 de las 7 series. log1p es estable y admite los ceros exactos sin "
            "desplazar la serie."
        ),
    }
    return s_out, varianza, transformacion
