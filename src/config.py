"""
Constantes y rutas del laboratorio.

Las rutas se derivan de __file__, no del directorio actual, para que el
pipeline corra igual desde cualquier parte (antes solo funcionaba si lo
ejecutabas parado en la raíz del repo).
"""

from pathlib import Path

# raiz del repo = carpeta padre de src/
ROOT = Path(__file__).resolve().parent.parent

DATA_PATH = ROOT / "Base_Migracion_2009-2026jun.xlsx"
SHEET_NAME = "Datos"

FIGDIR = ROOT / "figs"
RESULTSDIR = ROOT / "results"
CACHEDIR = ROOT / ".cache"
OUTPUTDIR = ROOT / "outputs"

CACHE_PATH = CACHEDIR / "migracion.csv"

# --- particion temporal -----------------------------------------------------
TRAIN_FRAC = 0.7
FREQ = "MS"  # inicio de mes

# --- analisis de series -----------------------------------------------------
PERIOD = 12       # periodo estacional (datos mensuales)
LAGS_ACF = 36     # rezagos en el grafico de autocorrelacion
ALPHA = 0.05      # nivel de significancia para ADF

# --- categorias -------------------------------------------------------------
VIAS = ["Aérea", "Terrestre", "Marítima"]
TIPOS_COMPARABLES = ["Turista", "Excursionista"]  # serie comparable en todo el rango
TOP_N_PAISES = 3

# --- calidad de datos -------------------------------------------------------
IQR_MULT = 1.5
CUANTILES = [0.25, 0.75]

# --- fechas de anotacion en graficos ---------------------------------------
PANDEMIA_INICIO = "2020-03-01"
PANDEMIA_FIN = "2021-12-01"
QUIEBRE_METODOLOGICO = "2023-01-01"

# --- estilo -----------------------------------------------------------------
DPI = 110
FONT_SIZE = 9

TEAL = "#0b6e6e"
AZUL = "#1f77b4"
NARANJA_OSCURO = "#c1440e"
AZUL_MEDIO = "#4c72b0"
VERDE = "#55a868"
MORADO = "#8172b2"
DURAZNO = "#dd8452"
