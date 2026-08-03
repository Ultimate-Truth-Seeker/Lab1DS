"""
Orquestacion. Une los modulos, genera las figuras y escribe results/*.json.

Los JSON son la fuente unica de verdad de los numeros del informe: el builder
solo los lee. Antes esos ~65 valores estaban transcritos a mano en el reporte.
"""

import json
import unicodedata

import pandas as pd

from src import config, data, decomposition, eda, plots, series as S, stationarity as St
from src import comparison as Cmp, evaluation as E, models as M, transform as T
from src import lstm as L
from src import catch22 as C22
from src import catch22_analysis as C22A

# nombre para mostrar de cada serie, por clave
_ETIQUETAS = {"total": "Total mensual de viajeros internacionales"}


def _escribir_json(nombre: str, payload: dict) -> None:
    """UTF-8 y ensure_ascii=False explicitos: en Windows el default es cp1252
    y corrompe 'Aérea' justo en el archivo que es fuente de verdad."""
    config.RESULTSDIR.mkdir(parents=True, exist_ok=True)
    ruta = config.RESULTSDIR / nombre
    with open(ruta, "w", encoding="utf-8") as fh:
        json.dump(payload, fh, ensure_ascii=False, indent=2)
    print(f"  -> {ruta.relative_to(config.ROOT)}")

def _serializar_modelo(resultado: dict) -> dict:
    """
    Convierte un resultado de models.py a un formato serializable a JSON.
    """

    salida = resultado.copy()

    if "forecast" in salida and salida["forecast"] is not None:
        salida["forecast"] = {
            fecha.strftime("%Y-%m"): float(valor)
            for fecha, valor in salida["forecast"].items()
        }

    if "residuos" in salida and salida["residuos"] is not None:
        salida["residuos"] = list(
            map(float, salida["residuos"].dropna().values)
        )

    salida.pop("fit", None)

    return salida

def _etiqueta(clave: str) -> str:
    if clave in _ETIQUETAS:
        return _ETIQUETAS[clave]
    if clave in config.VIAS:
        return f"Vía de ingreso: {clave}"
    return f"País de residencia: {clave}"


def _categoria(clave: str) -> str:
    if clave == "total":
        return "obligatoria"
    return "via" if clave in config.VIAS else "pais"


def slug(texto: str) -> str:
    """
    Nombre apto para archivo: sin acentos ni espacios.

    Los nombres con tilde ('11_serie_via_Aérea.png') daban problemas al viajar
    entre git, Windows y la consola. Se normaliza a NFD y se descartan los
    diacriticos, asi 'Aérea' queda 'Aerea' y 'Marítima' queda 'Maritima'.
    """
    sin_tilde = "".join(
        c for c in unicodedata.normalize("NFD", texto)
        if unicodedata.category(c) != "Mn"
    )
    return sin_tilde.replace(" ", "_")


def _nombre_figura(clave: str) -> str:
    """Prefijo por categoria: 10 la obligatoria, 11 vias, 12 paises."""
    if clave == "total":
        return "10_serie_total"
    if clave in config.VIAS:
        return f"11_serie_via_{slug(clave)}"
    return f"12_serie_pais_{slug(clave)}"


def _nombre_figura_completo(clave: str) -> str:
    """Igual que _nombre_figura pero para las series del periodo completo (2x)."""
    if clave == "total":
        return "20_completo_total"
    if clave in config.VIAS:
        return f"21_completo_via_{slug(clave)}"
    return f"22_completo_pais_{slug(clave)}"


