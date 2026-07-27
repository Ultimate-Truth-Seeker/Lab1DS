"""
Arma el PDF del informe.

Este modulo NO calcula nada: todos los numeros salen de results/*.json, que
produce el pipeline. Lo unico que vive aca es la maquetacion y la prosa
interpretativa.

Convencion de literales:
  - los numeros derivados de datos vienen del JSON, siempre;
  - la prosa interpretativa ("confirma el dominio estructural...") es del autor;
  - los pocos numeros verificados a mano fuera del pipeline van marcados con
    un comentario VERIFICADO MANUALMENTE y el criterio usado.
"""

import json
import sys
from pathlib import Path

from reportlab.lib import colors
from reportlab.lib.enums import TA_CENTER, TA_JUSTIFY
from reportlab.lib.pagesizes import letter
from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
from reportlab.lib.units import inch
from reportlab.platypus import (
    HRFlowable, Image, KeepTogether, PageBreak, Paragraph, SimpleDocTemplate,
    Spacer, Table, TableStyle,
)
from PIL import Image as PILImage

ROOT = Path(__file__).resolve().parent.parent
RESULTS = ROOT / "results"

# Lectura a primera vista de cada serie. Es interpretacion del autor sobre el
# grafico y la descomposicion, no un numero derivable: por eso vive aca y no en
# el JSON. La clave es la del pipeline.
#
# Los {sd} / {pvalue} / {n_series} se rellenan con los valores del JSON: la
# interpretacion es del autor, pero los numeros que cita siguen viniendo de una
# sola fuente.
INTERPRETACIONES = {
    "total":
        "Muestra tendencia creciente 2009-2019, colapso pandémico en 2020 y recuperación parcial hacia el corte de "
        "entrenamiento (mar-2021). La descomposición aditiva evidencia un componente de tendencia claramente no "
        "constante y una estacionalidad anual regular (picos en jul-ago y dic, típicos de temporada alta). El "
        "residuo muestra mayor dispersión durante 2020, coherente con la ruptura estructural de la pandemia.",
    "Aérea":
        "Tendencia creciente sostenida hasta 2019 y estacionalidad anual visible (picos de temporada alta). Cae "
        "prácticamente a cero en abr-2020 por el cierre del Aeropuerto La Aurora al tráfico de pasajeros.",
    "Terrestre":
        "Es la serie de mayor volumen y mayor variabilidad absoluta (desv. estándar {sd:,.1f}). Conserva un piso "
        "positivo incluso en pandemia, reflejando que el cruce terrestre nunca se cerró por completo (comercio y "
        "residentes fronterizos).",
    "Marítima":
        "Serie de menor volumen y con un tramo de {racha_ceros_max} meses consecutivos exactamente en cero por el "
        "cierre de fronteras marítimas, el evento atípico más marcado de las {n_series} series ({meses_en_cero} "
        "meses en cero en total, contando algunos previos a la pandemia). Su patrón estacional es menos regular que "
        "el de las otras dos vías.",
    "El Salvador":
        "Máximo emisor individual; sigue de cerca el patrón agregado de la vía Terrestre, con estacionalidad ligada "
        "a fines de semana largos y temporada de fin de año en la región.",
    "Guatemala":
        "Segunda serie en volumen; como se documentó en 1.2, mezcla flujo aéreo y terrestre y probablemente "
        "corresponde en su mayoría a residentes guatemaltecos que regresan del extranjero, por lo que su lectura "
        "como \"mercado emisor\" debe hacerse con cautela.",
    "Estados Unidos de América":
        "Es la única de las {n_series} series cuya prueba ADF sobre el nivel rechaza la hipótesis nula al 5% "
        "(p = {pvalue:.4f}), el único caso que ya en nivel apuntaría a estacionariedad en media sin diferenciar. "
        "Es un resultado al filo del umbral: al estabilizar la varianza el p-valor sube por encima del 5% y la "
        "serie deja de pasar la prueba, de modo que sí requiere una diferenciación regular. Conviene no leer el "
        "0.05 como una frontera dura cuando el estadístico queda tan cerca.",
}


def cargar_resultados() -> dict:
    """Lee los tres JSON del pipeline. Si faltan, aborta con un mensaje util."""
    datos = {}
    for nombre in ("eda", "split", "series"):
        ruta = RESULTS / f"{nombre}.json"
        if not ruta.exists():
            sys.exit(f"Falta {ruta.relative_to(ROOT)}. Corre primero: python main.py all")
        with open(ruta, encoding="utf-8") as fh:
            datos[nombre] = json.load(fh)
    return datos


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
def hr():
    story.append(HRFlowable(width="100%", color=colors.HexColor("#cccccc"), thickness=0.6, spaceBefore=6, spaceAfter=6))


def sized_image(ruta, width_in, height_in=None):
    """Escala la imagen preservando la relacion de aspecto."""
    with PILImage.open(ruta) as im:
        w, h = im.size
    if height_in is None:
        width = width_in * inch
        height = width * (h / w)
    else:
        height = height_in * inch
        width = height * (w / h)
    return Image(str(ruta), width=width, height=height)


