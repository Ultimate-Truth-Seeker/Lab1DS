# -*- coding: utf-8 -*-
"""Genera el PDF del avance (Análisis Exploratorio + Análisis preliminar de series)."""

from reportlab.lib.pagesizes import letter
from reportlab.lib.units import inch
from reportlab.lib import colors
from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
from reportlab.platypus import (
    SimpleDocTemplate, Paragraph, Spacer, PageBreak, Image, Table, TableStyle,
    KeepTogether, HRFlowable
)
from reportlab.lib.enums import TA_CENTER, TA_JUSTIFY
from PIL import Image as PILImage


def sized_image(path, width_in):
    """Return a reportlab Image scaled to width_in inches, preserving aspect ratio."""
    with PILImage.open(path) as im:
        w, h = im.size
    width = width_in * inch
    height = width * (h / w)
    return Image(path, width=width, height=height)

FIG = "figs"
TEAL = colors.HexColor("#0b6e6e")
DARK = colors.HexColor("#1a1a1a")

styles = getSampleStyleSheet()
styles.add(ParagraphStyle("TitleUVG", parent=styles["Title"], fontSize=20, textColor=TEAL, spaceAfter=6))
styles.add(ParagraphStyle("SubtitleUVG", parent=styles["Normal"], fontSize=11, textColor=colors.grey, alignment=TA_CENTER, spaceAfter=4))
styles.add(ParagraphStyle("H1", parent=styles["Heading1"], fontSize=15, textColor=TEAL, spaceBefore=14, spaceAfter=8))
styles.add(ParagraphStyle("H2", parent=styles["Heading2"], fontSize=12.5, textColor=DARK, spaceBefore=10, spaceAfter=6))
styles.add(ParagraphStyle("Body", parent=styles["Normal"], fontSize=10, leading=14, alignment=TA_JUSTIFY, spaceAfter=8))
styles.add(ParagraphStyle("Caption", parent=styles["Normal"], fontSize=8.5, textColor=colors.grey, alignment=TA_CENTER, spaceAfter=12, spaceBefore=2))
styles.add(ParagraphStyle("BulletUVG", parent=styles["Normal"], fontSize=10, leading=14, leftIndent=14, spaceAfter=4))
styles.add(ParagraphStyle("Note", parent=styles["Normal"], fontSize=9.5, leading=13, textColor=colors.HexColor("#7a4a00"),
                           backColor=colors.HexColor("#fff6e5"), borderPadding=8, spaceAfter=10, spaceBefore=4))

story = []


def h1(t): story.append(Paragraph(t, styles["H1"]))
def h2(t): story.append(Paragraph(t, styles["H2"]))
def p(t): story.append(Paragraph(t, styles["Body"]))
def bullet(t): story.append(Paragraph("• " + t, styles["BulletUVG"]))
def note(t): story.append(Paragraph(t, styles["Note"]))
def img(path, width=6.3, caption=None):
    story.append(sized_image(f"{FIG}/{path}", width))
    if caption:
        story.append(Paragraph(caption, styles["Caption"]))
def hr():
    story.append(HRFlowable(width="100%", color=colors.HexColor("#cccccc"), thickness=0.6, spaceBefore=6, spaceAfter=6))

# ---------------------------------------------------------------------------
# PORTADA
# ---------------------------------------------------------------------------
story.append(Spacer(1, 60))
story.append(Paragraph("Universidad del Valle de Guatemala", styles["SubtitleUVG"]))
story.append(Paragraph("Facultad de Ingeniería — Departamento de Ciencias de la Computación", styles["SubtitleUVG"]))
story.append(Paragraph("CC3084 — Data Science | Semestre II — 2026", styles["SubtitleUVG"]))
story.append(Spacer(1, 40))
story.append(Paragraph("Laboratorio 1: Series de Tiempo", styles["TitleUVG"]))
story.append(Paragraph("Ingreso de viajeros internacionales a Guatemala (2009 – junio 2026)", styles["Heading2"]))
story.append(Spacer(1, 10))
story.append(Paragraph("AVANCE — Análisis Exploratorio y Análisis Preliminar de Series de Tiempo", styles["SubtitleUVG"]))
story.append(Spacer(1, 6))
story.append(Paragraph("Entrega de avance: 23 de julio de 2026", styles["SubtitleUVG"]))
story.append(Spacer(1, 40))
note("<b>Nota:</b> este documento corresponde al avance solicitado (análisis exploratorio general y análisis "
     "preliminar de al menos dos series de tiempo). La estacionariedad formal, el modelado ARIMA/Prophet/"
     "Holt-Winters, las predicciones y el análisis comparativo completo se desarrollarán en el documento final "
     "(entrega del 26 de julio de 2026), siguiendo la estructura de la guía de laboratorio.")
