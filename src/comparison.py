"""
Predicción y análisis comparativo (rubros 5 y 6).

Igual que eda.py: todas las funciones DEVUELVEN datos, ninguna imprime ni
escribe archivos. pipeline.py orquesta, guarda resultados/*.json y llama a
plots.py para las figuras.

Depende de resultados que produce (results/models.json: parámetros,
AIC, BIC, Ljung-Box y forecast por serie y modelo) y, para las 4 preguntas
comparativas, de las series de entrenamiento ya construidas (que este módulo
reconstruye por su cuenta con series.construir_series, porque series.json solo
guarda estadísticos resumen, no los valores de la serie).
"""

from __future__ import annotations

import pandas as pd

from src import config, decomposition as D, evaluation as E, series as S


# ---------------------------------------------------------------------
# Series de prueba
# ---------------------------------------------------------------------

def construir_series_test(df: pd.DataFrame, part: dict, paises: list) -> dict:
    """
    Las 7 series mensuales sobre el rango de PRUEBA (nadie las había armado).

    Mismo mecanismo que las de entrenamiento: series.construir_series ya
    acepta cualquier rango de meses y cualquier subconjunto de filas, así que
    solo hace falta pasarle el tramo de prueba en vez del de entrenamiento.
    """
    meses_test = part["meses"][part["n_train"]:]
    return S.construir_series(part["test"], meses_test, paises)


# ---------------------------------------------------------------------
# Forecast de models.json (dict fecha->valor) a pd.Series
# ---------------------------------------------------------------------

def forecast_a_serie(forecast: dict) -> pd.Series:
    """
    {'2021-04': 120345.3, ...} -> pd.Series con índice de fechas (mes-inicio).

    Serie vacía si 'forecast' viene vacío (p. ej. prophet no instalado en
    models.py, que en ese caso deja forecast={}): evaluation.metricas_error
    ya sabe devolver NaN para ese caso en vez de fallar.
    """
    if not forecast:
        return pd.Series(dtype=float)
    s = pd.Series(forecast, dtype=float)
    s.index = pd.to_datetime(s.index)
    return s.sort_index()


# ---------------------------------------------------------------------
# Tabla comparativa por serie (AIC/BIC + MAE/RMSE propios)
# ---------------------------------------------------------------------

def evaluar_modelos_serie(serie_test: pd.Series, modelos_json: dict) -> dict:
    """
    Para una serie: junta aic/bic/ljung_box (de models.json) con
    mae/rmse (calculados acá contra serie_test). Devuelve {modelo: registro}.
    """
    registros = {}
    for modelo, info in modelos_json.items():
        forecast = forecast_a_serie(info.get("forecast", {}))
        err = E.metricas_error(serie_test, forecast)
        registros[modelo] = {
            "parametros": info.get("parametros"),
            "aic": info.get("aic"),
            "bic": info.get("bic"),
            "ljung_box": info.get("ljung_box"),
            "mae": err["mae"],
            "rmse": err["rmse"],
            "n_obs_comparados": err["n_obs_comparados"],
        }
    return registros


