"""
Extraccion de las 22 caracteristicas de catch22 (Laboratorio 2).

catch22 resume una serie de tiempo en 22 numeros que capturan propiedades como
autocorrelacion, distribucion de valores, entropia y comportamiento de rachas.
Sirve para comparar series entre si sin mirarlas una por una: en vez de siete
graficos, se obtiene una matriz de siete filas y veintidos columnas sobre la que
se puede hacer PCA, clustering o medir distancias.

Misma disciplina que models.py y lstm.py: aca solo se calcula y se devuelven
dicts. No se imprime, no se escriben archivos y no se conoce el pipeline.
"""

from __future__ import annotations

import numpy as np
import pandas as pd
import pycatch22

from src import config


def extraer(serie: pd.Series) -> dict:
    """
    Las 22 caracteristicas de una serie.

    pycatch22 espera una lista de floats: no acepta pd.Series ni ndarray, de ahi
    la conversion explicita.
    """
    valores = serie.to_numpy(dtype="float64").tolist()
    resultado = pycatch22.catch22_all(valores)
    return {
        "names": list(resultado["names"]),
        "values": [float(v) for v in resultado["values"]],
    }


def estandarizar(matriz: list[list[float]],
                 ddof: int = config.CATCH22_DDOF) -> dict:
    """
    z-score POR COLUMNA de la matriz de caracteristicas.

    Por columna y no global porque cada caracteristica tiene su propia escala: si
    se estandariza todo junto, las de rango grande dominan las distancias y el
    PCA, y las demas dejan de influir.

    Si una columna es constante su desviacion es 0; se usa 1.0 para no dividir
    por cero. Con estas 7 series no ocurre, pero la guardia evita un NaN
    silencioso si alguien corre el modulo sobre otro conjunto.
    """
    m = np.asarray(matriz, dtype="float64")
    media = m.mean(axis=0)
    sd = m.std(axis=0, ddof=ddof)
    sd_segura = np.where(sd > 0, sd, 1.0)

    return {
        "matriz": ((m - media) / sd_segura).tolist(),
        "media": media.tolist(),
        "sd": sd_segura.tolist(),
        "ddof": int(ddof),
        "columnas_constantes": int((sd == 0).sum()),
    }


def matriz(series: dict[str, pd.Series]) -> dict:
    """
    Matriz de caracteristicas: una fila por serie, una columna por caracteristica.

    Es lo que pide el inciso 2.3. Devuelve tambien la version estandarizada, que
    es sobre la que se hacen los analisis comparativos del 2.5.
    """
    if not series:
        raise ValueError("No hay series para procesar.")

    nombres_features = None
    filas = []
    for clave, serie in series.items():
        extraido = extraer(serie)
        if nombres_features is None:
            nombres_features = extraido["names"]
        elif extraido["names"] != nombres_features:
            # catch22 devuelve siempre las mismas 22 en el mismo orden; si esto
            # cambiara, las columnas dejarian de ser comparables entre filas
            raise ValueError(f"catch22 devolvio otras caracteristicas para '{clave}'.")
        filas.append(extraido["values"])

    estandar = estandarizar(filas)

    return {
        "n_series": len(filas),
        "n_features": len(nombres_features),
        "series": list(series.keys()),
        "features": nombres_features,
        "matriz": filas,
        "matriz_estandarizada": estandar["matriz"],
        "estandarizacion": {
            "media": estandar["media"],
            "sd": estandar["sd"],
            "ddof": estandar["ddof"],
            "columnas_constantes": estandar["columnas_constantes"],
        },
    }