note("<b>Nota de la fuente:</b> los datos son de uso exclusivamente académico; no corresponden a cifras "
     "oficiales del INGUAT ni del Instituto Guatemalteco de Migración.")
story.append(PageBreak())

# ---------------------------------------------------------------------------
# 0. DESCRIPCIÓN DEL CONJUNTO DE DATOS
# ---------------------------------------------------------------------------
h1("0. Descripción del conjunto de datos")
p("El conjunto de datos contiene el ingreso mensual de viajeros internacionales a Guatemala entre enero de 2009 "
  "y junio de 2026 (210 meses consecutivos, sin huecos), en formato largo: cada fila es una combinación única de "
  "año, mes, vía de ingreso, frontera, país/agrupación de residencia y tipo de viajero, con la cantidad "
  "correspondiente en la columna <b>Viajero</b>. El archivo contiene <b>161,036 registros</b> y 13 columnas.")
p("La fuente combina tres tramos con metodologías distintas: (1) 2009–2020, respaldos históricos; "
  "(2) 2021–2022, entrega del IGM con caracterización; (3) 2023–jun. 2026, sistema depurado del INGUAT. "
  "Esto genera dos quiebres relevantes para el análisis de series de tiempo:")
bullet("<b>Quiebre por pandemia (2020):</b> colapso de viajeros desde marzo de 2020, piso en 2020–2021 "
       "(~27% del nivel de 2019) y recuperación gradual desde 2022.")
bullet("<b>Quiebre metodológico 2022→2023:</b> el sistema depurado excluye a los viajeros no turísticos de alta "
       "frecuencia (comercio fronterizo, tránsito) de la categoría \"Viajero\", y desde 2023 la columna \"País\" "
       "pasa de reportar país individual (226 posibles) a agrupaciones de mercado (27 grupos). Por esto, la "
       "categoría \"Viajero\" cae de ~1.06M en 2022 a ~0.33M en 2023 sin que exista una caída real de tránsito "
       "fronterizo; para series comparables en todo el rango el enunciado recomienda usar Turista + Excursionista.")
p("Adicionalmente: la vía Marítima pierde detalle de registro desde 2017; los decimales en \"Viajero\" en 2021-2022 "
  "corresponden a estimaciones expandidas de encuesta, no conteos exactos; y el año 2026 solo cubre de enero a junio.")

# ---------------------------------------------------------------------------
# 1. ANÁLISIS EXPLORATORIO
# ---------------------------------------------------------------------------
h1("1. Análisis exploratorio")

h2("1.1 Comportamiento temporal del número de viajeros")
img("01_temporal_total.png", caption="Figura 1. Total mensual de viajeros internacionales, todas las categorías (2009–2026).")
p("La serie total muestra una tendencia creciente sostenida entre 2009 y 2019 (con estacionalidad marcada), "
  "una caída abrupta en marzo de 2020 y un piso prolongado durante 2020–2021 producto del cierre de fronteras "
  "por la pandemia de COVID-19, y una recuperación progresiva a partir de 2022. La línea discontinua naranja "
  "marca el quiebre metodológico de 2023: a partir de ese punto el nivel de la serie total ya no es "
  "estrictamente comparable con los años anteriores debido al cambio en la definición de \"Viajero\" y en la "
  "granularidad de país, aunque el patrón visual de recuperación pos-pandemia es consistente con fuentes "
  "externas de turismo regional.")