def correr_eda(df: pd.DataFrame) -> dict:
    """Metricas y las 6 figuras exploratorias."""
    print("\n=== Analisis exploratorio ===")

    mensual_total = df.groupby("Fecha")["Viajero"].sum().sort_index()
    tur_exc = df[df["Tipo de Viajero"].isin(config.TIPOS_COMPARABLES)]
    mensual_comparable = tur_exc.groupby("Fecha")["Viajero"].sum().sort_index()

    via_tot = df.groupby("Vía")["Viajero"].sum().sort_values(ascending=False)
    frontera_tot = df.groupby("Frontera")["Viajero"].sum().sort_values(ascending=False)
    tipo_tot = df.groupby("Tipo de Viajero")["Viajero"].sum().sort_values(ascending=False)
    paises_tot = df.groupby("País")["Viajero"].sum().sort_values(ascending=False)
    regiones_tot = df.groupby("Región dos")["Viajero"].sum().sort_values(ascending=False)

    dim = eda.dimensiones(df)
    cal = eda.calidad(df)
    des = eda.descriptivos(df)

    print(f"  registros: {dim['filas']:,} | columnas fuente: {dim['columnas_fuente']}")
    print(f"  faltantes: {cal['faltantes_total']} | duplicados: {cal['duplicados_exactos']} "
          f"| ceros: {cal['ceros']} | negativos: {cal['negativos']}")
    print(f"  IQR umbral superior: {cal['iqr_umbral_superior']:.1f} "
          f"({cal['iqr_filas_sobre_umbral']:,} filas, {cal['iqr_pct_sobre_umbral']:.1f}%)")
    print(f"  Viajero por registro: media {des['media']:.2f} | mediana {des['mediana']:.2f} "
          f"| max {des['max']:,.2f}")

    plots.temporal_total(mensual_total, config.FIGDIR / "01_temporal_total.png")
    plots.temporal_comparable(mensual_comparable, config.FIGDIR / "02_temporal_comparable.png")
    plots.top_paises(paises_tot, config.FIGDIR / "03_top_paises.png")
    plots.top_regiones(regiones_tot, config.FIGDIR / "04_top_regiones.png")
    plots.vias_fronteras(via_tot, frontera_tot, config.FIGDIR / "05_vias_fronteras.png")
    plots.distribuciones(df["Viajero"], tipo_tot, config.FIGDIR / "06_distribuciones.png")
    print("  6 figuras exploratorias generadas")

    payload = {
        "dataset": dim,
        "calidad": cal,
        "descriptivos_viajero": des,
        "quiebre_metodologico": eda.quiebre_metodologico(df),
        "cuasi_duplicados": eda.cuasi_duplicados(df),
        "region_sin_asignar": eda.region_sin_asignar(df),
        "impacto_pandemia": eda.impacto_pandemia(df),
        "top_paises": eda.acumulados(df, "País", top=10),
        "regiones": eda.acumulados(df, "Región dos"),
        "vias": eda.acumulados(df, "Vía"),
        "fronteras": eda.acumulados(df, "Frontera", top=10),
        "tipos_viajero": eda.acumulados(df, "Tipo de Viajero"),
    }
    _escribir_json("eda.json", payload)
    return payload


