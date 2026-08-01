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
LAGS_PACF = 36    # rezagos en el grafico de autocorrelacion parcial
ALPHA = 0.05      # nivel de significancia para ADF y KPSS

# --- estacionariedad --------------------------------------------------------
# umbral de estacionalidad fuerte (Hyndman, fpp3). Por encima de esto se
# justifica una diferenciacion estacional; aca las 7 series quedan por debajo.
FUERZA_ESTACIONAL_UMBRAL = 0.64

# si corr(sd_anual, media_anual) supera esto, la varianza depende del nivel
CORR_VARIANZA_UMBRAL = 0.50
TRAMO_VARIANZA = 12   # tamaño del tramo para medir sd y media (12 meses = 1 año)

# El chequeo de varianza se hace SOLO hasta esta fecha, a proposito. Medido
# sobre la serie completa de train, corr(sd,media) sale baja o negativa en 6 de
# las 7 series, o sea "no transformar"; excluyendo la pandemia sale 0.89-0.96 en
# las 7. El colapso de 2020-2021 mete un tramo de nivel bajo y varianza alta que
# rompe la relacion monotona y enmascara el diagnostico.
PRE_PANDEMIA_FIN = "2020-02-01"

TRANSFORMACION = "log1p"  # log(1+x): admite los ceros exactos de Marítima
D_MAX = 1        # tope de diferenciaciones estacionales
DIFF_MAX = 2     # tope de diferenciaciones regulares

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

# NOTA: FUERZA_ESTACIONAL_UMBRAL, TRAMO_VARIANZA, PRE_PANDEMIA_FIN,
# CORR_VARIANZA_UMBRAL y TRANSFORMACION estaban definidas dos veces (un merge
# dejo un bloque duplicado aca abajo que sobreescribia silenciosamente al de
# arriba). Se conservan las definiciones del bloque "estacionariedad".

# --- prediccion y comparacion de modelos --------------------------
CRITERIO_GANADOR = "rmse"           # metrica que decide el mejor modelo por serie
HORIZON_TEST = None                 # None = usar todos los meses de prueba disponibles

# --- LSTM (Lab 2) -----------------------------------------------------------
LSTM_SEMILLA = 42       # el enunciado exige reproducibilidad; con esto el JSON sale igual siempre
LSTM_EPOCHS = 300       # default; el valor real por serie lo decide el tuneo
LSTM_LR = 1e-2

# Las 2 series del inciso 1.1. Maritima quedo fuera a proposito: sus ultimos 12
# meses de entrenamiento son cero exacto (cierre de fronteras), asi que una red
# con ventana 12 solo ve ceros y su prediccion recursiva colapsa a cero. Se
# probaron 5 configuraciones y ninguna lo evita.
LSTM_SERIES = ["total", "Aérea"]

# El tuneo valida contra la cola del entrenamiento, nunca contra el test. Ojo al
# interpretar: esos 12 meses (2020-04 a 2021-03) son justo el colapso pandemico.
LSTM_VAL_MESES = 12
LSTM_REJILLA_EPOCHS = (50, 100, 200, 300, 500)

# Una prediccion recursiva puede converger a un punto fijo y quedar plana. No es
# un error, es un resultado que hay que medir y reportar.
LSTM_COLA_APLANAMIENTO = 20   # meses del final que se miran
LSTM_CV_APLANADO = 0.01       # coef. de variacion por debajo de esto = plana

# --- catch22 (Lab 2) --------------------------------------------------------
# None = las 7 series. El enunciado 2.2 pide las caracteristicas de "cada serie
# temporal", a diferencia del ejercicio 1 que solo pedia dos.
CATCH22_SERIES = None

# El z-score va POR COLUMNA, no global: las 22 caracteristicas viven en escalas
# muy distintas (en estas series van de -0.94 a 49), asi que estandarizar con una
# sola media haria que unas pocas dominen cualquier distancia o PCA.
CATCH22_DDOF = 0
