"""
Carga del dataset. Unico punto de entrada de I/O de datos.

El Excel tarda ~55s en abrirse, asi que se cachea a CSV. Ojo con un detalle
que no es obvio: un to_csv/read_csv normal NO devuelve los mismos floats.
Se pierden bits en 2,125 valores de 'Viajero' (delta ~1.5e-11), y eso mueve
el maximo del dataset de 92336.03506702803 a ...805, que es justo un numero
que sale impreso en el informe.

Por eso 'Viajero' se guarda como hexadecimal de float (float.hex), que es
exacto bit a bit. Se lee en ~0.5s en vez de 55s.
"""

import pandas as pd

from src import config

_COL_FLOAT = "Viajero"


def _cache_vigente() -> bool:
    """El cache sirve si existe y no es mas viejo que el Excel."""
    if not config.CACHE_PATH.exists():
        return False
    return config.CACHE_PATH.stat().st_mtime >= config.DATA_PATH.stat().st_mtime


def _leer_excel() -> pd.DataFrame:
    return pd.read_excel(config.DATA_PATH, sheet_name=config.SHEET_NAME)


def _guardar_cache(df: pd.DataFrame) -> None:
    config.CACHEDIR.mkdir(parents=True, exist_ok=True)
    aux = df.copy()
    aux[_COL_FLOAT] = [float(v).hex() for v in aux[_COL_FLOAT]]
    aux.to_csv(config.CACHE_PATH, index=False, encoding="utf-8")


def _leer_cache() -> pd.DataFrame:
    df = pd.read_csv(config.CACHE_PATH, encoding="utf-8", dtype={_COL_FLOAT: str})
    df[_COL_FLOAT] = [float.fromhex(s) for s in df[_COL_FLOAT]]
    return df


def cargar(usar_cache: bool = True) -> pd.DataFrame:
    """
    Devuelve el dataset con la columna 'Fecha' agregada.

    'Fecha' se deriva despues de leer, nunca se cachea, para que el cache sea
    espejo exacto del Excel y no acumule columnas calculadas.
    """
    if usar_cache and _cache_vigente():
        df = _leer_cache()
    else:
        df = _leer_excel()
        if usar_cache:
            _guardar_cache(df)

    df["Fecha"] = pd.to_datetime(dict(year=df["Año"], month=df["Mes cod"], day=1))
    return df