def correr_series(df: pd.DataFrame, paises: list) -> dict:
    """Particion, 7 series, sus 14 figuras y el analisis preliminar."""
    print("\n=== Particion y series ===")
    part = S.particion(df)

    n_test = len(part["meses"]) - part["n_train"]
    print(f"  meses: {len(part['meses'])} | train: {part['n_train']} "
          f"({part['meses'][0]:%Y-%m} a {part['corte']:%Y-%m}) | "
          f"test: {n_test} ({part['inicio_test']:%Y-%m} a {part['meses'][-1]:%Y-%m})")
    print(f"  filas train: {len(part['train']):,} | test: {len(part['test']):,}")

    split = {
        "n_meses_total": len(part["meses"]),
        "train_frac_objetivo": config.TRAIN_FRAC,
        "corte": part["corte"].strftime("%Y-%m"),
        "train": {
            "inicio": part["meses"][0].strftime("%Y-%m"),
            "fin": part["corte"].strftime("%Y-%m"),
            "n_meses": part["n_train"],
            "pct_meses": part["n_train"] / len(part["meses"]) * 100,
            "filas": len(part["train"]),
            "pct_filas": len(part["train"]) / len(df) * 100,
        },
        "test": {
            "inicio": part["inicio_test"].strftime("%Y-%m"),
            "fin": part["meses"][-1].strftime("%Y-%m"),
            "n_meses": n_test,
            "pct_meses": n_test / len(part["meses"]) * 100,
            "filas": len(part["test"]),
            "pct_filas": len(part["test"]) / len(df) * 100,
        },
    }
    _escribir_json("split.json", split)

    print(f"\n  top-{config.TOP_N_PAISES} paises (acumulado de todo el periodo): {paises}")
    series = S.construir_series(part["train"], part["meses_train"], paises)

    # Las mismas 7 series pero sobre los 210 meses. Solo para graficar el
    # comportamiento pos-pandemia: el modelado usa unicamente entrenamiento.
    series_completas = S.construir_series(df, part["meses"], paises)

    detalle = []
    for clave, s in series.items():
        nombre = _etiqueta(clave)
        base = _nombre_figura(clave)
        f_panel = config.FIGDIR / f"{base}.png"
        f_acf = config.FIGDIR / f"{base}_acf.png"
        f_pacf = config.FIGDIR / f"{base}_pacf.png"
        f_completo = config.FIGDIR / f"{_nombre_figura_completo(clave)}.png"

        # --- estacionariedad en varianza -> transformacion
        s_t, varianza, transformacion = T.decidir(s)

        # Dos descomposiciones distintas, no es un descuido:
        #  - la del nivel es solo para dibujar el panel, que se lee mejor en
        #    viajeros que en logaritmos (de ahi el _ que descarta sus metricas);
        #  - la de la serie transformada es la que se cita en el informe.
        dec_nivel, _ = decomposition.metricas_forma(s, etiqueta_base="nivel")
        _, forma = decomposition.metricas_forma(s_t, etiqueta_base=transformacion["nombre"])

        # --- estacionariedad en media -> cuantas diferenciaciones
        ordenes = St.determinar_ordenes(s_t, forma["fuerza_estacionalidad"],
                                        serie_base=transformacion["nombre"])
        s_final = St.diferenciar(s_t, d=ordenes["d"], D=ordenes["D"])

        plots.panel_serie(s, nombre, f_panel, dec=dec_nivel)
        plots.acf_serie(s, nombre, f_acf)
        plots.pacf_serie(s_final, nombre, f_pacf, subtitulo=ordenes["orden_recomendado"])
        plots.serie_periodo_completo(series_completas[clave], nombre, f_completo,
                                     corte_train=part["corte"])

        desc = eda.describir_serie(s)
        adf = St.adf_test(s)
        pruebas = {
            "nivel": St.pruebas_conjuntas(s),
            "transformada": St.pruebas_conjuntas(s_t),
            "final": St.pruebas_conjuntas(s_final),
        }

        print(f"  {nombre}")
        print(f"     {desc['inicio']} a {desc['fin']} | {desc['frecuencia']} | n={desc['n_obs']} "
              f"| media {desc['media']:,.1f} | sd {desc['sd']:,.1f}")
        print(f"     ADF nivel: stat {adf['stat']:.3f} | p {adf['pvalue']:.4f} -> "
              f"{'estacionaria' if adf['estacionaria'] else 'NO estacionaria'} en media")
        if not forma["descomposicion_ok"]:
            print(f"     ADVERTENCIA: descomposicion fallida")
        else:
            print(f"     forma: fuerza estacional {forma['fuerza_estacionalidad']:.3f} "
                  f"| tendencia {forma['tendencia_signo']}")
        print(f"     orden: {ordenes['orden_recomendado']} | estacionaria: "
              f"{ordenes['estacionaria_final']}")

        detalle.append({
            "clave": clave,
            "nombre": nombre,
            "categoria": _categoria(clave),
            # manifest: el reporte lee estas rutas en vez de reconstruirlas
            "fig_panel": f_panel.relative_to(config.ROOT).as_posix(),
            "fig_acf": f_acf.relative_to(config.ROOT).as_posix(),
            "fig_pacf": f_pacf.relative_to(config.ROOT).as_posix(),
            "fig_periodo_completo": f_completo.relative_to(config.ROOT).as_posix(),
            **desc,
            "adf": adf,
            "forma": forma,
            "varianza": varianza,
            "transformacion": transformacion,
            "diferenciacion": ordenes,
            "pruebas": pruebas,
        })

    _escribir_json("series.json", {
        "periodo_estacional": config.PERIOD,
        "lags_acf": config.LAGS_ACF,
        "lags_pacf": config.LAGS_PACF,
        "n_meses_periodo_completo": len(part["meses"]),
        "umbral_estacionalidad_fuerte": config.FUERZA_ESTACIONAL_UMBRAL,
        "umbral_corr_varianza": config.CORR_VARIANZA_UMBRAL,
        "pre_pandemia_fin": config.PRE_PANDEMIA_FIN,
        "series": detalle,
    })
    return {"split": split, "series": detalle}