img("02_temporal_comparable.png", caption="Figura 2. Serie mensual de Turista + Excursionista (comparable en todo el período).")
p("Al aislar Turista + Excursionista —la combinación recomendada por el enunciado para comparabilidad plena— "
  "el quiebre metodológico de 2023 deja de ser visible como salto de nivel, y el patrón pandemia/recuperación "
  "queda igual de claro. Esta será la serie de referencia para discutir el impacto \"real\" de la pandemia en el "
  "turismo, mientras que la serie total (obligatoria) se usará para el volumen agregado de ingreso migratorio.")

h2("1.2 Países con mayor cantidad de viajeros")
img("03_top_paises.png", caption="Figura 3. Top 15 países/agrupaciones de residencia por viajeros acumulados (2009–2026).")
tbl_paises = [["País / Agrupación", "Viajeros acumulados", "% del total"],
              ["El Salvador", "16,213,975", "31.0%"],
              ["Guatemala", "14,792,331", "28.3%"],
              ["Estados Unidos de América", "7,047,843", "13.5%"],
              ["Honduras", "2,788,233", "5.3%"],
              ["México", "1,808,946", "3.5%"],
              ["Belice", "1,328,256", "2.5%"],
              ["Nicaragua", "1,164,343", "2.2%"],
              ["Cruceristas", "1,078,372", "2.1%"],
              ["Costa Rica", "882,180", "1.7%"],
              ["Colombia", "561,035", "1.1%"]]
t = Table(tbl_paises, colWidths=[2.6*inch, 1.7*inch, 1.2*inch])
t.setStyle(TableStyle([
    ("BACKGROUND", (0, 0), (-1, 0), TEAL), ("TEXTCOLOR", (0, 0), (-1, 0), colors.white),
    ("FONTSIZE", (0, 0), (-1, -1), 9), ("ALIGN", (1, 0), (-1, -1), "RIGHT"),
    ("ALIGN", (0,0),(-1,0), "CENTER"),
    ("ROWBACKGROUNDS", (0, 1), (-1, -1), [colors.white, colors.HexColor("#f2f2f2")]),
    ("GRID", (0, 0), (-1, -1), 0.4, colors.HexColor("#dddddd")), ("TOPPADDING", (0,0),(-1,-1), 4),
    ("BOTTOMPADDING", (0,0),(-1,-1), 4),
]))
story.append(t); story.append(Spacer(1, 8))
p("El Salvador y Guatemala concentran conjuntamente el 59.3% del total histórico, lo que confirma el dominio "
  "estructural de la movilidad terrestre centroamericana sobre el turismo internacional de larga distancia.")
note("<b>Hallazgo relevante:</b> \"Guatemala\" aparece como segundo país de residencia (14.8M, 28.3%), a pesar de "
     "tratarse del país anfitrión. Al desagregar, el 77.3% de estos registros son \"Turista\" y provienen "
     "mayoritariamente de La Aurora (aeropuerto internacional) y de fronteras terrestres — es decir, "
     "corresponde principalmente a <b>residentes guatemaltecos que regresan del extranjero</b> (posible turismo "
     "de visita a familiares, VFR), no a turismo extranjero. Para el análisis de países se documenta este caso, "
     "y se recomienda tenerlo presente al interpretar la serie de \"Guatemala\" como serie de comparación, "
     "distinta en naturaleza a la de un mercado emisor extranjero real.")

h2("1.3 Regiones con mayor cantidad de viajeros")
img("04_top_regiones.png", caption="Figura 4. Viajeros acumulados por región (variable \"Región dos\"), 2009–2026.")
p("América del Centro concentra el 71.5% del total acumulado, seguida de América del Norte (17.9%) y Europa "
  "(4.3%). El resto de regiones (Sudamérica y el Caribe, Asia, Oceanía, Oriente Medio) aportan en conjunto menos "
  "del 4%. Se detectaron 821 registros (0.0016% del total) con el valor \"0\" en \"Región dos\" — un valor "
  "residual de catálogo sin agrupación asignada durante 2022, discutido en la sección 1.5 de calidad de datos.")

