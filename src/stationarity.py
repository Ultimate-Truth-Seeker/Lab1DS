"""
Pruebas de estacionariedad.

Por ahora solo Dickey-Fuller aumentado sobre el nivel de la serie. Aca entran
despues KPSS, la transformacion de varianza (log/Box-Cox) y la determinacion
del numero de diferenciaciones.
"""

import pandas as pd
from statsmodels.tsa.stattools import adfuller

from src import config


def adf_test(s: pd.Series, alpha: float = config.ALPHA) -> dict:
    """
    ADF sobre el nivel, sin diferenciar.

    H0: la serie tiene raiz unitaria (no es estacionaria en media). Si el
    p-valor cae por debajo de alpha se rechaza H0. Devolvemos el bool y no la
    frase, para que el texto lo redacte el informe.
    """
    stat, pvalue, *_ = adfuller(s.dropna())
    return {
        "stat": float(stat),
        "pvalue": float(pvalue),
        "alpha": alpha,
        "estacionaria": bool(pvalue < alpha),
    }