def correr_modelos(df: pd.DataFrame, part: dict, paises: list,
                   d_por_serie: dict | None = None, D_por_serie: dict | None = None) -> dict:
    """
    Ajusta los 5 modelos a las 7 series y escribe results/models.json.

    d/D vienen del analisis de estacionariedad (series.json -> diferenciacion),
    que correr_todo pasa por serie. El default 1,1 solo aplica si se llama a
    esta funcion sola, sin haber corrido antes correr_series.
    """
    print("\n=== Modelos ===")
    horizon = len(part["meses"]) - part["n_train"]
    series_train = S.construir_series(part["train"], part["meses_train"], paises)

    detalle = []
    for clave, s in series_train.items():
        d = (d_por_serie or {}).get(clave, 1)
        D = (D_por_serie or {}).get(clave, 1)

        # se ajusta sobre la serie transformada (si transform.decidir lo pide)
        # y se invierte SOLO el forecast antes de guardarlo: el resto del
        # pipeline compara contra la serie real, en viajeros, no en
        # escala logaritmica.
        s_transformada, _, transf = T.decidir(s)
        ajustes = M.ajustar_todos(s_transformada, horizon, d=d, D=D)

        modelos_json = {}
        for nombre_modelo, res in ajustes.items():
            res = E.agregar_diagnostico(res)
            forecast_real = T.invertir(res["forecast"], transf["nombre"])
            modelos_json[nombre_modelo] = {
                "parametros": res["parametros"],
                "aic": res["aic"],
                "bic": res["bic"],
                "ljung_box": res["ljung_box"],
                "forecast": {ts.strftime("%Y-%m"): float(v) for ts, v in forecast_real.items()},
            }

        nombre = _etiqueta(clave)
        print(f"  {nombre}: {', '.join(modelos_json)} | transformación: {transf['nombre']} (d={d}, D={D})")

        detalle.append({
            "clave": clave,
            "nombre": nombre,
            "transformacion": transf["nombre"],
            "d": d,
            "D": D,
            "modelos": modelos_json,
        })

    payload = {"horizon": horizon, "series": detalle}
    _escribir_json("models.json", payload)
    return payload


def correr_lstm(df: pd.DataFrame, part: dict, paises: list,
                claves: list | None = None) -> dict:
    """
    Ajusta las redes LSTM del Laboratorio 2 y escribe results/lstm.json.

    Va en un JSON aparte y no dentro de models.json por dos razones: models.json
    es el artefacto ya entregado del laboratorio anterior (regenerarlo implicaria
    repetir el grid de SARIMA de las 7 series), y el LSTM solo cubre 2 series, asi
    que meterlo ahi dejaria un archivo con 5 series incompletas.

    El horizonte y la particion son los mismos del Lab 1, que es justo lo que pide
    el enunciado para poder comparar.
    """
    print("\n=== LSTM ===")
    horizon = len(part["meses"]) - part["n_train"]
    series_train = S.construir_series(part["train"], part["meses_train"], paises)
    objetivo = claves if claves is not None else config.LSTM_SERIES

    detalle = []
    for clave in objetivo:
        if clave not in series_train:
            print(f"  (no existe la serie '{clave}', se omite)")
            continue

        s_transformada, _, transf = T.decidir(series_train[clave])
        ajustes = L.ajustar_todas_configs(s_transformada, horizon)

        modelos_json = {}
        for nombre_modelo, res in ajustes.items():
            # se llama a ljung_box directo y no a agregar_diagnostico: ese helper
            # espera un modelo de statsmodels y pisaria aic/bic con None
            lb = E.ljung_box(res["residuos"])
            forecast_real = T.invertir(res["forecast"], transf["nombre"])
            modelos_json[nombre_modelo] = {
                "parametros": res["parametros"],
                "aic": res["aic"],
                "bic": res["bic"],
                "ljung_box": lb,
                "forecast": {ts.strftime("%Y-%m"): float(v) for ts, v in forecast_real.items()},
            }

            p = res["parametros"]
            ap = p["aplanamiento"]
            print(f"  {_etiqueta(clave)} / {nombre_modelo}: "
                  f"epochs={p['epochs_usadas']} (tuneo sobre {p['tuneo']['val_meses']} meses) "
                  f"| loss={p['loss_final']:.4f} | aplanado={ap['aplanado']}")

        detalle.append({
            "clave": clave,
            "nombre": _etiqueta(clave),
            "transformacion": transf["nombre"],
            "modelos": modelos_json,
        })

    payload = {"horizon": horizon, "semilla": config.LSTM_SEMILLA, "series": detalle}
    _escribir_json("lstm.json", payload)
    return payload