def img(nombre_o_ruta, width=6.3, caption=None):
    ruta = ROOT / nombre_o_ruta
    story.append(sized_image(ruta, width))
    if caption:
        story.append(Paragraph(caption, styles["Caption"]))


def tabla(filas, col_widths, font_size=9, align="RIGHT"):
    t = Table(filas, colWidths=col_widths)
    t.setStyle(TableStyle([
        ("BACKGROUND", (0, 0), (-1, 0), TEAL), ("TEXTCOLOR", (0, 0), (-1, 0), colors.white),
        ("FONTSIZE", (0, 0), (-1, -1), font_size), ("ALIGN", (1, 0), (-1, -1), align),
        ("ALIGN", (0, 0), (-1, 0), "CENTER"),
        ("ROWBACKGROUNDS", (0, 1), (-1, -1), [colors.white, colors.HexColor("#f2f2f2")]),
        ("GRID", (0, 0), (-1, -1), 0.4, colors.HexColor("#dddddd")),
        ("TOPPADDING", (0, 0), (-1, -1), 4), ("BOTTOMPADDING", (0, 0), (-1, -1), 4),
    ]))
    story.append(t)
    story.append(Spacer(1, 8))


def construir(datos: dict) -> None:
    eda = datos["eda"]
    split = datos["split"]
    series_doc = datos["series"]

    ds = eda["dataset"]
    cal = eda["calidad"]
    des = eda["descriptivos_viajero"]
    pais_pct = {x["nombre"]: x["pct"] for x in eda["top_paises"]}
    reg = {x["nombre"]: x["pct"] for x in eda["regiones"]}
    via = {x["nombre"]: x["pct"] for x in eda["vias"]}
    fron = {x["nombre"]: x["pct"] for x in eda["fronteras"]}
    tipo = {x["nombre"]: x["pct"] for x in eda["tipos_viajero"]}
    tr, te = split["train"], split["test"]

    # ---------------------------------------------------------------- portada
    story.append(Spacer(1, 60))
    story.append(Paragraph("Universidad del Valle de Guatemala", styles["SubtitleUVG"]))
    story.append(Paragraph("Facultad de Ingeniería — Departamento de Ciencias de la Computación", styles["SubtitleUVG"]))
    story.append(Paragraph("CC3084 — Data Science | Semestre II — 2026", styles["SubtitleUVG"]))
    story.append(Spacer(1, 40))
    story.append(Paragraph("Laboratorio 1: Series de Tiempo", styles["TitleUVG"]))
    story.append(Paragraph("Ingreso de viajeros internacionales a Guatemala (2009 – junio 2026)", styles["Heading2"]))
    story.append(Spacer(1, 10))
    story.append(Paragraph("Análisis Exploratorio, Análisis de Series y Determinación de Estacionariedad",
                           styles["SubtitleUVG"]))
    story.append(Spacer(1, 6))
    story.append(Paragraph("Julio de 2026", styles["SubtitleUVG"]))
    story.append(Spacer(1, 40))
    note("<b>Contenido de este documento:</b> análisis exploratorio del conjunto de datos, construcción de las "
         "series de tiempo, análisis de sus componentes y determinación formal de estacionariedad en varianza y en "
         "media (con la transformación aplicada y el número de diferenciaciones por serie). El modelado "
         "ARIMA/Prophet/Holt-Winters, las predicciones sobre el conjunto de prueba y el análisis comparativo se "
         "desarrollan en las secciones siguientes del informe, siguiendo la estructura de la guía de laboratorio.")
    note("<b>Nota de la fuente:</b> los datos son de uso exclusivamente académico; no corresponden a cifras "
         "oficiales del INGUAT ni del Instituto Guatemalteco de Migración.")
    story.append(PageBreak())

    # ------------------------------------------------- 0. descripcion general
    h1("0. Descripción del conjunto de datos")
    p(f"El conjunto de datos contiene el ingreso mensual de viajeros internacionales a Guatemala entre enero de 2009 "
      f"y junio de 2026 ({split['n_meses_total']} meses consecutivos, sin huecos), en formato largo: cada fila es una "
      f"combinación única de año, mes, vía de ingreso, frontera, país/agrupación de residencia y tipo de viajero, con "
      f"la cantidad correspondiente en la columna <b>Viajero</b>. El archivo contiene <b>{ds['filas']:,} registros</b> "
      f"y {ds['columnas_fuente']} columnas.")
    # los tramos y sus metodologias vienen de las notas de la fuente; los numeros que
    # los acompañan si salen del pipeline (antes estaban a mano, y varios estaban mal).
    qm = eda["quiebre_metodologico"]
    pand = eda["impacto_pandemia"]
    pct_pand = pand["pct_respecto_base"]
    p("La fuente combina tres tramos con metodologías distintas: (1) 2009–2020, respaldos históricos; "
      "(2) 2021–2022, entrega del IGM con caracterización; (3) 2023–jun. 2026, sistema depurado del INGUAT. "
      "Esto genera dos quiebres relevantes para el análisis de series de tiempo:")
    bullet(f"<b>Quiebre por pandemia (2020):</b> colapso de viajeros desde marzo de 2020, piso en 2020–2021 "
           f"({pct_pand['2020']:.0f}% y {pct_pand['2021']:.0f}% del nivel de {pand['anio_base']} en la serie "
           f"comparable) y recuperación gradual desde 2022.")
    bullet(f"<b>Quiebre metodológico 2022→{qm['anio_corte']}:</b> el sistema depurado excluye a los viajeros no "
           f"turísticos de alta frecuencia (comercio fronterizo, tránsito) de la categoría \"Viajero\", y desde "
           f"{qm['anio_corte']} la columna \"País\" pasa de reportar país individual ({qm['paises_antes']} valores "
           f"distintos hasta {qm['anio_corte']-1}) a agrupaciones de mercado ({qm['grupos_despues']} grupos). Por "
           f"esto, la categoría \"Viajero\" cae de {qm['viajero_anio_previo']/1e6:.2f}M en {qm['anio_corte']-1} a "
           f"{qm['viajero_anio_corte']/1e6:.2f}M en {qm['anio_corte']} sin que exista una caída real de tránsito "
           f"fronterizo; para series comparables en todo el rango el enunciado recomienda usar Turista + "
           f"Excursionista.")
    p("Adicionalmente: la vía Marítima pierde detalle de registro desde 2017; los decimales en \"Viajero\" en 2021-2022 "
      "corresponden a estimaciones expandidas de encuesta, no conteos exactos; y el año 2026 solo cubre de enero a junio.")

    # ------------------------------------------------- 1. analisis exploratorio
    h1("1. Análisis exploratorio")

    h2("1.1 Comportamiento temporal del número de viajeros")
    img("figs/01_temporal_total.png",
        caption="Figura 1. Total mensual de viajeros internacionales, todas las categorías (2009–2026).")
    p("La serie total muestra una tendencia creciente sostenida entre 2009 y 2019 (con estacionalidad marcada), "
      "una caída abrupta en marzo de 2020 y un piso prolongado durante 2020–2021 producto del cierre de fronteras "
      "por la pandemia de COVID-19, y una recuperación progresiva a partir de 2022. La línea discontinua naranja "
      "marca el quiebre metodológico de 2023: a partir de ese punto el nivel de la serie total ya no es "
      "estrictamente comparable con los años anteriores debido al cambio en la definición de \"Viajero\" y en la "
      "granularidad de país, aunque el patrón visual de recuperación pos-pandemia es consistente con fuentes "
      "externas de turismo regional.")
    img("figs/02_temporal_comparable.png",
        caption="Figura 2. Serie mensual de Turista + Excursionista (comparable en todo el período).")
    p("Al aislar Turista + Excursionista —la combinación recomendada por el enunciado para comparabilidad plena— "
      "el quiebre metodológico de 2023 deja de ser visible como salto de nivel, y el patrón pandemia/recuperación "
      "queda igual de claro. Esta será la serie de referencia para discutir el impacto \"real\" de la pandemia en el "
      "turismo, mientras que la serie total (obligatoria) se usará para el volumen agregado de ingreso migratorio.")

    h2("1.2 Países con mayor cantidad de viajeros")
    img("figs/03_top_paises.png",
        caption="Figura 3. Top 15 países/agrupaciones de residencia por viajeros acumulados (2009–2026).")
    filas = [["País / Agrupación", "Viajeros acumulados", "% del total"]]
    filas += [[x["nombre"], f"{x['acumulado']:,.0f}", f"{x['pct']:.1f}%"] for x in eda["top_paises"]]
    tabla(filas, [2.6 * inch, 1.7 * inch, 1.2 * inch])
    dos_primeros = eda["top_paises"][0]["pct"] + eda["top_paises"][1]["pct"]
    p(f"El Salvador y Guatemala concentran conjuntamente el {dos_primeros:.1f}% del total histórico, lo que confirma "
      f"el dominio estructural de la movilidad terrestre centroamericana sobre el turismo internacional de larga "
      f"distancia.")
    # VERIFICADO MANUALMENTE: el 77.3% sale de cruzar Pais=Guatemala con Tipo de Viajero; el pipeline
    # no lo calcula porque exige una decision metodologica propia sobre como tratar ese caso.
    gt = next(x for x in eda["top_paises"] if x["nombre"] == "Guatemala")
    note(f"<b>Hallazgo relevante:</b> \"Guatemala\" aparece como segundo país de residencia "
         f"({gt['acumulado']/1e6:.1f}M, {gt['pct']:.1f}%), a pesar de tratarse del país anfitrión. Al desagregar, el 77.3% "
         f"de estos registros son \"Turista\" y provienen mayoritariamente de La Aurora (aeropuerto internacional) y "
         f"de fronteras terrestres — es decir, corresponde principalmente a <b>residentes guatemaltecos que regresan "
         f"del extranjero</b> (posible turismo de visita a familiares, VFR), no a turismo extranjero. Para el análisis "
         f"de países se documenta este caso, y se recomienda tenerlo presente al interpretar la serie de \"Guatemala\" "
         f"como serie de comparación, distinta en naturaleza a la de un mercado emisor extranjero real.")

    h2("1.3 Regiones con mayor cantidad de viajeros")
    img("figs/04_top_regiones.png",
        caption="Figura 4. Viajeros acumulados por región (variable \"Región dos\"), 2009–2026.")
    otras = 100 - reg["América Del Centro"] - reg["América Del Norte"] - reg["Europa"]
    rsa = eda["region_sin_asignar"]
    anios_rsa = ", ".join(str(a) for a in rsa["anios"])
    p(f"América del Centro concentra el {reg['América Del Centro']:.1f}% del total acumulado, seguida de América del "
      f"Norte ({reg['América Del Norte']:.1f}%) y Europa ({reg['Europa']:.1f}%). El resto de regiones (Sudamérica y el "
      f"Caribe, Asia, Oceanía, Oriente Medio) aportan en conjunto {otras:.1f}%. Se detectaron "
      f"{rsa['registros']} registros ({rsa['pct']:.4f}% del total) con el valor \"0\" en \"Región dos\" — un valor "
      f"residual de catálogo sin agrupación asignada durante {anios_rsa}, discutido en la sección 1.5 de calidad "
      f"de datos.")

    h2("1.4 Vías de ingreso y fronteras más utilizadas")
    img("figs/05_vias_fronteras.png",
        caption="Figura 5. Viajeros acumulados por vía de ingreso (izq.) y top 10 fronteras (der.).")
    f_top = eda["fronteras"]
    p(f"La vía Terrestre domina con {via['Terrestre']:.1f}% del total histórico, seguida de la vía Aérea "
      f"({via['Aérea']:.1f}%); la vía Marítima representa apenas {via['Marítima']:.1f}%, coherente con la pérdida de "
      f"detalle de registro desde 2017 señalada en las notas de la fuente. A nivel de frontera puntual, "
      f"el Aeropuerto {f_top[0]['nombre'][3:]} concentra el {f_top[0]['pct']:.1f}% del total (toda la vía aérea), seguido de "
      f"{f_top[1]['nombre'][3:]} ({f_top[1]['pct']:.1f}%, frontera con El Salvador) y {f_top[2]['nombre'][3:]} "
      f"({f_top[2]['pct']:.1f}%, frontera con Honduras) — ambas coherentes con el peso de El Salvador y Honduras "
      f"entre los principales países emisores.")

    h2("1.5 Valores faltantes, duplicados y valores atípicos")
    bullet(f"<b>Valores faltantes:</b> {cal['faltantes_total']} en las {ds['columnas_fuente']} columnas — "
           f"el conjunto de datos está completo.")
    bullet(f"<b>Filas duplicadas exactas</b> (todas las columnas): {cal['duplicados_exactos']}.")
    cd_ = eda["cuasi_duplicados"]["combinaciones_repetidas"]
    bullet(f"<b>Cuasi-duplicados aparentes:</b> al agrupar por Año, Mes, Vía, Frontera, País y Tipo de Viajero (sin "
           f"incluir \"Agrupación Residencia\") aparecen {cd_} combinaciones repetidas; al inspeccionarlas se "
           f"confirma que corresponden a subcategorías legítimas y distintas de \"Agrupación Residencia\" dentro del "
           f"mismo país (p. ej. \"Colombia\" vs. \"Otros Suramérica\" dentro del país \"Colombia\") — no son errores "
           f"de carga, sino mayor granularidad de esa columna.")
    bullet(f"<b>Valores en cero:</b> {cal['ceros']} registros ({cal['pct_ceros']:.2f}%) — plausibles dado que "
           f"corresponden a combinaciones de categorías con muy baja frecuencia (p. ej. un país/vía/mes puntual sin "
           f"viajeros ese mes).")
    bullet(f"<b>Valores negativos:</b> {cal['negativos']}.")
    bullet(f"<b>Atípicos a nivel de fila</b> (regla de Tukey, 1.5×RIC sobre \"Viajero\"): el umbral superior es "
           f"{cal['iqr_umbral_superior']:.1f} viajeros por registro y el {cal['iqr_pct_sobre_umbral']:.1f}% de las "
           f"filas lo supera. Esto es un artefacto esperado de una variable de conteo extremadamente sesgada a la "
           f"derecha por el diseño mismo del dataset (categorías con miles de combinaciones posibles de "
           f"país/frontera/tipo, la mayoría con volúmenes pequeños y unas pocas —como La Aurora/vía Aérea o Valle "
           f"Nuevo/vía Terrestre— con volúmenes muy altos). No se interpretan como errores de captura; el análisis "
           f"de atípicos relevante para series de tiempo se hará sobre las series agregadas mensuales (sección 1.6 "
           f"y 2), donde el evento atípico dominante es el colapso de viajeros por la pandemia en 2020.")
    rpa = cal["registros_por_anio"]
    bullet(f"<b>Quiebres estructurales en volumen de registros por año</b> (no en \"Viajero\", sino en la cantidad de "
           f"filas): de ~{min(rpa[a] for a in list(rpa)[:11]):,}–{max(rpa[a] for a in list(rpa)[:11]):,} "
           f"registros/año entre 2009-2019, cae a {rpa['2020']:,} en 2020 y {rpa['2021']:,}–{rpa['2022']:,} en "
           f"2021-2022 (menos combinaciones activas por la pandemia), y baja de nuevo a "
           f"~{min(rpa[a] for a in ['2023', '2024', '2025']):,}–{max(rpa[a] for a in ['2023', '2024', '2025']):,} "
           f"registros/año desde 2023 por el cambio de país individual a agrupación de mercado. Es importante no "
           f"confundir este quiebre de granularidad con un cambio real en el volumen de viajeros.")

    h2("1.6 Estadísticas descriptivas")
    img("figs/06_distribuciones.png",
        caption="Figura 6. Distribución de \"Viajero\" por registro (log) y total acumulado por tipo de viajero.")
    mc = des["max_contexto"]
    filas = [["Estadístico", "Valor (viajeros por registro)"],
             ["Conteo", f"{des['count']:,.0f}"],
             ["Media", f"{des['media']:,.2f}"],
             ["Desv. estándar", f"{des['sd']:,.2f}"],
             ["Mínimo", f"{des['min']:,.2f}"],
             ["Percentil 25", f"{des['p25']:,.2f}"],
             ["Mediana", f"{des['mediana']:,.2f}"],
             ["Percentil 75", f"{des['p75']:,.2f}"],
             ["Máximo", f"{des['max']:,.2f} ({mc['pais']}, {mc['frontera'][3:]}, "
                        f"tipo {mc['tipo_viajero']}, {mc['fecha']})"]]
    tabla(filas, [2.3 * inch, 3.6 * inch], align="LEFT")
    comparable = tipo["Turista"] + tipo["Excursionista"]
    p(f"La distribución de \"Viajero\" por registro es fuertemente asimétrica a la derecha (media muy superior a la "
      f"mediana), típica de datos de conteo desagregados en muchas categorías. A nivel de tipo de viajero, Turista "
      f"concentra {tipo['Turista']:.1f}% del total histórico, Excursionista {tipo['Excursionista']:.1f}%, Viajero "
      f"(tránsito/comercio fronterizo de alta frecuencia) {tipo['Viajero']:.1f}% y Cruceristas "
      f"{tipo['Cruceristas']:.1f}% — coherente con la recomendación del enunciado de usar Turista + Excursionista "
      f"({comparable:.1f}% del total) como medida comparable de flujo turístico en todo el período.")

    # ------------------------------- 1.7 comportamiento durante y post pandemia
    h2("1.7 Comportamiento de cada serie durante y después de la pandemia")
    p(f"Las series que se usan para modelar terminan en {tr['fin']} por la partición cronológica, de modo que la "
      f"recuperación posterior no es visible en ellas. Para documentar el comportamiento completo se grafica cada "
      f"una de las {len(series_doc['series'])} series sobre los {series_doc['n_meses_periodo_completo']} meses del "
      f"período de estudio, sombreando el tramo de entrenamiento y marcando la pandemia y el quiebre metodológico "
      f"de 2023.")
    note("<b>Alcance:</b> estas figuras son exclusivamente exploratorias. Todas las series de modelado, "
         "estacionariedad y predicción se mantienen sobre el tramo de entrenamiento, porque el conjunto de prueba "
         "debe permanecer sin observar hasta la evaluación de los modelos.")

    for s in series_doc["series"]:
        story.append(sized_image(ROOT / s["fig_periodo_completo"], 5.9))
        story.append(Paragraph(f"Figura. {s['nombre']} — período completo "
                               f"({series_doc['n_meses_periodo_completo']} meses).", styles["Caption"]))

    p("La lectura conjunta muestra tres comportamientos distintos tras la pandemia. La vía Aérea es la que se "
      "recupera con más fuerza: vuelve a superar su nivel pre-pandemia y mantiene la estacionalidad anual marcada, "
      "lo que la convierte en la serie más informativa para planificación turística. La vía Terrestre conserva un "
      "piso positivo incluso en 2020 —nunca se cerró del todo— y se recupera de forma más plana. La vía Marítima "
      "no regresa a los niveles de 2009-2016, consistente con la pérdida de detalle de registro que la fuente "
      "documenta desde 2017. En la serie total se aprecia además el salto de nivel de 2023 correspondiente al "
      "cambio de metodología, que no aparece al aislar Turista + Excursionista (figura 2).")

    story.append(PageBreak())

    # --------------------------------------------------- 2. entrenamiento/prueba
    h1("2. División en entrenamiento y prueba")
    p("Dado que se trabaja con series de tiempo, la división se realizó de forma <b>cronológica</b> (no aleatoria), "
      "cortando el eje temporal en el mes que deja aproximadamente 70% de los meses en entrenamiento y 30% en prueba, "
      "de forma que el conjunto de prueba siempre sea posterior en el tiempo al de entrenamiento.")
    filas = [["Conjunto", "Rango de fechas", "N.° de meses", "% de meses", "Filas del dataset"],
             ["Entrenamiento", f"{tr['inicio']} a {tr['fin']}", str(tr["n_meses"]),
              f"{tr['pct_meses']:.1f}%", f"{tr['filas']:,} ({tr['pct_filas']:.1f}%)"],
             ["Prueba", f"{te['inicio']} a {te['fin']}", str(te["n_meses"]),
              f"{te['pct_meses']:.1f}%", f"{te['filas']:,} ({te['pct_filas']:.1f}%)"]]
    tabla(filas, [1.3 * inch, 1.6 * inch, 1.0 * inch, 0.9 * inch, 1.3 * inch], font_size=8.7, align="CENTER")
    p(f"La proporción de <i>meses</i> es exactamente {tr['pct_meses']:.0f}/{te['pct_meses']:.0f} por construcción. La "
      f"proporción de <i>filas</i> del dataset difiere ({tr['pct_filas']:.1f}% / {te['pct_filas']:.1f}%) porque, como "
      f"se documentó en 1.5, el tramo 2009–2022 tiene mayor granularidad de país (más filas por mes) que el tramo "
      f"2023 en adelante; esto no afecta la validez de la partición temporal, solo refleja el cambio de metodología "
      f"de la fuente. Todas las series de tiempo del punto 3 se construyen exclusivamente a partir del conjunto de "
      f"entrenamiento ({tr['inicio']} a {tr['fin']}).")

    # --------------------------------------------------------- 3. series usadas
    lista = series_doc["series"]
    vias = [s for s in lista if s["categoria"] == "via"]
    paises = [s for s in lista if s["categoria"] == "pais"]
    def _enumerar(nombres):
        """'a, b y c' — separador final en español."""
        if len(nombres) < 2:
            return "".join(nombres)
        return f"{', '.join(nombres[:-1])} y {nombres[-1]}"

    h1("3. Series de tiempo construidas (a partir de entrenamiento)")
    p(f"Se construyó la serie obligatoria (total mensual) y se seleccionaron dos categorías de análisis: "
      f"<b>(i) Vías de ingreso</b> ({_enumerar([s['clave'] for s in vias])}) y <b>(ii) Países de residencia</b>, "
      f"tomando el top {len(paises)} según el acumulado de todo el período de estudio 2009–2026 (no solo "
      f"entrenamiento): {_enumerar([s['clave'] for s in paises])}. En total se obtienen "
      f"1 + {len(vias)} + {len(paises)} = {len(lista)} series mensuales.")
    mar = next((s for s in vias if s["clave"] == "Marítima"), None)
    detalle_mar = (f"que no tiene ningún registro durante {mar['racha_ceros_max']} meses consecutivos por el cierre "
                   f"de fronteras marítimas") if mar else "sin registros durante la pandemia"
    note(f"<b>Nota metodológica:</b> todas las series se reindexaron contra el rango fijo de {tr['n_meses']} meses de "
         f"entrenamiento (no contra el propio primer/último dato de cada subserie), de forma que los meses sin "
         f"ningún registro se reflejen como 0 en vez de recortar la serie. Esto fue clave para la vía Marítima, "
         f"{detalle_mar}: sin este ajuste la serie parecía terminar antes de tiempo.")

    # ------------------------- 4. analisis de las series y estacionariedad
    h1("4. Análisis de las series y determinación de estacionariedad")
    p(f"Para cada serie se presenta: inicio, fin y frecuencia; el gráfico de la serie con su descomposición en "
      f"tendencia, estacionalidad y residuo; las funciones de autocorrelación (ACF) y autocorrelación parcial "
      f"(PACF); la cuantificación de la fuerza de la estacionalidad y de la tendencia; el diagnóstico de "
      f"estacionariedad en varianza con la transformación aplicada; y la determinación del número de "
      f"diferenciaciones necesarias para alcanzar estacionariedad en media, contrastada con las pruebas de "
      f"Dickey-Fuller Aumentada (ADF) y KPSS.")
    note("<b>Nota sobre las dos pruebas:</b> ADF y KPSS plantean hipótesis nulas opuestas y por eso se usan "
         "juntas. En ADF la H0 es que existe una raíz unitaria (la serie <i>no</i> es estacionaria), así que "
         "interesa <i>rechazar</i>. En KPSS la H0 es que la serie <i>sí</i> es estacionaria, así que interesa "
         "<i>no</i> rechazar. Una serie se declara estacionaria solo cuando ambas coinciden. Cuando el "
         "estadístico KPSS cae fuera del rango tabulado, statsmodels satura el p-valor; en esos casos se reporta "
         "el límite (por ejemplo &gt;0.1) y no el valor saturado, que sería engañoso.")

    for s in lista:
        adf = s["adf"]
        forma = s["forma"]
        var = s["varianza"]
        tr_s = s["transformacion"]
        dif = s["diferenciacion"]
        pr = s["pruebas"]

        bloque = [
            Paragraph(s["nombre"], styles["H2"]),
            Paragraph(
                f"<b>Inicio:</b> {s['inicio']} &nbsp;&nbsp; <b>Fin:</b> {s['fin']} &nbsp;&nbsp; "
                f"<b>Frecuencia:</b> mensual (MS) &nbsp;&nbsp; <b>N:</b> {s['n_obs']} obs. &nbsp;&nbsp; "
                f"<b>Media:</b> {s['media']:,.1f} &nbsp;&nbsp; <b>Desv. estándar:</b> {s['sd']:,.1f} &nbsp;&nbsp; "
                f"<b>Mín–Máx:</b> {s['min']:,.0f} – {s['max']:,.1f}", styles["Body"]),
            sized_image(ROOT / s["fig_panel"], 6.0),
            Paragraph(f"Figura. {s['nombre']} — serie, tendencia, estacionalidad y residuo (train).",
                      styles["Caption"]),
        ]
        story.append(KeepTogether(bloque))

        if s["clave"] in INTERPRETACIONES:
            p(INTERPRETACIONES[s["clave"]].format(
                sd=s["sd"], pvalue=adf["pvalue"], n_series=len(lista),
                meses_en_cero=s["meses_en_cero"], racha_ceros_max=s["racha_ceros_max"]))

        # --- forma: estacionalidad y tendencia cuantificadas
        if forma["descomposicion_ok"]:
            calificacion = ("por encima" if forma["estacionalidad_fuerte"] else "por debajo")
            implicacion = ("la estacionalidad domina la variación y justifica una diferenciación estacional"
                           if forma["estacionalidad_fuerte"] else
                           "la estacionalidad es visible y regular pero explica una fracción menor de la "
                           "variación no atribuible a la tendencia: hay que modelarla con términos estacionales, "
                           "pero por sí sola no justifica una diferenciación estacional")
            p(f"<b>Estacionalidad y tendencia.</b> Medida sobre la serie en {forma['serie_base']}, la fuerza de la "
              f"estacionalidad (criterio de Hyndman, 1 − Var(residuo)/Var(estacional+residuo)) es "
              f"<b>{forma['fuerza_estacionalidad']:.3f}</b>, {calificacion} del umbral de "
              f"{forma['umbral_estacionalidad_fuerte']} usado como referencia de estacionalidad fuerte: "
              f"{implicacion}. La pendiente de la tendencia es <b>{forma['pendiente_anual']:+.4f}</b> por año en "
              f"escala {forma['serie_base']} ({forma['pct_anual_sobre_media']:+.2f}% anual sobre el nivel medio de "
              f"la tendencia), es decir una tendencia <b>{forma['tendencia_signo']}</b> en el tramo analizado.")
        else:
            note("<b>Descomposición no disponible</b> para esta serie, de modo que la fuerza de la estacionalidad "
                 "y la pendiente de la tendencia no se reportan.")

        # --- ACF y PACF
        story.append(sized_image(ROOT / s["fig_acf"], 4.3))
        story.append(Paragraph(f"Figura. Función de autocorrelación (ACF, {series_doc['lags_acf']} rezagos) "
                               f"sobre la serie en nivel.", styles["Caption"]))
        story.append(sized_image(ROOT / s["fig_pacf"], 4.3))
        story.append(Paragraph(f"Figura. Función de autocorrelación parcial (PACF, "
                               f"{series_doc['lags_pacf']} rezagos) sobre la serie ya transformada y diferenciada "
                               f"({dif['orden_recomendado']}).", styles["Caption"]))

        # --- varianza y transformacion
        p(f"<b>Estacionariedad en varianza.</b> Para diagnosticarla se divide la serie en tramos de 12 meses y se "
          f"mide la correlación entre la desviación estándar y la media de cada tramo. Sobre el tramo "
          f"pre-pandemia ({var['tramo_evaluado']['inicio']} a {var['tramo_evaluado']['fin']}) esa correlación es "
          f"<b>{var['corr_nivel_pre_pandemia']:+.3f}</b>: la dispersión crece junto con el nivel, así que la serie "
          f"<b>no</b> es estacionaria en varianza. Medida sobre el tramo completo de entrenamiento la correlación "
          f"cae a {var['corr_nivel_completo']:+.3f}, porque el colapso de 2020-2021 introduce un tramo de nivel "
          f"bajo y dispersión alta que rompe la relación monótona y <b>enmascara el diagnóstico</b>; por eso el "
          f"chequeo se hace sobre el tramo pre-pandemia. Se aplica la transformación "
          f"<b>{tr_s['nombre']}</b> (inversa: {tr_s['inversa']}), tras la cual la correlación baja a "
          f"<b>{var['corr_post_transformacion']:+.3f}</b>: la varianza deja de depender del nivel.")

        # --- tabla de pruebas en las tres etapas
        filas = [["Etapa de la serie", "ADF estad.", "ADF p", "KPSS estad.", "KPSS p", "¿Estacionaria?"]]
        etapas = [("Nivel original", "nivel"),
                  (f"Transformada ({tr_s['nombre']})", "transformada"),
                  (f"Transformada + d={dif['d']}, D={dif['D']}", "final")]
        for etiqueta, llave in etapas:
            e = pr[llave]
            filas.append([etiqueta,
                          f"{e['adf']['stat']:.3f}", f"{e['adf']['pvalue']:.4f}",
                          f"{e['kpss']['stat']:.3f}", e["kpss"]["pvalue_reportable"],
                          "Sí" if e["ambas_estacionaria"] else "No"])
        tabla(filas, [1.9 * inch, 0.8 * inch, 0.7 * inch, 0.85 * inch, 0.7 * inch, 0.95 * inch],
              font_size=8, align="CENTER")

        # --- diferenciacion
        conclusion_nivel = ("se rechaza H0" if adf["estacionaria"] else "no se rechaza H0")
        p(f"<b>Estacionariedad en media y diferenciaciones.</b> Sobre el nivel, el ADF da un p-valor de "
          f"{adf['pvalue']:.4f} ({conclusion_nivel}) y la ACF decae lentamente con un patrón oscilante de periodo "
          f"aproximadamente anual — ambos síntomas de no estacionariedad en media. Para la componente estacional, "
          f"<b>D = {dif['D']}</b>: {dif['criterio_D']}. El ADF no se usa para decidir <i>D</i> porque contrasta una "
          f"raíz unitaria en el rezago 1 y no está diseñado para raíces unitarias estacionales. Para la componente "
          f"regular, <b>d = {dif['d']}</b>, aplicando el criterio de {dif['criterio_d']}. La especificación "
          f"resultante es <b>{dif['orden_recomendado']}</b>, y sobre ella ambas pruebas coinciden en "
          f"estacionariedad (última fila de la tabla), lo que confirma que el número de diferenciaciones es "
          f"suficiente y no excesivo.")
        hr()

    # --------------------------------------- 4.8 resumen de ordenes de integracion
    h2("4.8 Resumen: transformación y órdenes de integración por serie")
    filas = [["Serie", "Transf.", "d", "D", "s", "Fuerza estac.", "Pendiente anual", "Estacionaria"]]
    for s in lista:
        dif, forma = s["diferenciacion"], s["forma"]
        filas.append([
            s["clave"], s["transformacion"]["nombre"], str(dif["d"]), str(dif["D"]), str(dif["s"]),
            f"{forma['fuerza_estacionalidad']:.3f}" if forma["fuerza_estacionalidad"] is not None else "n/d",
            f"{forma['pendiente_anual']:+.4f}" if forma["pendiente_anual"] is not None else "n/d",
            "Sí" if dif["estacionaria_final"] else "No",
        ])
    tabla(filas, [1.55 * inch, 0.65 * inch, 0.3 * inch, 0.3 * inch, 0.3 * inch, 0.8 * inch,
                  0.95 * inch, 0.85 * inch], font_size=7.5, align="CENTER")
    p(f"Las {len(lista)} series requieren la misma transformación de varianza, lo que simplifica la comparación "
      f"posterior entre ellas: todas se modelan en escala logarítmica y las predicciones deben revertirse con la "
      f"función inversa antes de calcular cualquier métrica de error, para que los resultados queden en viajeros y "
      f"sean interpretables. Ninguna serie requiere diferenciación estacional, y la diferenciación regular varía "
      f"entre 0 y {max(s['diferenciacion']['d'] for s in lista)} según la serie. Esta tabla es la especificación de "
      f"partida para la identificación de los órdenes p y q de los modelos ARIMA.")
    note("<b>Sobre el signo de la pendiente:</b> cuatro de las siete series presentan pendiente negativa. Esto "
         "<b>no</b> indica un declive estructural del turismo, sino que el tramo de entrenamiento termina en marzo "
         "de 2021 y el ajuste lineal queda dominado por el colapso pandémico. La sección 1.7 muestra que, sobre el "
         "período completo, la mayoría de las series se recupera a partir de 2022. La pendiente debe leerse como "
         "descriptor del tramo de entrenamiento, no como proyección.")

    story.append(PageBreak())

    # ------------------------------------------------------- 5. proximos pasos
    h1("5. Próximos pasos")
    bullet(f"Completar la construcción de las {len(lista)} series también para el conjunto de prueba, para poder "
           f"evaluar predicciones fuera de muestra.")
    bullet("Seleccionar p, d, q (y componente estacional P, D, Q, s si aplica) con base en ACF/PACF, contrastar con "
           "auto_arima/auto.arima, y ajustar varios modelos ARIMA por serie, comparando residuos, AIC y BIC.")
    bullet("Ajustar y comparar modelos Prophet, Holt-Winters, suavizamiento exponencial y seasonal naive frente a "
           "los modelos ARIMA.")
    bullet("Generar predicciones sobre el conjunto de prueba y comparar todos los modelos con MAE, RMSE, AIC y BIC "
           "para seleccionar el mejor modelo por serie.")
    bullet("Desarrollar el análisis comparativo entre las series de cada categoría (estacionalidad, tendencia, "
           "volatilidad, impacto de la pandemia) y los hallazgos generales orientados a la toma de decisiones del "
           "INGUAT.")


def main():
    datos = cargar_resultados()
    construir(datos)

    salida_dir = ROOT / "outputs"
    salida_dir.mkdir(parents=True, exist_ok=True)
    salida = salida_dir / "Laboratorio1_Avance_SeriesDeTiempo.pdf"

    doc = SimpleDocTemplate(
        str(salida), pagesize=letter,
        topMargin=0.7 * inch, bottomMargin=0.7 * inch,
        leftMargin=0.75 * inch, rightMargin=0.75 * inch,
        title="Laboratorio 1 - Avance - Series de Tiempo - CC3084",
        author="CC3084 Data Science - UVG",
    )
    doc.build(story)
    print(f"PDF generado en {salida}")


if __name__ == "__main__":
    main()
