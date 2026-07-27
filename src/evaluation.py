"""
Evaluación y diagnóstico de modelos.

Este módulo concentra las métricas utilizadas para comparar modelos.
"""

from __future__ import annotations

import numpy as np
import pandas as pd

from statsmodels.stats.diagnostic import acorr_ljungbox

from src import config


# ---------------------------------------------------------------------
# utilidades
# ---------------------------------------------------------------------

def obtener_aic(modelo) -> float | None:
    """
    Devuelve el AIC del modelo si está disponible.
    """

    if modelo is None:
        return None

    return float(getattr(modelo, "aic", np.nan))


def obtener_bic(modelo) -> float | None:
    """
    Devuelve el BIC del modelo si está disponible.
    """

    if modelo is None:
        return None

    return float(getattr(modelo, "bic", np.nan))


# ---------------------------------------------------------------------
# Ljung-Box
# ---------------------------------------------------------------------

def ljung_box(
    residuos: pd.Series,
    lags: int = config.PERIOD,
    alpha: float = config.ALPHA,
) -> dict:
    """
    Prueba de Ljung-Box.

    H0:
        Los residuos son independientes
        (no presentan autocorrelación).

    Si p > alpha
        No se rechaza H0.
        El modelo dejó residuos compatibles con ruido blanco.
    """

    residuos = residuos.dropna()

    if len(residuos) <= lags:
        return {
            "stat": None,
            "pvalue": None,
            "alpha": alpha,
            "independientes": None,
        }

    prueba = acorr_ljungbox(
        residuos,
        lags=[lags],
        return_df=True,
    )

    stat = float(prueba["lb_stat"].iloc[0])
    pvalue = float(prueba["lb_pvalue"].iloc[0])

    return {
        "stat": stat,
        "pvalue": pvalue,
        "alpha": alpha,
        "independientes": bool(pvalue > alpha),
    }

# ---------------------------------------------------------------------
# Diagnóstico completo
# ---------------------------------------------------------------------

def diagnostico(
    modelo=None,
    residuos: pd.Series | None = None,
) -> dict:
    """
    Resume las métricas de evaluación disponibles para un modelo.

    Parameters
    ----------
    modelo
        Modelo ajustado (statsmodels).

    residuos
        Serie de residuos del modelo.

    Returns
    -------
    dict
        Diccionario con AIC, BIC y resultado de Ljung-Box.
    """

    resultado = {
        "aic": obtener_aic(modelo),
        "bic": obtener_bic(modelo),
        "ljung_box": None,
    }

    if residuos is not None:
        resultado["ljung_box"] = ljung_box(residuos)

    return resultado


# ---------------------------------------------------------------------
# Actualizar resultado de un modelo
# ---------------------------------------------------------------------

def agregar_diagnostico(
    resultado_modelo: dict,
) -> dict:
    """
    Agrega AIC, BIC y Ljung-Box a un resultado devuelto por models.py.
    """

    modelo = resultado_modelo.get("fit")
    residuos = resultado_modelo.get("residuos")

    diag = diagnostico(
        modelo=modelo,
        residuos=residuos,
    )

    resultado_modelo["aic"] = diag["aic"]
    resultado_modelo["bic"] = diag["bic"]
    resultado_modelo["ljung_box"] = diag["ljung_box"]

    return resultado_modelo