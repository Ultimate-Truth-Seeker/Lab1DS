"""
Modelos de predicción para las series de tiempo.

Este módulo únicamente ajusta modelos y devuelve sus resultados.
No escribe archivos, no genera figuras y no conoce el pipeline.
"""

from __future__ import annotations

import numpy as np
import pandas as pd

from statsmodels.tsa.holtwinters import (
    SimpleExpSmoothing,
    ExponentialSmoothing,
)

from src import config
from src import transform


# ---------------------------------------------------------------------
# utilidades privadas
# ---------------------------------------------------------------------

def _resultado(
    modelo: str,
    parametros: dict,
    forecast: pd.Series,
    residuos: pd.Series,
    aic: float | None = None,
    bic: float | None = None,
    ajuste=None,
) -> dict:
    """
    Construye un resultado con formato uniforme para todos los modelos.
    """
    return {
        "modelo": modelo,
        "parametros": parametros,
        "forecast": forecast,
        "residuos": residuos,
        "aic": aic,
        "bic": bic,
        "fit": ajuste,      # útil para inspección; pipeline no lo serializará
    }


def pronostico_index(serie: pd.Series, horizon: int) -> pd.DatetimeIndex:
    """
    Índice mensual para el horizonte de predicción.

    Publica porque lstm.py tambien la necesita: el LSTM debe pronosticar sobre
    exactamente los mismos meses que los modelos de este modulo.
    """
    inicio = serie.index[-1] + pd.offsets.MonthBegin()
    return pd.date_range(
        start=inicio,
        periods=horizon,
        freq=config.FREQ,
    )


# los modelos de abajo la llaman con el nombre privado original
_pronostico_index = pronostico_index


# ---------------------------------------------------------------------
# seasonal naive
# ---------------------------------------------------------------------

def seasonal_naive(
    serie: pd.Series,
    horizon: int,
    season_length: int = config.PERIOD,
) -> dict:
    """
    Pronóstico Seasonal Naive.

    Cada mes futuro toma el valor observado exactamente un año atrás.
    """

    if len(serie) < season_length:
        raise ValueError(
            f"La serie necesita al menos {season_length} observaciones."
        )

    indice = _pronostico_index(serie, horizon)

    patron = serie.iloc[-season_length:].to_numpy()

    forecast = np.resize(patron, horizon)

    forecast = pd.Series(
        forecast,
        index=indice,
        name="forecast",
    )

    residuos = serie.iloc[season_length:] - serie.shift(season_length).iloc[season_length:]

    return _resultado(
        modelo="seasonal_naive",
        parametros={
            "season_length": season_length,
        },
        forecast=forecast,
        residuos=residuos,
    )


# ---------------------------------------------------------------------
# simple exponential smoothing
# ---------------------------------------------------------------------

def simple_exponential(
    serie: pd.Series,
    horizon: int,
) -> dict:
    """
    Ajusta un modelo de suavizamiento exponencial simple.
    """

    ajuste = (
        SimpleExpSmoothing(
            serie,
            initialization_method="estimated",
        )
        .fit(optimized=True)
    )

    indice = _pronostico_index(serie, horizon)

    forecast = pd.Series(
        ajuste.forecast(horizon),
        index=indice,
        name="forecast",
    )

    residuos = ajuste.resid

    return _resultado(
        modelo="simple_exponential",
        parametros={
            "alpha": float(ajuste.model.params["smoothing_level"]),
        },
        forecast=forecast,
        residuos=residuos,
        aic=float(ajuste.aic),
        bic=float(ajuste.bic),
        ajuste=ajuste,
    )


# ---------------------------------------------------------------------
# Holt-Winters
# ---------------------------------------------------------------------

def holt_winters(
    serie: pd.Series,
    horizon: int,
    trend: str = "add",
    seasonal: str = "add",
    seasonal_periods: int = config.PERIOD,
) -> dict:

    ajuste = (
        ExponentialSmoothing(
            serie,
            trend=trend,
            seasonal=seasonal,
            seasonal_periods=seasonal_periods,
            initialization_method="estimated",
        )
        .fit(optimized=True)
    )

    indice = _pronostico_index(serie, horizon)

    forecast = pd.Series(
        ajuste.forecast(horizon),
        index=indice,
        name="forecast",
    )

    residuos = ajuste.resid

    parametros = {
        "trend": trend,
        "seasonal": seasonal,
        "seasonal_periods": seasonal_periods,
        "alpha": float(ajuste.model.params["smoothing_level"]),
        "beta": float(ajuste.model.params["smoothing_trend"]),
        "gamma": float(ajuste.model.params["smoothing_seasonal"]),
    }

    return _resultado(
        modelo="holt_winters",
        parametros=parametros,
        forecast=forecast,
        residuos=residuos,
        aic=float(ajuste.aic),
        bic=float(ajuste.bic),
        ajuste=ajuste,
    )

