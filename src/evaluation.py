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


# ---------------------------------------------------------------------
# Métricas de error de pronóstico
# ---------------------------------------------------------------------
#
# mae/rmse siempre alinean por INDICE (fecha), nunca por posicion: un
# pronostico que arranca un mes corrido del real pasaria desapercibido si
# se comparara por posicion, y ambas series viven en el mismo eje de fechas
# (ver series.py). Si el pronostico viene vacio (p. ej. prophet no
# instalado, ver models.py) el resultado es NaN, no un error, para que la
# tabla comparativa lo pueda mostrar como "no disponible" en vez de
# romperse.

def mae(y_real: pd.Series, y_pred: pd.Series) -> float:
    """Error absoluto medio entre pronostico y valor real, alineado por fecha."""
    y_real_al, y_pred_al = y_real.align(y_pred, join="inner")
    if y_real_al.empty:
        return float("nan")
    return float(np.mean(np.abs(y_real_al - y_pred_al)))


def rmse(y_real: pd.Series, y_pred: pd.Series) -> float:
    """Raiz del error cuadratico medio entre pronostico y valor real."""
    y_real_al, y_pred_al = y_real.align(y_pred, join="inner")
    if y_real_al.empty:
        return float("nan")
    return float(np.sqrt(np.mean((y_real_al - y_pred_al) ** 2)))


def metricas_error(y_real: pd.Series, y_pred: pd.Series) -> dict:
    """
    MAE y RMSE juntos, mas cuantos meses se pudieron comparar.

    n_obs_comparados por debajo del horizonte esperado (63 meses de prueba)
    es la señal de que el pronostico no cubre todo el rango de prueba (p.
    ej. un modelo que fallo a mitad de camino); el llamador decide si eso
    invalida al modelo para la tabla comparativa.
    """
    y_real_al, _ = y_real.align(y_pred, join="inner")
    return {
        "mae": mae(y_real, y_pred),
        "rmse": rmse(y_real, y_pred),
        "n_obs_comparados": int(len(y_real_al)),
    }