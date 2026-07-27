"""
Punto de entrada del laboratorio.

    python main.py eda      solo el analisis exploratorio (6 figuras + eda.json)
    python main.py series    particion + 7 series (14 figuras + split/series.json)
    python main.py all       todo el pipeline
    python main.py report    arma el PDF a partir de results/*.json

Opcional: --no-cache fuerza leer el Excel en vez del cache.
"""

import argparse
import subprocess
import sys

from src import config, data, pipeline


def _stdout_utf8():
    """Sin esto la consola de Windows escupe mojibake en 'Aérea' o 'Región'."""
    try:
        sys.stdout.reconfigure(encoding="utf-8")
    except (AttributeError, OSError):
        pass


def _cmd_eda(args):
    df = data.cargar(usar_cache=not args.no_cache)
    pipeline.correr_eda(df)


def _cmd_series(args):
    df = data.cargar(usar_cache=not args.no_cache)
    resumen = pipeline.correr_eda(df)
    paises = [d["nombre"] for d in resumen["top_paises"][:config.TOP_N_PAISES]]
    pipeline.correr_series(df, paises)


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
    parser.add_argument("comando", choices=["eda", "series", "all", "report"])
    parser.add_argument("--no-cache", action="store_true",
                        help="lee el Excel directo, ignorando el cache")
    args = parser.parse_args()

    _stdout_utf8()
    return {
        "eda": _cmd_eda,
        "series": _cmd_series,
        "all": _cmd_all,
        "report": _cmd_report,
    }[args.comando](args) or 0


if __name__ == "__main__":
    sys.exit(main())