# ---------------------------------------------------------------------
# SARIMAX
# ---------------------------------------------------------------------

from itertools import product

from statsmodels.tsa.statespace.sarimax import SARIMAX


def sarimax_grid(
    serie: pd.Series,
    horizon: int,
    d: int = 1,
    D: int = 1,
    seasonal_periods: int = config.PERIOD,
    p_values=(0, 1, 2),
    q_values=(0, 1, 2),
    P_values=(0, 1),
    Q_values=(0, 1),
) -> dict:

    mejor_modelo = None
    mejor_fit = None
    mejor_aic = np.inf

    for p, q, P, Q in product(
        p_values,
        q_values,
        P_values,
        Q_values,
    ):

        try:

            modelo = SARIMAX(
                serie,
                order=(p, d, q),
                seasonal_order=(P, D, Q, seasonal_periods),
                enforce_stationarity=False,
                enforce_invertibility=False,
            )

            fit = modelo.fit(disp=False)

            if fit.aic < mejor_aic:
                mejor_aic = fit.aic
                mejor_modelo = (
                    p,
                    d,
                    q,
                    P,
                    D,
                    Q,
                )
                mejor_fit = fit

        except Exception:
            continue

    if mejor_fit is None:
        raise RuntimeError(
            "No fue posible ajustar ningún modelo SARIMA."
        )

    indice = _pronostico_index(
        serie,
        horizon,
    )

    forecast = pd.Series(
        mejor_fit.forecast(horizon),
        index=indice,
        name="forecast",
    )

    residuos = mejor_fit.resid

    p, d, q, P, D, Q = mejor_modelo

    return _resultado(
        modelo="sarima",
        parametros={
            "order": [p, d, q],
            "seasonal_order": [
                P,
                D,
                Q,
                seasonal_periods,
            ],
        },
        forecast=forecast,
        residuos=residuos,
        aic=float(mejor_fit.aic),
        bic=float(mejor_fit.bic),
        ajuste=mejor_fit,
    )

# ---------------------------------------------------------------------
# Prophet
# ---------------------------------------------------------------------

try:
    from prophet import Prophet
    _PROPHET_DISPONIBLE = True
except ImportError:
    Prophet = None
    _PROPHET_DISPONIBLE = False


def prophet_model(
    serie: pd.Series,
    horizon: int,
) -> dict:
    """
    Ajusta un modelo Prophet.

    Si Prophet no está instalado devuelve un resultado indicando
    que el modelo no pudo ejecutarse.
    """

    if not _PROPHET_DISPONIBLE:

        indice = _pronostico_index(serie, horizon)

        return _resultado(
            modelo="prophet",
            parametros={
                "disponible": False,
            },
            forecast=pd.Series(index=indice, dtype=float),
            residuos=pd.Series(dtype=float),
        )

    df = pd.DataFrame({
        "ds": serie.index,
        "y": serie.values,
    })

    modelo = Prophet(
        yearly_seasonality=True,
        weekly_seasonality=False,
        daily_seasonality=False,
    )

    modelo.fit(df)

    futuro = modelo.make_future_dataframe(
        periods=horizon,
        freq="MS",
    )

    pred = modelo.predict(futuro)

    forecast = pd.Series(
        pred["yhat"].iloc[-horizon:].values,
        index=_pronostico_index(serie, horizon),
        name="forecast",
    )

    ajustado = pred["yhat"].iloc[:len(serie)].values

    residuos = pd.Series(
        serie.values - ajustado,
        index=serie.index,
    )

    return _resultado(
        modelo="prophet",
        parametros={
            "yearly_seasonality": True,
            "weekly_seasonality": False,
            "daily_seasonality": False,
        },
        forecast=forecast,
        residuos=residuos,
    )


# ---------------------------------------------------------------------
# Ejecutar todos los modelos
# ---------------------------------------------------------------------

def ajustar_todos(
    serie: pd.Series,
    horizon: int,
    transformacion: str = "none",
    d: int = 0,
    D: int = 0,
) -> dict:

    if transformacion != "none":
        serie_modelo = transform.aplicar(
            serie,
            nombre=transformacion,
        )
    else:
        serie_modelo = serie

    resultados = {}

    resultados["seasonal_naive"] = seasonal_naive(
        serie_modelo,
        horizon,
    )

    resultados["simple_exponential"] = simple_exponential(
        serie_modelo,
        horizon,
    )

    resultados["holt_winters"] = holt_winters(
        serie_modelo,
        horizon,
    )

    resultados["sarima"] = sarimax_grid(
        serie_modelo,
        horizon,
        d=d,
        D=D,
    )

    resultados["prophet"] = prophet_model(
        serie_modelo,
        horizon,
    )

    if transformacion != "none":
        for resultado in resultados.values():
            resultado["forecast"] = transform.invertir(
                resultado["forecast"],
                nombre=transformacion,
            )

    return resultados