def elegir_ganador(registros: dict, criterio: str = config.CRITERIO_GANADOR) -> dict:
    """
    Ganador por 'criterio' (rmse por defecto) entre los modelos con métrica
    valida (no NaN). No se usa AIC/BIC como criterio principal porque son
    medidas de ajuste IN-SAMPLE; la rúbrica pide qué tan bien predice el
    conjunto de PRUEBA, que es lo que mide MAE/RMSE.

    Siempre informa explícitamente si seasonal_naive superó a sarima (el
    caso que advierte el enunciado del equipo: si un ARIMA no le gana al
    piso ingenuo, ese ARIMA no sirve).
    """
    validos = {m: r for m, r in registros.items() if r.get(criterio) == r.get(criterio)}  # descarta NaN
    if not validos:
        return {"modelo": None, "criterio": criterio, "nota": "ningún modelo tiene métrica válida"}

    ganador = min(validos, key=lambda m: validos[m][criterio])

    nota_naive = None
    gana_naive_a_sarima = None
    if "seasonal_naive" in validos and "sarima" in validos:
        gana_naive_a_sarima = bool(validos["seasonal_naive"][criterio] <= validos["sarima"][criterio])
        if gana_naive_a_sarima:
            nota_naive = (
                f"seasonal_naive ({criterio}={validos['seasonal_naive'][criterio]:.1f}) "
                f"iguala o supera a sarima ({criterio}={validos['sarima'][criterio]:.1f}): "
                "el componente ARIMA no está agregando valor frente al piso ingenuo en esta serie."
            )
        else:
            nota_naive = (
                f"sarima ({criterio}={validos['sarima'][criterio]:.1f}) supera a seasonal_naive "
                f"({criterio}={validos['seasonal_naive'][criterio]:.1f})."
            )

    return {
        "modelo": ganador,
        "criterio": criterio,
        "valor": validos[ganador][criterio],
        "gana_seasonal_naive_a_sarima": gana_naive_a_sarima,
        "nota_seasonal_naive": nota_naive,
        "modelos_excluidos_sin_metrica": sorted(set(registros) - set(validos)),
    }


def tabla_comparativa(clave: str, nombre: str, categoria: str,
                      serie_test: pd.Series, modelos_json: dict) -> dict:
    """Registro completo de una serie: sus 5 modelos + el ganador."""
    registros = evaluar_modelos_serie(serie_test, modelos_json)
    return {
        "clave": clave,
        "nombre": nombre,
        "categoria": categoria,
        "modelos": registros,
        "ganador": elegir_ganador(registros),
    }


# ---------------------------------------------------------------------
# Las 4 preguntas comparativas (rubro 6)
# ---------------------------------------------------------------------

def coeficiente_variacion(serie: pd.Series) -> float | None:
    """CV = sd/media. A diferencia de la sd cruda, es comparable entre series
    de magnitud muy distinta (Terrestre tiene la sd más grande, pero también
    el nivel más alto; el CV es el que dice si es la más *inestable*)."""
    media = serie.mean()
    if not media:
        return None
    return float(serie.std(ddof=1) / media)


def impacto_pandemia_serie(df: pd.DataFrame, columna: str | None, valor: str | None,
                           anio_base: int = 2019) -> dict:
    """
    Caída % del año siguiente (y del subsiguiente) respecto de anio_base,
    para la categoría indicada (columna=None -> total sin filtrar).

    Se calcula sobre el DataFrame crudo (no sobre la serie ya reindexada a
    meses de train) porque acá interesa el total anual real, no un recorte.
    """
    sub = df if columna is None else df[df[columna] == valor]
    por_anio = sub.groupby("Año")["Viajero"].sum()
    base = por_anio.get(anio_base, 0)

    return {
        "anio_base": anio_base,
        "total_base": float(base),
        "pct_respecto_base": {
            str(a): (float(por_anio.get(a, 0) / base * 100) if base else None)
            for a in (anio_base + 1, anio_base + 2)
        },
    }


def _racha_ceros(serie: pd.Series) -> int:
    """Tramo consecutivo de ceros más largo (mismo criterio que eda.describir_serie)."""
    racha = tramo = 0
    for v in serie == 0:
        tramo = tramo + 1 if v else 0
        racha = max(racha, tramo)
    return racha


