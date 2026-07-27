"""
Metricas del analisis exploratorio.

Todas las funciones DEVUELVEN datos, ninguna imprime ni grafica. De aca salen
los numeros que cita el informe, asi que el pipeline las serializa a JSON y el
reporte solo los lee (antes estaban transcritos a mano en el builder).
"""

import pandas as pd

from src import config


def dimensiones(df: pd.DataFrame) -> dict:
    """Filas y columnas. Ojo: 'Fecha' es calculada, no viene del Excel."""
    return {
        "filas": int(df.shape[0]),
        "columnas": int(df.shape[1]),
        "columnas_fuente": int(df.shape[1] - 1),  # sin la 'Fecha' que agregamos
    }


def calidad(df: pd.DataFrame) -> dict:
    """Faltantes, duplicados, ceros, negativos y atipicos por regla de Tukey."""
    q1, q3 = df["Viajero"].quantile(config.CUANTILES)
    iqr = q3 - q1
    upper = q3 + config.IQR_MULT * iqr
    n_sobre = int((df["Viajero"] > upper).sum())

    return {
        "faltantes_por_columna": {c: int(n) for c, n in df.isnull().sum().items()},
        "faltantes_total": int(df.isnull().sum().sum()),
        "duplicados_exactos": int(df.duplicated().sum()),
        "ceros": int((df["Viajero"] == 0).sum()),
        "pct_ceros": float((df["Viajero"] == 0).mean() * 100),
        "negativos": int((df["Viajero"] < 0).sum()),
        "iqr_umbral_superior": float(upper),
        "iqr_filas_sobre_umbral": n_sobre,
        "iqr_pct_sobre_umbral": float((df["Viajero"] > upper).mean() * 100),
        "registros_por_anio": {int(a): int(n) for a, n in df.groupby("Año").size().items()},
    }


def descriptivos(df: pd.DataFrame) -> dict:
    """describe() de 'Viajero' mas el registro donde ocurre el maximo."""
    d = df["Viajero"].describe()
    fila_max = df.loc[df["Viajero"].idxmax()]

    return {
        "count": float(d["count"]),
        "media": float(d["mean"]),
        "sd": float(d["std"]),
        "min": float(d["min"]),
        "p25": float(d["25%"]),
        "mediana": float(d["50%"]),
        "p75": float(d["75%"]),
        "max": float(d["max"]),
        "max_contexto": {
            "pais": str(fila_max["País"]),
            "frontera": str(fila_max["Frontera"]),
            "tipo_viajero": str(fila_max["Tipo de Viajero"]),
            "fecha": fila_max["Fecha"].strftime("%Y-%m"),
        },
    }


def acumulados(df: pd.DataFrame, columna: str, top: int | None = None) -> list:
    """
    Viajeros acumulados por categoria, de mayor a menor, con su porcentaje
    sobre el total. El % lo calculamos aca para que el informe no lo derive.
    """
    tot = df.groupby(columna)["Viajero"].sum().sort_values(ascending=False)
    total = tot.sum()
    if top is not None:
        tot = tot.head(top)

    return [
        {"nombre": str(k), "acumulado": float(v), "pct": float(v / total * 100)}
        for k, v in tot.items()
    ]


def quiebre_metodologico(df: pd.DataFrame, anio_corte: int = 2023) -> dict:
    """
    Evidencia del cambio de metodologia de la fuente en 2023.

    Son cuatro numeros que el informe citaba a mano y estaban mal: cuantos
    paises individuales se reportaban antes del corte, cuantas agrupaciones de
    mercado despues, y como cae la categoria 'Viajero' entre ambos tramos.
    """
    pre = df[df["Año"] < anio_corte]
    post = df[df["Año"] >= anio_corte]
    viajero = df[df["Tipo de Viajero"] == "Viajero"].groupby("Año")["Viajero"].sum()

    return {
        "anio_corte": anio_corte,
        "paises_antes": int(pre["País"].nunique()),
        "grupos_despues": int(post["País"].nunique()),
        "viajero_anio_previo": float(viajero.get(anio_corte - 1, 0)),
        "viajero_anio_corte": float(viajero.get(anio_corte, 0)),
    }


def cuasi_duplicados(df: pd.DataFrame) -> dict:
    """
    Combinaciones repetidas al ignorar 'Agrupación Residencia'.

    No son errores de carga: esa columna aporta granularidad extra dentro de un
    mismo país (p. ej. 'Colombia' vs 'Otros Suramérica'). Se reporta el conteo
    para documentarlo.
    """
    cols = ["Año", "Mes cod", "Vía", "Frontera", "País", "Tipo de Viajero"]
    repetidos = df.groupby(cols).size()
    return {"combinaciones_repetidas": int((repetidos > 1).sum())}


def region_sin_asignar(df: pd.DataFrame, columna: str = "Región dos") -> dict:
    """Registros con '0' de catalogo en la columna de region, y en que años."""
    marca = df[columna].astype(str).str.strip() == "0"
    return {
        "registros": int(marca.sum()),
        "pct": float(marca.mean() * 100),
        "anios": sorted(int(a) for a in df.loc[marca, "Año"].unique()),
    }


def impacto_pandemia(df: pd.DataFrame, anio_base: int = 2019) -> dict:
    """
    Caida de la serie comparable (Turista + Excursionista) frente al año base.

    Se usa Turista + Excursionista porque es la unica combinacion consistente
    en todo el rango, segun la nota del enunciado.
    """
    comp = df[df["Tipo de Viajero"].isin(config.TIPOS_COMPARABLES)]
    por_anio = comp.groupby("Año")["Viajero"].sum()
    base = por_anio.get(anio_base, 0)

    return {
        "anio_base": anio_base,
        "total_base": float(base),
        "pct_respecto_base": {
            str(a): float(por_anio.get(a, 0) / base * 100)
            for a in (anio_base + 1, anio_base + 2) if base
        },
    }


def describir_serie(s: pd.Series) -> dict:
    """Inicio, fin, frecuencia y descriptivos de una serie mensual."""
    d = s.describe()
    ceros = s == 0
    # tramo consecutivo de ceros mas largo: para la via Maritima es el cierre de
    # fronteras, el evento atipico mas marcado de todas las series
    racha = tramo = 0
    for v in ceros:
        tramo = tramo + 1 if v else 0
        racha = max(racha, tramo)

    return {
        "inicio": s.index.min().strftime("%Y-%m"),
        "fin": s.index.max().strftime("%Y-%m"),
        "frecuencia": "Mensual (MS)",
        "n_obs": int(len(s)),
        "media": float(d["mean"]),
        "sd": float(d["std"]),
        "min": float(d["min"]),
        "max": float(d["max"]),
        "meses_en_cero": int(ceros.sum()),
        "racha_ceros_max": int(racha),
    }