h2("1.4 Vías de ingreso y fronteras más utilizadas")
img("05_vias_fronteras.png", caption="Figura 5. Viajeros acumulados por vía de ingreso (izq.) y top 10 fronteras (der.).")
p("La vía Terrestre domina con 61.2% del total histórico, seguida de la vía Aérea (36.5%); la vía Marítima "
  "representa apenas 2.4%, coherente con la pérdida de detalle de registro desde 2017 señalada en las notas de "
  "la fuente. A nivel de frontera puntual, el Aeropuerto La Aurora concentra el 36.4% del total (toda la vía "
  "aérea), seguido de Valle Nuevo (20.5%, frontera con El Salvador) y San Cristóbal (10.3%, frontera con "
  "Honduras) — ambas coherentes con el peso de El Salvador y Honduras entre los principales países emisores.")

h2("1.5 Valores faltantes, duplicados y valores atípicos")
bullet("<b>Valores faltantes:</b> 0 en las 13 columnas — el conjunto de datos está completo.")
bullet("<b>Filas duplicadas exactas</b> (todas las columnas): 0.")
bullet("<b>Cuasi-duplicados aparentes:</b> al agrupar por Año, Mes, Vía, Frontera, País y Tipo de Viajero (sin "
       "incluir \"Agrupación Residencia\") aparecen 22 combinaciones repetidas; al inspeccionarlas se confirma "
       "que corresponden a subcategorías legítimas y distintas de \"Agrupación Residencia\" dentro del mismo "
       "país (p. ej. \"Colombia\" vs. \"Otros Suramérica\" dentro del país \"Colombia\") — no son errores de "
       "carga, sino mayor granularidad de esa columna.")
bullet("<b>Valores en cero:</b> 54 registros (0.03%) — plausibles dado que corresponden a combinaciones de "
       "categorías con muy baja frecuencia (p. ej. un país/vía/mes puntual sin viajeros ese mes).")
bullet("<b>Valores negativos:</b> 0.")
bullet("<b>Atípicos a nivel de fila</b> (regla de Tukey, 1.5×RIC sobre \"Viajero\"): el umbral superior es "
       "94.2 viajeros por registro y el 16.4% de las filas lo supera. Esto es un artefacto esperado de una "
       "variable de conteo extremadamente sesgada a la derecha por el diseño mismo del dataset (categorías "
       "con miles de combinaciones posibles de país/frontera/tipo, la mayoría con volúmenes pequeños y unas "
       "pocas —como La Aurora/vía Aérea o Valle Nuevo/vía Terrestre— con volúmenes muy altos). No se interpretan "
       "como errores de captura; el análisis de atípicos relevante para series de tiempo se hará sobre las "
       "series agregadas mensuales (sección 1.6 y 2), donde el evento atípico dominante es el colapso de "
       "viajeros por la pandemia en 2020.")
bullet("<b>Quiebres estructurales en volumen de registros por año</b> (no en \"Viajero\", sino en la cantidad de "
       "filas): de ~11,000–12,600 registros/año entre 2009-2019, cae a 4,375 en 2020 y 6,523–7,323 en 2021-2022 "
       "(menos combinaciones activas por la pandemia), y baja de nuevo a ~4,600–5,150 registros/año desde 2023 "
       "por el cambio de país individual a agrupación de mercado. Es importante no confundir este quiebre de "
       "granularidad con un cambio real en el volumen de viajeros.")

h2("1.6 Estadísticas descriptivas")
img("06_distribuciones.png", caption="Figura 6. Distribución de \"Viajero\" por registro (log) y total acumulado por tipo de viajero.")
tbl_desc = [["Estadístico", "Valor (viajeros por registro)"],
            ["Conteo", "161,036"], ["Media", "324.70"], ["Desv. estándar", "2,387.75"],
            ["Mínimo", "0.00"], ["Percentil 25", "2.00"], ["Mediana", "7.00"],
            ["Percentil 75", "38.89"], ["Máximo", "92,336.04 (Belice, Melchor de Mencos, tipo Viajero, ago-2017)"]]