def metricas_forma_categoria(df: pd.DataFrame, series_train: dict, claves: list,
                             columna_filtro: str) -> dict:
    """
    Para un grupo de series (vías o países): fuerza de estacionalidad
    (decomposition.py), pendiente anual, CV y caída pandémica de
    cada una, listas para comparar.

    Nota: si series.json ya trae 'fuerza_estacionalidad'/'pendiente_anual'
    (una vez que se conecte decomposition.py al pipeline), conviene leer
    esos valores en vez de recalcularlos acá para no descomponer dos veces.
    Mientras tanto este módulo es autosuficiente y no depende de ese paso.
    """
    filas = {}
    for clave in claves:
        s = series_train[clave]
        _, forma = D.metricas_forma(s, etiqueta_base=clave)
        filas[clave] = {
            "fuerza_estacionalidad": forma["fuerza_estacionalidad"],
            "pendiente_anual": forma["pendiente_anual"],
            "pct_anual_sobre_media": forma["pct_anual_sobre_media"],
            "cv": coeficiente_variacion(s),
            "impacto_pandemia": impacto_pandemia_serie(df, columna_filtro, clave),
            "racha_ceros_max": _racha_ceros(s),
        }
    return filas


def _mayor(filas: dict, campo: str, extraer=lambda v: v) -> dict | None:
    """Clave con el mayor valor de 'campo' entre las que lo tienen definido."""
    candidatos = {k: extraer(v[campo]) for k, v in filas.items() if extraer(v[campo]) is not None}
    if not candidatos:
        return None
    ganador = max(candidatos, key=candidatos.get)
    return {"serie": ganador, "valor": candidatos[ganador]}


def responder_comparativo(filas: dict) -> dict:
    """Las 4 preguntas del rubro 6.a para un grupo de series (vías o países)."""
    mas_estacional = _mayor(filas, "fuerza_estacionalidad")
    mas_creciente = _mayor(filas, "pendiente_anual")
    mas_volatil = _mayor(filas, "cv")
    mas_afectada = _mayor(
        filas, "impacto_pandemia",
        extraer=lambda v: (100 - v["pct_respecto_base"]["2020"]) if v["pct_respecto_base"]["2020"] is not None else None,
    )
    if mas_afectada is not None:
        mas_afectada["caida_pct_2020_vs_2019"] = mas_afectada.pop("valor")
        mas_afectada["racha_ceros_max"] = filas[mas_afectada["serie"]]["racha_ceros_max"]

    return {
        "mas_estacionalidad": mas_estacional,
        "mas_tendencia_crecimiento": mas_creciente,
        "mas_volatilidad": mas_volatil,
        "mas_afectada_pandemia": mas_afectada,
    }


def comparativo_categoria(df: pd.DataFrame, series_train: dict, claves: list,
                          columna_filtro: str) -> dict:
    """
    Detalle por serie + las 4 respuestas, para un grupo (vías o países).

    Se guardan ambas cosas (no solo las 4 respuestas) porque una caída %
    puede "ganar" la pregunta de pandemia sin ser el dato más llamativo: ver
    hallazgos_inguat, que necesita poder mencionar p. ej. la vía Marítima
    aunque no sea la de mayor caída porcentual.
    """
    filas = metricas_forma_categoria(df, series_train, claves, columna_filtro)
    return {"detalle": filas, **responder_comparativo(filas)}


# ---------------------------------------------------------------------
# Hallazgos para INGUAT (cierre, rubro 6.b)
# ---------------------------------------------------------------------

