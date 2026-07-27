"""
Particion temporal y construccion de las series mensuales.
"""

import pandas as pd

from src import config


def particion(df: pd.DataFrame, frac: float = config.TRAIN_FRAC) -> dict:
    """
    Corte cronologico del eje temporal (no aleatorio: son series de tiempo,
    el conjunto de prueba tiene que ser posterior al de entrenamiento).

    Devuelve los meses completos, los de train, y las filas de cada lado.
    """
    meses = pd.date_range(df["Fecha"].min(), df["Fecha"].max(), freq=config.FREQ)
    n_train = int(len(meses) * frac)
    corte = meses[n_train - 1]        # ultimo mes de entrenamiento
    inicio_test = meses[n_train]      # primer mes de prueba

    return {
        "meses": meses,
        "n_train": n_train,
        "corte": corte,
        "inicio_test": inicio_test,
        "meses_train": meses[:n_train],
        "train": df[df["Fecha"] <= corte].copy(),
        "test": df[df["Fecha"] > corte].copy(),
    }


def _serie_mensual(df: pd.DataFrame, meses: pd.DatetimeIndex) -> pd.Series:
    """
    Agrega viajeros por mes y reindexa contra el rango FIJO de meses recibido.

    El reindex contra un rango fijo (y no contra el min/max de la propia
    subserie) es deliberado: algunas categorias no tienen NINGUN registro en
    ciertos meses -- por ejemplo la via Maritima durante el cierre de fronteras
    de la pandemia. Esa ausencia es un 0 real, no un motivo para recortar la
    serie. Sin esto, la serie de Maritima parecia terminar en marzo de 2020.
    """
    return df.groupby("Fecha")["Viajero"].sum().reindex(meses, fill_value=0)


def construir_series(df: pd.DataFrame, meses: pd.DatetimeIndex,
                     paises: list) -> dict:
    """
    Construye las 7 series mensuales sobre el rango de meses indicado.

    'paises' se recibe como parametro a proposito: el top-3 se decide con el
    acumulado de TODO el periodo (criterio del enunciado), no con el subconjunto
    que se pasa aca. Calcularlo adentro daria un top-3 distinto.

    Devuelve {clave: Series} donde clave es 'total', el nombre de la via, o el
    nombre del pais.
    """
    series = {"total": _serie_mensual(df, meses)}
    series["total"].index.name = "Fecha"

    for via in config.VIAS:
        series[via] = _serie_mensual(df[df["Vía"] == via], meses)

    for pais in paises:
        series[pais] = _serie_mensual(df[df["País"] == pais], meses)

    return series
