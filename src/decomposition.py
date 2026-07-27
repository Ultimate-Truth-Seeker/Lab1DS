"""
Descomposicion estacional y metricas de forma de la serie.

Este modulo SI produce numeros que el informe cita (fuerza de la estacionalidad
y pendiente de la tendencia), y por eso vive aparte de plots.py: la regla del
repo es que el modulo de graficos no genere valores citables.

metricas_forma descompone UNA sola vez y entrega el objeto para que plots lo
dibuje mas el dict para el JSON, de modo que la descomposicion no se calcule
dos veces por serie.
"""

import numpy as np
import pandas as pd
from statsmodels.tsa.seasonal import seasonal_decompose

from src import config


def descomponer(s: pd.Series, period: int = config.PERIOD, model: str = "additive"):
    """
    Descompone la serie en tendencia + estacionalidad + residuo.

    Se descompone la serie TAL CUAL. Antes se hacia replace(0, nan).interpolate()
    y eso inventaba datos justo en los meses que de verdad valen 0 -- los 12
    meses seguidos de la via Maritima con las fronteras cerradas, que es el
    evento mas interesante de esa serie.

    Devuelve None si no se puede descomponer (p. ej. menos de dos periodos
    completos); el llamador decide que hacer.
    """
    try:
        return seasonal_decompose(s, model=model, period=period)
    except Exception:
        return None


def fuerza_estacionalidad(dec) -> float | None:
    """
    Fuerza de la estacionalidad segun Hyndman (fpp3):

        F = max(0, 1 - Var(residuo) / Var(estacional + residuo))

    Cerca de 0 significa que la estacionalidad aporta poco frente al ruido;
    cerca de 1, que domina. El umbral de referencia para llamarla "fuerte" es
    config.FUERZA_ESTACIONAL_UMBRAL.
    """
    if dec is None:
        return None

    # se alinean contra el indice comun: trend y resid vienen con NaN en los
    # extremos por la media movil
    resid = dec.resid.dropna()
    seasonal = dec.seasonal.reindex(resid.index)
    if resid.empty or seasonal.isna().any():
        return None

    var_resid = resid.var(ddof=1)
    var_sr = (seasonal + resid).var(ddof=1)
    if not var_sr or np.isnan(var_sr):
        return None

    return float(max(0.0, 1.0 - var_resid / var_sr))


def pendiente_tendencia(dec) -> dict | None:
    """
    Ajusta una recta al componente de tendencia y devuelve su pendiente.

    Ojo con la lectura: describe el tramo analizado, no es una proyeccion. Si el
    tramo termina en plena pandemia la pendiente sale negativa aunque la serie
    venga creciendo desde 2009.
    """
    if dec is None:
        return None

    trend = dec.trend.dropna()
    if len(trend) < 2:
        return None

    t = np.arange(len(trend))
    pendiente = float(np.polyfit(t, trend.values, 1)[0])
    media = float(trend.mean())

    return {
        "pendiente_mensual": pendiente,
        "pendiente_anual": pendiente * 12,
        "pct_anual_sobre_media": float(pendiente * 12 / media * 100) if media else None,
        "n_puntos_tendencia": int(len(trend)),
    }


def metricas_forma(s: pd.Series, period: int = config.PERIOD,
                   model: str = "additive", etiqueta_base: str = ""):
    """
    Descompone y resume la forma de la serie.

    Devuelve (dec, metricas). El dict de metricas SIEMPRE trae las mismas
    claves, incluso si la descomposicion falla: asi el JSON no queda con claves
    faltantes y el informe nunca intenta formatear un None inesperado.
    """
    dec = descomponer(s, period=period, model=model)

    metricas = {
        "descomposicion_ok": dec is not None,
        "modelo": model,
        "periodo": period,
        "serie_base": etiqueta_base,
        "fuerza_estacionalidad": None,
        "umbral_estacionalidad_fuerte": config.FUERZA_ESTACIONAL_UMBRAL,
        "estacionalidad_fuerte": None,
        "pendiente_mensual": None,
        "pendiente_anual": None,
        "pct_anual_sobre_media": None,
        "tendencia_signo": "indeterminada",
        "n_puntos_tendencia": 0,
    }

    if dec is None:
        return dec, metricas

    fuerza = fuerza_estacionalidad(dec)
    metricas["fuerza_estacionalidad"] = fuerza
    if fuerza is not None:
        metricas["estacionalidad_fuerte"] = bool(fuerza >= config.FUERZA_ESTACIONAL_UMBRAL)

    tend = pendiente_tendencia(dec)
    if tend is not None:
        metricas.update(tend)
        metricas["tendencia_signo"] = "positiva" if tend["pendiente_mensual"] > 0 else "negativa"

    return dec, metricas