t2 = Table(tbl_desc, colWidths=[2.3*inch, 3.6*inch])
t2.setStyle(TableStyle([
    ("BACKGROUND", (0, 0), (-1, 0), TEAL), ("TEXTCOLOR", (0, 0), (-1, 0), colors.white),
    ("FONTSIZE", (0, 0), (-1, -1), 9), ("ALIGN", (1, 0), (-1, -1), "LEFT"),
    ("ROWBACKGROUNDS", (0, 1), (-1, -1), [colors.white, colors.HexColor("#f2f2f2")]),
    ("GRID", (0, 0), (-1, -1), 0.4, colors.HexColor("#dddddd")), ("TOPPADDING", (0,0),(-1,-1), 4),
    ("BOTTOMPADDING", (0,0),(-1,-1), 4),
]))
story.append(t2); story.append(Spacer(1, 8))
p("La distribución de \"Viajero\" por registro es fuertemente asimétrica a la derecha (media muy superior a la "
  "mediana), típica de datos de conteo desagregados en muchas categorías. A nivel de tipo de viajero, Turista "
  "concentra 72.0% del total histórico, Excursionista 17.3%, Viajero (tránsito/comercio fronterizo de alta "
  "frecuencia) 8.6% y Cruceristas 2.1% — coherente con la recomendación del enunciado de usar Turista + "
  "Excursionista (89.3% del total) como medida comparable de flujo turístico en todo el período.")

story.append(PageBreak())

# ---------------------------------------------------------------------------
# 2. DIVISIÓN ENTRENAMIENTO / PRUEBA
# ---------------------------------------------------------------------------
h1("2. División en entrenamiento y prueba")
p("Dado que se trabaja con series de tiempo, la división se realizó de forma <b>cronológica</b> (no aleatoria), "
  "cortando el eje temporal en el mes que deja aproximadamente 70% de los meses en entrenamiento y 30% en prueba, "
  "de forma que el conjunto de prueba siempre sea posterior en el tiempo al de entrenamiento.")
tbl_split = [["Conjunto", "Rango de fechas", "N.° de meses", "% de meses", "Filas del dataset"],
             ["Entrenamiento", "2009-01 a 2021-03", "147", "70.0%", "131,442 (81.6%)"],
             ["Prueba", "2021-04 a 2026-06", "63", "30.0%", "29,594 (18.4%)"]]
t3 = Table(tbl_split, colWidths=[1.3*inch, 1.6*inch, 1.0*inch, 0.9*inch, 1.3*inch])
t3.setStyle(TableStyle([
    ("BACKGROUND", (0, 0), (-1, 0), TEAL), ("TEXTCOLOR", (0, 0), (-1, 0), colors.white),
    ("FONTSIZE", (0, 0), (-1, -1), 8.7), ("ALIGN", (1, 0), (-1, -1), "CENTER"),
    ("ROWBACKGROUNDS", (0, 1), (-1, -1), [colors.white, colors.HexColor("#f2f2f2")]),
    ("GRID", (0, 0), (-1, -1), 0.4, colors.HexColor("#dddddd")), ("TOPPADDING", (0,0),(-1,-1), 4),
    ("BOTTOMPADDING", (0,0),(-1,-1), 4),
]))
story.append(t3); story.append(Spacer(1, 8))
p("La proporción de <i>meses</i> es exactamente 70/30 por construcción. La proporción de <i>filas</i> del "
  "dataset difiere (81.6% / 18.4%) porque, como se documentó en 1.5, el tramo 2009–2022 tiene mayor granularidad "
  "de país (más filas por mes) que el tramo 2023 en adelante; esto no afecta la validez de la partición temporal, "
  "solo refleja el cambio de metodología de la fuente. Todas las series de tiempo del punto 3 se construyen "
  "exclusivamente a partir del conjunto de entrenamiento (2009-01 a 2021-03).")

# ---------------------------------------------------------------------------
# 3. SERIES SELECCIONADAS
# ---------------------------------------------------------------------------
h1("3. Series de tiempo construidas (a partir de entrenamiento)")
p("Se construyó la serie obligatoria (total mensual) y se seleccionaron dos categorías de análisis: "
  "<b>(i) Vías de ingreso</b> (Aérea, Terrestre, Marítima) y <b>(ii) Países de residencia</b>, tomando el top 3 "
  "según el acumulado de todo el período de estudio 2009–2026 (no solo entrenamiento): El Salvador, Guatemala y "
  "Estados Unidos de América. En total se obtienen 1 + 3 + 3 = 7 series mensuales.")
