"""
Punto de entrada del laboratorio.

    python main.py eda        solo el analisis exploratorio (6 figuras + eda.json)
    python main.py series     particion + 7 series (14 figuras + split/series.json)
    python main.py modelos    ajusta los 5 modelos a las 7 series (models.json)
    python main.py prediccion series de prueba + MAE/RMSE + comparativo (comparison.json)
    python main.py all        todo el pipeline
    python main.py report     arma el PDF a partir de results/*.json

Opcional: --no-cache fuerza leer el Excel en vez del cache.
"""

import argparse
import json
import logging
import subprocess
import sys

from src import config, data, pipeline


def _stdout_utf8():
    """Sin esto la consola de Windows escupe mojibake en 'Aérea' o 'Región'."""
    try:
        sys.stdout.reconfigure(encoding="utf-8")
    except (AttributeError, OSError):
        pass


def _silenciar_cmdstanpy():
    """
    Prophet usa cmdstanpy, que escupe dos lineas de INFO por cada ajuste.
    Con 7 series eso son 14 lineas de ruido que tapan la salida del pipeline.
    """
    logging.getLogger("cmdstanpy").setLevel(logging.ERROR)


def _cmd_eda(args):
    df = data.cargar(usar_cache=not args.no_cache)
    pipeline.correr_eda(df)


def _cmd_series(args):
    df = data.cargar(usar_cache=not args.no_cache)
    resumen = pipeline.correr_eda(df)
    paises = [d["nombre"] for d in resumen["top_paises"][:config.TOP_N_PAISES]]
    pipeline.correr_series(df, paises)


def _ordenes_guardados():
    """
    Lee los d/D que dejo el analisis de estacionariedad en series.json.

    Si el archivo no existe todavia se devuelve None y correr_modelos usa su
    default; conviene correr antes 'series' para no modelar con d/D arbitrarios.
    """
    ruta = config.RESULTSDIR / "series.json"
    if not ruta.exists():
        print("Aviso: falta results/series.json; los modelos usaran d/D por defecto.\n"
              "       Corre 'python main.py series' antes para usar los reales.",
              file=sys.stderr)
        return None, None
    with open(ruta, encoding="utf-8") as fh:
        detalle = json.load(fh)["series"]
    return ({s["clave"]: s["diferenciacion"]["d"] for s in detalle},
            {s["clave"]: s["diferenciacion"]["D"] for s in detalle})


def _cmd_modelos(args):
    df = data.cargar(usar_cache=not args.no_cache)
    resumen = pipeline.correr_eda(df)
    paises = [d["nombre"] for d in resumen["top_paises"][:config.TOP_N_PAISES]]
    part = pipeline.S.particion(df)
    d_por_serie, D_por_serie = _ordenes_guardados()
    pipeline.correr_modelos(df, part, paises,
                            d_por_serie=d_por_serie, D_por_serie=D_por_serie)


def _cmd_prediccion(args):
    df = data.cargar(usar_cache=not args.no_cache)
    resumen = pipeline.correr_eda(df)
    paises = [d["nombre"] for d in resumen["top_paises"][:config.TOP_N_PAISES]]
    part = pipeline.S.particion(df)
    pipeline.correr_prediccion(df, part, paises)


def _cmd_all(args):
    pipeline.correr_todo(usar_cache=not args.no_cache)


def _cmd_report(args):
    """El builder es un script aparte; se invoca tal cual."""
    build = config.ROOT / "report" / "build.py"
    if not build.exists():
        print(f"No existe {build}", file=sys.stderr)
        return 1
    return subprocess.call([sys.executable, str(build)])


def main():
    parser = argparse.ArgumentParser(description="Laboratorio 1 - Series de Tiempo")
    parser.add_argument("comando", choices=["eda", "series", "modelos", "prediccion", "all", "report"])
    parser.add_argument("--no-cache", action="store_true",
                        help="lee el Excel directo, ignorando el cache")
    args = parser.parse_args()

    _stdout_utf8()
    _silenciar_cmdstanpy()
    return {
        "eda": _cmd_eda,
        "series": _cmd_series,
        "modelos": _cmd_modelos,
        "prediccion": _cmd_prediccion,
        "all": _cmd_all,
        "report": _cmd_report,
    }[args.comando](args) or 0


if __name__ == "__main__":
    sys.exit(main())