def correr_catch22(df: pd.DataFrame, part: dict, paises: list,
                   claves: list | None = None) -> dict:
    """
    Extrae las 22 caracteristicas de catch22 y escribe results/catch22.json.

    A diferencia del LSTM, que trabaja dos series, aca van las 7: el enunciado
    pide las caracteristicas de cada serie temporal construida.

    Se usan las series de entrenamiento, las mismas del laboratorio anterior, en
    su escala original (sin log1p): catch22 ya normaliza internamente lo que
    necesita, y transformarlas cambiaria caracteristicas como la asimetria.
    """
    print("\n=== catch22 ===")
    series_train = S.construir_series(part["train"], part["meses_train"], paises)

    objetivo = claves if claves is not None else config.CATCH22_SERIES
    if objetivo is not None:
        series_train = {k: v for k, v in series_train.items() if k in objetivo}

    payload = C22.matriz(series_train)
    print(f"  {payload['n_series']} series x {payload['n_features']} caracteristicas")
    if payload["estandarizacion"]["columnas_constantes"]:
        print(f"  aviso: {payload['estandarizacion']['columnas_constantes']} "
              f"caracteristicas constantes entre series")

    _escribir_json("catch22.json", payload)
    return payload

def correr_catch22_analysis() -> dict:
    """
    Análisis estadístico de las características catch22.

    Requiere que exista results/catch22.json.
    """

    print("\n=== Análisis catch22 ===")

    ruta = config.RESULTSDIR / "catch22.json"

    if not ruta.exists():
        raise FileNotFoundError(
            f"No existe {ruta}. Ejecute primero correr_catch22()."
        )

    with open(ruta, encoding="utf-8") as fh:
        payload = json.load(fh)

    resultado = C22A.analizar(payload)

    figs = {}

    figs["pca"] = (
        config.FIGDIR /
        "30_pca.png"
    )

    figs["clusters"] = (
        config.FIGDIR /
        "31_clusters.png"
    )

    figs["heatmap"] = (
        config.FIGDIR /
        "32_heatmap.png"
    )

    figs["correlaciones"] = (
        config.FIGDIR /
        "33_correlaciones.png"
    )

    figs["distancias"] = (
        config.FIGDIR /
        "34_distancias.png"
    )

    plots.plot_pca(
        resultado["pca"]["proyeccion"],
        figs["pca"],
    )

    plots.plot_clusters(
        resultado["pca"]["proyeccion"],
        resultado["clustering"]["asignacion"],
        figs["clusters"],
    )

    plots.plot_heatmap(
        payload["matriz_estandarizada"],
        payload["series"],
        payload["features"],
        figs["heatmap"],
    )

    plots.plot_correlaciones(
        resultado["correlaciones"],
        payload["features"],
        figs["correlaciones"],
    )

    plots.plot_distancias(
        resultado["distancias"]["matriz"],
        payload["series"],
        figs["distancias"],
    )

    resultado["figuras"] = {
        nombre: ruta.relative_to(config.ROOT).as_posix()
        for nombre, ruta in figs.items()
    }

    _escribir_json(
        "catch22_analysis.json",
        resultado,
    )

    return resultado