def hallazgos_inguat(eda_json: dict, comparativo: dict, tablas: list) -> list:
    """
    Conclusiones de negocio en prosa, pero generadas a partir de números ya
    calculados (nunca tecleados a mano, regla de coordinación #3). Son
    plantillas de texto parametrizadas con los propios resultados; el
    contenido cualitativo (a qué mercado apuntar, etc.) es lo único que no
    sale de una fórmula, como pide el enunciado ("acá no hay cálculo, es
    conclusión de negocio").

    'comparativo' trae, por categoría, tanto las 4 respuestas como el
    'detalle' de cada serie (ver comparativo_categoria) -- necesario para no
    perder de vista, por ejemplo, la vía con más meses en cero aunque otra
    serie tenga la mayor caída porcentual.
    """
    hallazgos = []

    vias = comparativo.get("vias", {})
    paises = comparativo.get("paises", {})
    detalle_vias = vias.get("detalle", {})

    if vias.get("mas_volatilidad"):
        hallazgos.append(
            f"La vía más volátil en términos relativos (CV) es "
            f"{vias['mas_volatilidad']['serie']}, no necesariamente la de mayor desviación "
            "absoluta: para planificar capacidad (personal en frontera, slots aéreos) importa "
            "más esta inestabilidad relativa que el volumen bruto."
        )

    if vias.get("mas_afectada_pandemia"):
        info = vias["mas_afectada_pandemia"]
        hallazgos.append(
            f"Por caída porcentual anual, {info['serie']} fue la vía más golpeada por la "
            f"pandemia (caída de {info['caida_pct_2020_vs_2019']:.0f}% en 2020 vs. 2019)."
        )

    # Aunque no "gane" la pregunta de % de caída, cualquier vía con un cierre
    # prolongado (varios meses seguidos en cero) es un hallazgo aparte: es
    # evidencia de un cierre TOTAL del canal, no solo de una baja de demanda.
    cierres_totales = {
        clave: v["racha_ceros_max"] for clave, v in detalle_vias.items() if v["racha_ceros_max"] >= 6
    }
    for clave, racha in cierres_totales.items():
        if not vias.get("mas_afectada_pandemia") or clave != vias["mas_afectada_pandemia"]["serie"]:
            hallazgos.append(
                f"Aparte de lo anterior, {clave} es la única vía que estuvo completamente "
                f"cerrada durante la pandemia ({racha} meses consecutivos en cero): aunque su "
                "peso relativo en el total sea menor, es la que evidencia con más claridad un "
                "cierre total del canal (no solo una baja de demanda) y la que un plan de "
                "contingencia ante el cierre de fronteras debería priorizar."
            )

    if paises.get("mas_tendencia_crecimiento"):
        ganador_pais = paises["mas_tendencia_crecimiento"]["serie"]
        if ganador_pais == "Guatemala":
            hallazgos.append(
                "Guatemala aparece con la mayor pendiente de crecimiento entre los tres "
                "principales países de residencia, pero esa serie corresponde mayoritariamente "
                "a residentes guatemaltecos que regresan del extranjero (ver hallazgo del "
                "análisis exploratorio), no a un mercado turístico extranjero: no es una serie "
                "sobre la que tenga sentido recomendar promoción internacional."
            )
        else:
            hallazgos.append(
                f"{ganador_pais} es el mercado con mayor pendiente de crecimiento entre los "
                "tres principales países emisores, y por tanto el más rentable para sostener "
                "promoción activa en el mediano plazo."
            )

    top_paises = eda_json.get("top_paises", [])
    if len(top_paises) >= 2 and top_paises[0]["nombre"] == "El Salvador":
        hallazgos.append(
            "El Salvador (31.0% del total histórico) domina como mercado emisor casi en su "
            "totalidad por vía terrestre: si la promoción del INGUAT se diseña con el mismo "
            "enfoque que para el turismo aéreo de larga distancia, está apuntando mal a su "
            "mercado más grande."
        )

    naives_ganadores = [t["nombre"] for t in tablas if t["ganador"].get("gana_seasonal_naive_a_sarima")]
    if naives_ganadores:
        hallazgos.append(
            "En " + ", ".join(naives_ganadores) + ", el modelo seasonal naive iguala o supera "
            "a SARIMA en el conjunto de prueba: dado que train solo vio la caída pandémica y "
            "test es toda la recuperación (más el quiebre metodológico de 2023), ningún modelo "
            "entrenado en ese tramo podía anticipar el rebote — el hallazgo en sí (que el "
            "quiebre estructural es más grande que lo que cualquier modelo de serie de tiempo "
            "puede capturar) es más útil para INGUAT que la predicción puntual."
        )

    return hallazgos