note("<b>Nota metodológica:</b> todas las series se reindexaron contra el rango fijo de 147 meses de "
     "entrenamiento (no contra el propio primer/último dato de cada subserie), de forma que los meses sin "
     "ningún registro se reflejen como 0 en vez de recortar la serie. Esto fue clave para la vía Marítima, que "
     "no tiene ningún registro entre abril de 2020 y marzo de 2021 (cierre de fronteras marítimas por la "
     "pandemia): sin este ajuste la serie parecía terminar en marzo de 2020.")

# ---------------------------------------------------------------------------
# 4. ANÁLISIS PRELIMINAR DE SERIES
# ---------------------------------------------------------------------------
h1("4. Análisis preliminar de las series")
p("A continuación se presenta el análisis preliminar (inicio/fin/frecuencia, gráfico, descomposición y una "
  "primera lectura de estacionariedad con ACF y la prueba de Dickey-Fuller Aumentada) para la serie obligatoria "
  "y para las seis series de las dos categorías seleccionadas. El análisis formal de estacionariedad "
  "(transformaciones, número de diferenciaciones) y el modelado ARIMA/Prophet/Holt-Winters se completan en el "
  "documento final.")

series_info = [
    ("Total mensual de viajeros internacionales", "10_serie_total.png",
     "237,120.9", "101,886.5", "9,779", "515,820.4", -1.970, 0.2998,
     "Muestra tendencia creciente 2009-2019, colapso pandémico en 2020 y recuperación parcial hacia el corte de "
     "entrenamiento (mar-2021). La descomposición aditiva evidencia un componente de tendencia claramente no "
     "constante y una estacionalidad anual regular (picos en jul-ago y dic, típicos de temporada alta). El "
     "residuo muestra mayor dispersión durante 2020, coherente con la ruptura estructural de la pandemia."),
    ("Vía de ingreso: Aérea", "11_serie_via_Aérea.png",
     "89,141.3", "29,412.5", "489", "157,842.0", -2.364, 0.1522,
     "Tendencia creciente sostenida hasta 2019 y estacionalidad anual visible (picos de temporada alta). Cae "
     "prácticamente a cero en abr-2020 por el cierre del Aeropuerto La Aurora al tráfico de pasajeros."),
    ("Vía de ingreso: Terrestre", "11_serie_via_Terrestre.png",
     "139,988.5", "72,323.9", "5,715", "348,626.4", -1.873, 0.3451,
     "Es la serie de mayor volumen y mayor variabilidad absoluta (desv. estándar 72,323.9). Conserva un piso "
     "positivo incluso en pandemia, reflejando que el cruce terrestre nunca se cerró por completo (comercio y "
     "residentes fronterizos)."),
    ("Vía de ingreso: Marítima", "11_serie_via_Marítima.png",
     "7,991.2", "6,934.3", "0", "29,506.0", -0.989, 0.7571,
     "Serie de menor volumen y con un tramo de 12 meses exactamente en cero (abr-2020 a mar-2021), el evento "
     "atípico más marcado de las 7 series. Su patrón estacional es menos regular que el de las otras dos vías."),
    ("País de residencia: El Salvador", "12_serie_pais_El_Salvador.png",
     "61,502.0", "33,698.0", "0", "165,263.0", -1.781, 0.3901,
     "Máximo emisor individual; sigue de cerca el patrón agregado de la vía Terrestre, con estacionalidad ligada "
     "a fines de semana largos y temporada de fin de año en la región."),
    ("País de residencia: Guatemala", "12_serie_pais_Guatemala.png",
     "86,951.8", "40,005.6", "9,779", "207,097.0", -2.091, 0.2481,
     "Segunda serie en volumen; como se documentó en 1.2, mezcla flujo aéreo y terrestre y probablemente "
     "corresponde en su mayoría a residentes guatemaltecos que regresan del extranjero, por lo que su lectura "
     "como \"mercado emisor\" debe hacerse con cautela."),
    ("País de residencia: Estados Unidos de América", "12_serie_pais_Estados_Unidos_de_América.png",
     "27,955.1", "11,062.9", "0", "54,990.0", -3.122, 0.0249,
     "Es la única de las 7 series cuya prueba ADF preliminar rechaza la hipótesis nula al 5% (p = 0.0249), es "
     "decir, el único caso donde el resultado preliminar apunta a estacionariedad en media sin diferenciar; aun "
     "así se observa un quiebre de nivel claro en 2020 que debe evaluarse con más detalle en el documento final."),
]