def correr_catch22_modelo(df: pd.DataFrame, part: dict, paises: list,
                          claves: list | None = None) -> dict:
    """
    Inciso 2.14: LSTM con las features de catch22 como entrada extra.

    Para cada serie en 'claves' (default: config.LSTM_SERIES, o sea las
    mismas 2 series del inciso 1.1) entrena lstm_catch22 y lo compara contra
    el mejor de lstm_c1/lstm_c2 YA guardado en results/lstm.json, evaluando
    ambos con el mismo conjunto de prueba (mismo criterio que comparison.py,
    para que la comparacion sea justa). Escribe results/catch22_modelo.json.
    """
    print("\n=== catch22 + LSTM (2.14) ===")

    ruta_c22 = config.RESULTSDIR / "catch22.json"
    if not ruta_c22.exists():
        raise FileNotFoundError(f"No existe {ruta_c22}. Ejecute primero 'catch22'.")
    with open(ruta_c22, encoding="utf-8") as fh:
        c22 = json.load(fh)
    vector_por_serie = dict(zip(c22["series"], c22["matriz_estandarizada"]))

    objetivo = claves if claves is not None else config.LSTM_SERIES
    horizon = len(part["meses"]) - part["n_train"]
    series_train = S.construir_series(part["train"], part["meses_train"], paises)
    series_test = Cmp.construir_series_test(df, part, paises)

    ruta_lstm = config.RESULTSDIR / "lstm.json"
    modelos_existentes = {}
    if ruta_lstm.exists():
        with open(ruta_lstm, encoding="utf-8") as fh:
            for s in json.load(fh)["series"]:
                modelos_existentes[s["clave"]] = s["modelos"]
    else:
        print("  aviso: no existe results/lstm.json; se entrena lstm_catch22 "
              "pero no se puede comparar contra lstm_c1/lstm_c2.")

    detalle = []
    for clave in objetivo:
        if clave not in vector_por_serie:
            print(f"  (no hay vector catch22 para '{clave}', se omite)")
            continue
        if clave not in series_train:
            print(f"  (no existe la serie '{clave}', se omite)")
            continue

        vector = vector_por_serie[clave]
        s_transformada, _, transf = T.decidir(series_train[clave])

        tuneo = L.tunear_epochs_catch22(s_transformada, vector)
        res = L.ajustar_lstm_catch22(s_transformada, horizon, vector,
                                     epochs_override=tuneo["mejor"], tuneo=tuneo)

        lb = E.ljung_box(res["residuos"])
        forecast_real = T.invertir(res["forecast"], transf["nombre"])

        err_nuevo = None
        if clave in series_test:
            err_nuevo = E.metricas_error(series_test[clave], forecast_real)

        # el/los mejor(es) LSTM ya existentes para esta serie, evaluados
        # contra el MISMO conjunto de prueba (no se reusa el mae/rmse de
        # comparison.json a ciegas: si ese JSON quedo desactualizado,
        # aca se recalcula igual que hace comparison.py)
        comparables = {}
        for nombre_modelo, info in modelos_existentes.get(clave, {}).items():
            if clave not in series_test:
                break
            f = Cmp.forecast_a_serie(info.get("forecast", {}))
            err = E.metricas_error(series_test[clave], f)
            comparables[nombre_modelo] = err

        mejor_existente = (min(comparables, key=lambda m: comparables[m]["rmse"])
                           if comparables else None)

        modelo_json = {
            "parametros": res["parametros"],
            "aic": res["aic"],
            "bic": res["bic"],
            "ljung_box": lb,
            "forecast": {ts.strftime("%Y-%m"): float(v) for ts, v in forecast_real.items()},
            "mae": err_nuevo["mae"] if err_nuevo else None,
            "rmse": err_nuevo["rmse"] if err_nuevo else None,
            "n_obs_comparados": err_nuevo["n_obs_comparados"] if err_nuevo else None,
        }

        gana_catch22 = None
        if err_nuevo and mejor_existente:
            gana_catch22 = bool(err_nuevo["rmse"] < comparables[mejor_existente]["rmse"])

        registro = {
            "clave": clave,
            "nombre": _etiqueta(clave),
            "transformacion": transf["nombre"],
            "lstm_catch22": modelo_json,
            "mejor_lstm_existente": {
                "modelo": mejor_existente,
                "mae": comparables[mejor_existente]["mae"] if mejor_existente else None,
                "rmse": comparables[mejor_existente]["rmse"] if mejor_existente else None,
            },
            "gana_lstm_catch22": gana_catch22,
        }
        detalle.append(registro)

        if err_nuevo and mejor_existente:
            print(f"  {_etiqueta(clave)}: lstm_catch22 rmse={err_nuevo['rmse']:.1f} "
                  f"vs {mejor_existente} rmse={comparables[mejor_existente]['rmse']:.1f} "
                  f"-> {'gana lstm_catch22' if gana_catch22 else 'gana el existente'}")
        else:
            print(f"  {_etiqueta(clave)}: lstm_catch22 entrenado "
                  f"(epochs={tuneo['mejor']}, loss={res['parametros']['loss_final']:.4f}); "
                  "comparacion incompleta por falta de lstm.json o serie de prueba")

    payload = {"horizon": horizon, "semilla": config.LSTM_SEMILLA, "series": detalle}
    _escribir_json("catch22_modelo.json", payload)
    return payload


