"""
Análisis de las características catch22 (Laboratorio 2).

Este módulo realiza los análisis solicitados sobre la matriz
estandarizada de catch22.

No imprime.
No genera figuras.
No escribe archivos.

Toda la orquestación queda en pipeline.py y las figuras en plots.py.
"""

from __future__ import annotations

import numpy as np

from sklearn.cluster import AgglomerativeClustering
from sklearn.decomposition import PCA
from sklearn.metrics import silhouette_score
from sklearn.metrics.pairwise import euclidean_distances


# ---------------------------------------------------------------------
# utilidades
# ---------------------------------------------------------------------

def cargar_matriz(payload: dict):
    """
    Extrae del JSON de catch22 la matriz estandarizada.

    Parameters
    ----------
    payload : dict
        Contenido de results/catch22.json

    Returns
    -------
    matriz : ndarray
    series : list[str]
    features : list[str]
    """

    matriz = np.asarray(
        payload["matriz_estandarizada"],
        dtype=float,
    )

    series = list(payload["series"])

    features = list(payload["features"])

    return matriz, series, features

# ---------------------------------------------------------------------
# PCA
# ---------------------------------------------------------------------

def analisis_pca(
    matriz: np.ndarray,
    series: list[str],
):
    """
    Análisis de componentes principales.

    Trabaja SIEMPRE sobre la matriz estandarizada.
    """

    pca = PCA(
        n_components=2,
        random_state=42,
    )

    proyeccion = pca.fit_transform(matriz)

    return {
        "varianza_explicada": [
            float(v)
            for v in pca.explained_variance_ratio_
        ],

        "loadings": (
            pca.components_
            .astype(float)
            .tolist()
        ),

        "proyeccion": {
            serie: [
                float(x),
                float(y),
            ]
            for serie, (x, y)
            in zip(series, proyeccion)
        },
    }

# ---------------------------------------------------------------------
# Clustering
# ---------------------------------------------------------------------

def analisis_clustering(
    matriz: np.ndarray,
    series: list[str],
):
    """
    Clustering jerárquico sobre la matriz estandarizada.

    Se prueban 2, 3 y 4 grupos y se selecciona el que
    obtiene el mayor silhouette score.
    """

    mejor_modelo = None
    mejor_labels = None
    mejor_score = -np.inf
    mejor_k = None

    for k in (2, 3, 4):

        modelo = AgglomerativeClustering(
            n_clusters=k,
            linkage="ward",
        )

        labels = modelo.fit_predict(matriz)

        score = silhouette_score(
            matriz,
            labels,
        )

        if score > mejor_score:
            mejor_modelo = modelo
            mejor_labels = labels
            mejor_score = score
            mejor_k = k

    return {

        "metodo": "AgglomerativeClustering",

        "n_clusters": int(mejor_k),

        "asignacion": {
            serie: int(cluster)
            for serie, cluster
            in zip(series, mejor_labels)
        },

        "criterio": (
            f"Se evaluaron k=2,3,4 y se seleccionó "
            f"el mayor silhouette score "
            f"({mejor_score:.3f})."
        ),

        "silhouette": float(mejor_score),
    }

# ---------------------------------------------------------------------
# Correlaciones
# ---------------------------------------------------------------------

def analisis_correlaciones(
    matriz: np.ndarray,
    features: list[str],
):
    """
    Matriz de correlaciones entre las 22 características.
    """

    correlaciones = np.corrcoef(
        matriz,
        rowvar=False,
    )

    return {
        "features": features,
        "matriz": correlaciones.astype(float).tolist(),
    }


# ---------------------------------------------------------------------
# Distancias
# ---------------------------------------------------------------------

def analisis_distancias(
    matriz: np.ndarray,
    series: list[str],
):
    """
    Matriz de distancias euclidianas entre las series.
    """

    distancias = euclidean_distances(
        matriz,
    )

    return {

        "metrica": "euclidean",

        "series": series,

        "matriz": (
            distancias
            .astype(float)
            .tolist()
        ),
    }


# ---------------------------------------------------------------------
# Análisis completo
# ---------------------------------------------------------------------

def analizar(
    payload: dict,
):
    """
    Ejecuta todos los análisis solicitados para catch22.

    Parameters
    ----------
    payload : dict
        Contenido de results/catch22.json.

    Returns
    -------
    dict
        Estructura lista para serializar como
        results/catch22_analysis.json.
    """

    matriz, series, features = cargar_matriz(
        payload,
    )

    pca = analisis_pca(
        matriz,
        series,
    )

    clustering = analisis_clustering(
        matriz,
        series,
    )

    correlaciones = analisis_correlaciones(
        matriz,
        features,
    )

    distancias = analisis_distancias(
        matriz,
        series,
    )

    return {

        "pca": pca,

        "clustering": clustering,

        "correlaciones": correlaciones["matriz"],

        "distancias": distancias,

        # pipeline.py llenará estas rutas
        "figuras": {},

    }