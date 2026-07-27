"""
Orquestacion. Une los modulos, genera las figuras y escribe results/*.json.

Los JSON son la fuente unica de verdad de los numeros del informe: el builder
solo los lee. Antes esos ~65 valores estaban transcritos a mano en el reporte.
"""

import json
import unicodedata

import pandas as pd

from src import config, data, eda, plots, series as S, stationarity as St

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

    detalle = []
    for clave, s in series.items():
        nombre = _etiqueta(clave)
        base = _nombre_figura(clave)
        f_panel = config.FIGDIR / f"{base}.png"
        f_acf = config.FIGDIR / f"{base}_acf.png"

        plots.panel_serie(s, nombre, f_panel)
        plots.acf_serie(s, nombre, f_acf)

        desc = eda.describir_serie(s)
        adf = St.adf_test(s)
        print(f"  {nombre}")
        print(f"     {desc['inicio']} a {desc['fin']} | {desc['frecuencia']} | n={desc['n_obs']} "
              f"| media {desc['media']:,.1f} | sd {desc['sd']:,.1f}")
        print(f"     ADF: stat {adf['stat']:.3f} | p {adf['pvalue']:.4f} -> "
              f"{'estacionaria' if adf['estacionaria'] else 'NO estacionaria'} en media")

        detalle.append({
            "clave": clave,
            "nombre": nombre,
            "categoria": _categoria(clave),
            # manifest: el reporte lee estas rutas en vez de reconstruirlas
            "fig_panel": f_panel.relative_to(config.ROOT).as_posix(),
            "fig_acf": f_acf.relative_to(config.ROOT).as_posix(),
            **desc,
            "adf": adf,
        })

    _escribir_json("series.json", {
        "periodo_estacional": config.PERIOD,
        "lags_acf": config.LAGS_ACF,
        "series": detalle,
    })
    return {"split": split, "series": detalle}


def correr_todo(usar_cache: bool = True) -> None:
    df = data.cargar(usar_cache=usar_cache)
    resumen = correr_eda(df)
    paises = [d["nombre"] for d in resumen["top_paises"][:config.TOP_N_PAISES]]
    correr_series(df, paises)
    print("\nListo. Figuras en figs/ y resultados en results/")