def correr_prediccion(df: pd.DataFrame, part: dict, paises: list) -> dict:
    """
    Predicción y análisis comparativo 

    Requiere que exista results/models.json (ver correr_modelos). Construye
    las series de PRUEBA -- nadie las había armado --, calcula MAE/RMSE de
    cada modelo contra esas series, arma la tabla comparativa por serie
    (AIC/BIC + MAE/RMSE propios) y responde las 4 preguntas de la
    sección 6 para vías y países. Escribe results/comparison.json.
    """
    ruta_modelos = config.RESULTSDIR / "models.json"
    if not ruta_modelos.exists():
        raise FileNotFoundError(
            f"No existe {ruta_modelos}. Hay que correr el paso de modelos "
            "(correr_modelos) antes de la predicción."
        )
    with open(ruta_modelos, encoding="utf-8") as fh:
        models_json = json.load(fh)
    modelos_por_clave = {s["clave"]: dict(s["modelos"]) for s in models_json["series"]}

    # Los LSTM del Lab 2 se suman a la comparacion si ya se corrieron. Comparten
    # el esquema por modelo con models.json, asi que comparison.py los evalua sin
    # cambio alguno y elegir_ganador compite LSTM contra los modelos del Lab 1.
    ruta_lstm = config.RESULTSDIR / "lstm.json"
    if ruta_lstm.exists():
        with open(ruta_lstm, encoding="utf-8") as fh:
            for s in json.load(fh)["series"]:
                modelos_por_clave.setdefault(s["clave"], {}).update(s["modelos"])

    print("\n=== Predicción y comparativo ===")
    series_test = Cmp.construir_series_test(df, part, paises)
    series_train = S.construir_series(part["train"], part["meses_train"], paises)

    tablas = []
    for clave, s_test in series_test.items():
        if clave not in modelos_por_clave:
            print(f"  (sin modelos para '{clave}' en models.json, se omite)")
            continue

        nombre = _etiqueta(clave)
        tabla = Cmp.tabla_comparativa(clave, nombre, _categoria(clave), s_test, modelos_por_clave[clave])

        forecasts = {m: Cmp.forecast_a_serie(info.get("forecast", {}))
                    for m, info in modelos_por_clave[clave].items()}
        f_forecast = config.FIGDIR / f"20_forecast_{slug(clave)}.png"
        plots.forecast_vs_real(series_train[clave], s_test, forecasts, nombre, f_forecast)
        tabla["fig_forecast"] = f_forecast.relative_to(config.ROOT).as_posix()
        tablas.append(tabla)

        g = tabla["ganador"]
        if g.get("modelo"):
            print(f"  {nombre}: gana {g['modelo']} ({g['criterio']}={g['valor']:.1f})")
        else:
            print(f"  {nombre}: {g.get('nota', 'sin ganador')}")

    comparativo = {
        "vias": Cmp.comparativo_categoria(df, series_train, config.VIAS, "Vía"),
        "paises": Cmp.comparativo_categoria(df, series_train, paises, "País"),
    }

    with open(config.RESULTSDIR / "eda.json", encoding="utf-8") as fh:
        eda_json = json.load(fh)
    hallazgos = Cmp.hallazgos_inguat(eda_json, comparativo, tablas)

    payload = {
        "criterio_ganador": config.CRITERIO_GANADOR,
        "series": tablas,
        "comparativo": comparativo,
        "hallazgos_inguat": hallazgos,
    }
    _escribir_json("comparison.json", payload)
    return payload


def correr_todo(usar_cache: bool = True) -> None:
    df = data.cargar(usar_cache=usar_cache)
    resumen = correr_eda(df)
    paises = [d["nombre"] for d in resumen["top_paises"][:config.TOP_N_PAISES]]
    res_series = correr_series(df, paises)

    # los d/D salen del analisis de estacionariedad, no del default 1,1: sin
    # esto los modelos quedan sobre-diferenciados (D=1 cuando el criterio de
    # fuerza estacional da D=0 en las 7 series)
    d_por_serie = {s["clave"]: s["diferenciacion"]["d"] for s in res_series["series"]}
    D_por_serie = {s["clave"]: s["diferenciacion"]["D"] for s in res_series["series"]}

    part = S.particion(df)
    correr_modelos(df, part, paises, d_por_serie=d_por_serie, D_por_serie=D_por_serie)
    correr_lstm(df, part, paises)
    correr_catch22(df, part, paises)
    correr_catch22_analysis()
    correr_catch22_modelo(df, part, paises)
    correr_prediccion(df, part, paises)
    print("\nListo. Figuras en figs/ y resultados en results/")