for nombre, fig, media, sd, mn, mx, adf_stat, adf_p, interpretacion in series_info:
    block = []
    block.append(Paragraph(nombre, styles["H2"]))
    conclusion = "no se rechaza H0 (no estacionaria en media)" if adf_p >= 0.05 else "se rechaza H0 (estacionaria en media)"
    block.append(Paragraph(
        f"<b>Inicio:</b> 2009-01 &nbsp;&nbsp; <b>Fin:</b> 2021-03 &nbsp;&nbsp; <b>Frecuencia:</b> mensual (MS) "
        f"&nbsp;&nbsp; <b>N:</b> 147 obs. &nbsp;&nbsp; <b>Media:</b> {media} &nbsp;&nbsp; "
        f"<b>Desv. estándar:</b> {sd} &nbsp;&nbsp; <b>Mín–Máx:</b> {mn} – {mx}", styles["Body"]))
    block.append(sized_image(f"{FIG}/{fig}", 6.0))
    block.append(Paragraph(f"Figura. {nombre} — serie, tendencia, estacionalidad y residuo (train).", styles["Caption"]))
    story.append(KeepTogether(block))
    story.append(Image(f"{FIG}/{fig.replace('.png','_acf.png')}", width=4.3*inch, height=None, kind="proportional"))
    story.append(Paragraph("Figura. Función de autocorrelación (ACF, 36 rezagos).", styles["Caption"]))
    p(interpretacion)
    p(f"<b>Prueba ADF preliminar</b> (sobre el nivel, sin diferenciar): estadístico = {adf_stat:.3f}, "
      f"p-valor = {adf_p:.4f} → {conclusion}. La ACF decae lentamente y con un patrón oscilante de periodo "
      "aproximadamente anual, consistente con la presencia de tendencia y estacionalidad — ambos síntomas "
      "típicos de no estacionariedad en media, que en el documento final se abordarán con diferenciación regular "
      "y/o estacional según corresponda, además de confirmar la necesidad (o no) de una transformación "
      "(p. ej. logarítmica) para estabilizar la varianza.")
    hr()

story.append(PageBreak())

# ---------------------------------------------------------------------------
# 5. PRÓXIMOS PASOS
# ---------------------------------------------------------------------------
h1("5. Próximos pasos (documento final — 26 de julio de 2026)")
bullet("Completar la construcción de las 7 series también para el conjunto de prueba, para poder evaluar "
       "predicciones fuera de muestra.")
bullet("Determinar formalmente la estacionariedad en varianza (transformación Box-Cox/log si corresponde) y en "
       "media (número de diferenciaciones regulares y estacionales) para cada una de las 7 series.")
bullet("Seleccionar p, d, q (y componente estacional P, D, Q, s si aplica) con base en ACF/PACF, contrastar con "
       "auto_arima/auto.arima, y ajustar varios modelos ARIMA por serie, comparando residuos, AIC y BIC.")
bullet("Ajustar y comparar modelos Prophet, Holt-Winters, suavizamiento exponencial y seasonal naive frente a "
       "los modelos ARIMA.")
bullet("Generar predicciones sobre el conjunto de prueba y comparar todos los modelos con MAE, RMSE, AIC y BIC "
       "para seleccionar el mejor modelo por serie.")
bullet("Desarrollar el análisis comparativo entre las series de cada categoría (estacionalidad, tendencia, "
       "volatilidad, impacto de la pandemia) y los hallazgos generales orientados a la toma de decisiones del "
       "INGUAT.")

doc = SimpleDocTemplate(
    "/mnt/user-data/outputs/Laboratorio1_Avance_SeriesDeTiempo.pdf",
    pagesize=letter,
    topMargin=0.7*inch, bottomMargin=0.7*inch, leftMargin=0.75*inch, rightMargin=0.75*inch,
    title="Laboratorio 1 - Avance - Series de Tiempo - CC3084",
    author="CC3084 Data Science - UVG",
)
doc.build(story)
print("PDF generado.")