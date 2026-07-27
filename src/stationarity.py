"""
Estacionariedad en media: contrastes y numero de diferenciaciones.

ADF y KPSS son complementarios y se usan juntos: sus hipotesis nulas son
opuestas, asi que coincidir en ambas es mas solido que fiarse de una sola.
  - ADF   H0: hay raiz unitaria (NO estacionaria)  -> se busca rechazar
  - KPSS  H0: la serie es estacionaria             -> se busca NO rechazar

La estacionariedad en varianza (diagnostico y transformacion) vive en
transform.py, que es otra responsabilidad.
"""

import warnings

import pandas as pd
from statsmodels.tools.sm_exceptions import InterpolationWarning
from statsmodels.tsa.stattools import adfuller, kpss

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


def kpss_test(s: pd.Series, alpha: float = config.ALPHA,
              regression: str = "c") -> dict:
    """
    KPSS. H0: la serie ES estacionaria, asi que NO rechazar es la buena señal.

    statsmodels interpola el p-valor en una tabla y lo satura en 0.1 y en 0.01.
    Cuando eso pasa avisa con InterpolationWarning, y reportar "p = 0.1000"
    seria falso porque el p real es mayor. Por eso devolvemos ademas
    'pvalue_reportable', que es lo que debe imprimir el informe.
    """
    with warnings.catch_warnings(record=True) as capturados:
        warnings.simplefilter("always", InterpolationWarning)
        stat, pvalue, *_ = kpss(s.dropna(), regression=regression, nlags="auto")
        topado = any(issubclass(w.category, InterpolationWarning) for w in capturados)

    if topado and pvalue >= 0.1:
        limite, reportable = ">", ">0.1"
    elif topado and pvalue <= 0.01:
        limite, reportable = "<", "<0.01"
    else:
        limite, reportable = "=", f"{pvalue:.4f}"

    return {
        "stat": float(stat),
        "pvalue": float(pvalue),
        "pvalue_topado": bool(topado),
        "limite": limite,
        "pvalue_reportable": reportable,
        "alpha": alpha,
        # H0 es estacionariedad: no rechazar (p > alpha) la apoya
        "estacionaria": bool(pvalue > alpha),
    }


def pruebas_conjuntas(s: pd.Series, alpha: float = config.ALPHA) -> dict:
    """ADF + KPSS. Solo se da por estacionaria si las dos coinciden."""
    a = adf_test(s, alpha=alpha)
    k = kpss_test(s, alpha=alpha)
    return {
        "adf": a,
        "kpss": k,
        "ambas_estacionaria": bool(a["estacionaria"] and k["estacionaria"]),
    }


def diferenciar(s: pd.Series, d: int = 0, D: int = 0,
                s_period: int = config.PERIOD) -> pd.Series:
    """
    Aplica D diferencias estacionales y despues d regulares.

    El orden entre ambas casi no cambia el resultado, pero se fija (estacional
    primero) para que sea reproducible.
    """
    out = s
    for _ in range(D):
        out = out.diff(s_period)
    for _ in range(d):
        out = out.diff()
    return out.dropna()


def decidir_D(fuerza_estacionalidad, umbral: float = config.FUERZA_ESTACIONAL_UMBRAL,
              d_max: int = config.D_MAX) -> dict:
    """
    Decide la diferenciacion estacional por FUERZA de la estacionalidad.

    A proposito no se usa el ADF aca: el ADF contrasta una raiz unitaria en el
    rezago 1, no esta diseñado para raices unitarias estacionales, y comparar sus
    p-valores con y sin diferencia estacional es una heuristica floja. Se usa el
    criterio de Hyndman (fpp3): si la estacionalidad explica una fraccion grande
    de la variacion (>= umbral), se diferencia en el periodo.
    """
    if fuerza_estacionalidad is None:
        return {"D": 0, "criterio_D": "fuerza de estacionalidad no disponible; D=0 por defecto"}

    fuerte = fuerza_estacionalidad >= umbral
    return {
        "D": min(d_max, 1) if fuerte else 0,
        "criterio_D": (f"fuerza de estacionalidad {fuerza_estacionalidad:.3f} "
                       f"{'>=' if fuerte else '<'} {umbral} (umbral fpp3)"),
    }


def decidir_d(s: pd.Series, D: int = 0, alpha: float = config.ALPHA,
              diff_max: int = config.DIFF_MAX,
              s_period: int = config.PERIOD) -> dict:
    """
    Sube d hasta que ADF rechace Y KPSS no rechace, con tope en diff_max.

    Devuelve la traza de cada intento para que el informe pueda mostrar por que
    se detuvo en ese d y no antes.
    """
    traza = []
    for d in range(diff_max + 1):
        x = diferenciar(s, d=d, D=D, s_period=s_period)
        pr = pruebas_conjuntas(x, alpha=alpha)
        traza.append({
            "d": d,
            "adf_pvalue": pr["adf"]["pvalue"],
            "kpss_pvalue_reportable": pr["kpss"]["pvalue_reportable"],
            "ambas_estacionaria": pr["ambas_estacionaria"],
        })
        if pr["ambas_estacionaria"]:
            return {"d": d, "pruebas_por_d": traza, "estacionaria_final": True}

    return {"d": diff_max, "pruebas_por_d": traza, "estacionaria_final": False}


def determinar_ordenes(s: pd.Series, fuerza_estacionalidad,
                       alpha: float = config.ALPHA,
                       diff_max: int = config.DIFF_MAX,
                       s_period: int = config.PERIOD,
                       serie_base: str = "") -> dict:
    """
    Determina D y d, y arma el bloque que consume el resto del equipo.

    'orden_recomendado' resume la especificacion en notacion de operador de
    retardos, que es lo que hace falta para configurar un ARIMA.
    """
    dec_D = decidir_D(fuerza_estacionalidad)
    dec_d = decidir_d(s, D=dec_D["D"], alpha=alpha, diff_max=diff_max, s_period=s_period)

    d, D = dec_d["d"], dec_D["D"]
    base = serie_base or "serie"
    return {
        "serie_base": base,
        "d": d,
        "D": D,
        "s": s_period,
        "criterio_D": dec_D["criterio_D"],
        "criterio_d": (f"se incrementa d hasta que ADF p < {alpha} y KPSS p > {alpha} "
                       f"simultaneamente (tope {diff_max})"),
        "d_max_permitido": diff_max,
        "orden_recomendado": f"{base} + (1-B)^{d} (1-B^{s_period})^{D}",
        "estacionaria_final": dec_d["estacionaria_final"],
        "pruebas_por_d": dec_d["pruebas_por_d"],
    }
