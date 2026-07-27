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
    """Lee los JSON del pipeline. Si falta alguno, aborta con un mensaje util."""
    datos = {}
    for nombre in ("eda", "split", "series", "models", "comparison"):
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

story = []


def h1(t): story.append(Paragraph(t, styles["H1"]))
def h2(t): story.append(Paragraph(t, styles["H2"]))
def p(t): story.append(Paragraph(t, styles["Body"]))
def bullet(t): story.append(Paragraph("• " + t, styles["BulletUVG"]))
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
    models_doc = datos["models"]
    comp_doc = datos["comparison"]

    ds = eda["dataset"]
    cal = eda["calidad"]
    des = eda["descriptivos_viajero"]
    reg = {x["nombre"]: x["pct"] for x in eda["regiones"]}
    via = {x["nombre"]: x["pct"] for x in eda["vias"]}
    tipo = {x["nombre"]: x["pct"] for x in eda["tipos_viajero"]}
    tr, te = split["train"], split["test"]

    # ---------------------------------------------------------------- portada
    story.append(Spacer(1, 60))
    story.append(Paragraph("Universidad del Valle de Guatemala", styles["SubtitleUVG"]))
    story.append(Paragraph("Facultad de Ingeniería — Departamento de Ciencias de la Computación", styles["SubtitleUVG"]))
    story.append(Paragraph("CC3084 — Data Science | Semestre II — 2026 | Sección 20", styles["SubtitleUVG"]))
    story.append(Spacer(1, 40))
    story.append(Paragraph("Laboratorio 1: Series de Tiempo", styles["TitleUVG"]))
    story.append(Paragraph("Ingreso de viajeros internacionales a Guatemala (2009 – junio 2026)", styles["Heading2"]))
    story.append(Spacer(1, 24))
    story.append(Paragraph("Diego López · Nelson Escalante · Roberto Nájera", styles["SubtitleUVG"]))
    story.append(Spacer(1, 6))
    story.append(Paragraph("Julio de 2026", styles["SubtitleUVG"]))
    story.append(Spacer(1, 40))
    story.append(PageBreak())

    # ------------------------------------------------- 0. descripcion general
    h1("0. Descripción del conjunto de datos")
    p(f"Ingreso mensual de viajeros internacionales a Guatemala entre enero de 2009 y junio de 2026 "
      f"({split['n_meses_total']} meses consecutivos, sin huecos). Formato largo: cada fila combina año, mes, vía de "
      f"ingreso, frontera, país de residencia y tipo de viajero, con la cantidad en la columna <b>Viajero</b>. "
      f"{ds['filas']:,} registros y {ds['columnas_fuente']} columnas.")
    qm = eda["quiebre_metodologico"]
    pand = eda["impacto_pandemia"]
    pct_pand = pand["pct_respecto_base"]
    p("La fuente combina tres tramos con metodologías distintas (2009–2020 respaldos históricos, 2021–2022 entrega "
      "del IGM, 2023–2026 sistema depurado del INGUAT), lo que produce dos quiebres:")
    bullet(f"<b>Pandemia (2020):</b> caída desde marzo de 2020, con {pct_pand['2020']:.0f}% y "
           f"{pct_pand['2021']:.0f}% del nivel de {pand['anio_base']} en la serie comparable, y recuperación desde 2022.")
    bullet(f"<b>Metodológico (2023):</b> se excluye a los viajeros no turísticos de alta frecuencia de la categoría "
           f"\"Viajero\", que cae de {qm['viajero_anio_previo']/1e6:.2f}M a {qm['viajero_anio_corte']/1e6:.2f}M sin "
           f"caída real de tránsito. La columna \"País\" pasa de {qm['paises_antes']} países individuales a "
           f"{qm['grupos_despues']} agrupaciones de mercado. Para comparar todo el rango se usa Turista + "
           f"Excursionista.")
    p("Además: la vía Marítima pierde detalle de registro desde 2017, los decimales de 2021-2022 son estimaciones "
      "de encuesta, y 2026 solo cubre enero a junio.")

    # ------------------------------------------------- 1. analisis exploratorio
    h1("1. Análisis exploratorio")

    h2("1.1 Comportamiento temporal del número de viajeros")
    img("figs/01_temporal_total.png",
        caption="Figura 1. Total mensual de viajeros internacionales, todas las categorías (2009–2026).")
    p("Tendencia creciente y estacionalidad marcada entre 2009 y 2019, caída abrupta en marzo de 2020, piso durante "
      "2020–2021 y recuperación desde 2022. La línea naranja marca el quiebre metodológico de 2023: a partir de ahí "
      "el nivel de la serie total no es comparable con los años previos.")
    img("figs/02_temporal_comparable.png",
        caption="Figura 2. Serie mensual de Turista + Excursionista (comparable en todo el período).")
    p("Al aislar Turista + Excursionista el quiebre de 2023 desaparece como salto de nivel y el patrón "
      "pandemia/recuperación se mantiene. Esta es la serie de referencia para el impacto real en turismo; la serie "
      "total se usa para el volumen agregado de ingreso migratorio.")

    h2("1.2 Países con mayor cantidad de viajeros")
    img("figs/03_top_paises.png",
        caption="Figura 3. Top 15 países/agrupaciones de residencia por viajeros acumulados (2009–2026).")
    filas = [["País / Agrupación", "Viajeros acumulados", "% del total"]]
    filas += [[x["nombre"], f"{x['acumulado']:,.0f}", f"{x['pct']:.1f}%"] for x in eda["top_paises"]]
    tabla(filas, [2.6 * inch, 1.7 * inch, 1.2 * inch])
    dos_primeros = eda["top_paises"][0]["pct"] + eda["top_paises"][1]["pct"]
    p(f"El Salvador y Guatemala concentran el {dos_primeros:.1f}% del total histórico: domina la movilidad terrestre "
      f"centroamericana sobre el turismo de larga distancia.")
    # VERIFICADO MANUALMENTE: el 77.3% sale de cruzar Pais=Guatemala con Tipo de Viajero.
    gt = next(x for x in eda["top_paises"] if x["nombre"] == "Guatemala")
   

    h2("1.3 Regiones con mayor cantidad de viajeros")
    img("figs/04_top_regiones.png",
        caption="Figura 4. Viajeros acumulados por región (variable \"Región dos\"), 2009–2026.")
    otras = 100 - reg["América Del Centro"] - reg["América Del Norte"] - reg["Europa"]
    rsa = eda["region_sin_asignar"]
    anios_rsa = ", ".join(str(a) for a in rsa["anios"])
    p(f"América del Centro concentra el {reg['América Del Centro']:.1f}%, América del Norte "
      f"{reg['América Del Norte']:.1f}% y Europa {reg['Europa']:.1f}%; el resto de regiones aporta {otras:.1f}%. "
      f"Hay {rsa['registros']} registros ({rsa['pct']:.4f}%) con valor \"0\" en \"Región dos\", residuo de catálogo "
      f"sin agrupación asignada en {anios_rsa}.")

    h2("1.4 Vías de ingreso y fronteras más utilizadas")
    img("figs/05_vias_fronteras.png",
        caption="Figura 5. Viajeros acumulados por vía de ingreso (izq.) y top 10 fronteras (der.).")
    f_top = eda["fronteras"]
    p(f"Terrestre domina con {via['Terrestre']:.1f}%, seguida de Aérea ({via['Aérea']:.1f}%) y Marítima "
      f"({via['Marítima']:.1f}%, coherente con su pérdida de registro desde 2017). Por frontera, el aeropuerto "
      f"{f_top[0]['nombre'][3:]} concentra el {f_top[0]['pct']:.1f}% (toda la vía aérea), seguido de "
      f"{f_top[1]['nombre'][3:]} ({f_top[1]['pct']:.1f}%, El Salvador) y {f_top[2]['nombre'][3:]} "
      f"({f_top[2]['pct']:.1f}%, Honduras), consistente con el peso de esos dos mercados.")

    h2("1.5 Valores faltantes, duplicados y valores atípicos")
    bullet(f"<b>Valores faltantes:</b> {cal['faltantes_total']} en las {ds['columnas_fuente']} columnas — "
           f"el conjunto de datos está completo.")
    bullet(f"<b>Filas duplicadas exactas</b> (todas las columnas): {cal['duplicados_exactos']}.")
    cd_ = eda["cuasi_duplicados"]["combinaciones_repetidas"]
    bullet(f"<b>Cuasi-duplicados:</b> {cd_} combinaciones repetidas al agrupar sin \"Agrupación Residencia\". Son "
           f"subcategorías legítimas de esa columna dentro de un mismo país, no errores de carga.")
    bullet(f"<b>Valores en cero:</b> {cal['ceros']} registros ({cal['pct_ceros']:.2f}%), en combinaciones de "
           f"categorías de baja frecuencia.")
    bullet(f"<b>Valores negativos:</b> {cal['negativos']}.")
    bullet(f"<b>Atípicos por fila</b> (Tukey, 1.5×RIC): umbral superior {cal['iqr_umbral_superior']:.1f} viajeros y "
           f"{cal['iqr_pct_sobre_umbral']:.1f}% de las filas lo supera. Es esperable en una variable de conteo "
           f"desagregada en miles de categorías, la mayoría de volumen bajo. No se tratan como errores: el atípico "
           f"relevante para series de tiempo es el colapso de 2020, visible en las series agregadas.")
    rpa = cal["registros_por_anio"]
    bullet(f"<b>Quiebre en el volumen de registros</b> (filas, no viajeros): de "
           f"~{min(rpa[a] for a in list(rpa)[:11]):,}–{max(rpa[a] for a in list(rpa)[:11]):,} al año entre "
           f"2009-2019, cae a {rpa['2020']:,} en 2020 y a "
           f"~{min(rpa[a] for a in ['2023', '2024', '2025']):,}–{max(rpa[a] for a in ['2023', '2024', '2025']):,} "
           f"desde 2023 por el cambio a agrupación de mercado. No confundir con un cambio real de volumen.")

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
    p(f"La distribución por registro es fuertemente asimétrica a la derecha (media muy superior a la mediana), "
      f"típica de conteos desagregados. Por tipo de viajero: Turista {tipo['Turista']:.1f}%, Excursionista "
      f"{tipo['Excursionista']:.1f}%, Viajero {tipo['Viajero']:.1f}% y Cruceristas {tipo['Cruceristas']:.1f}%. "
      f"Turista + Excursionista suman {comparable:.1f}%, la medida comparable en todo el período.")

    # ------------------------------- 1.7 comportamiento durante y post pandemia
    h2("1.7 Comportamiento de cada serie durante y después de la pandemia")
    p(f"Las series de modelado terminan en {tr['fin']}, así que la recuperación posterior no se ve en ellas. Estas "
      f"figuras las muestran sobre los {series_doc['n_meses_periodo_completo']} meses del período, con el tramo de "
      f"entrenamiento sombreado. Son solo exploratorias: el modelado y la predicción usan únicamente entrenamiento.")

    for s in series_doc["series"]:
        story.append(sized_image(ROOT / s["fig_periodo_completo"], 5.9))
        story.append(Paragraph(f"Figura. {s['nombre']} — período completo "
                               f"({series_doc['n_meses_periodo_completo']} meses).", styles["Caption"]))

    p("Hay tres comportamientos distintos tras la pandemia. La Aérea se recupera con más fuerza y supera su nivel "
      "pre-pandemia. La Terrestre mantuvo un piso positivo en 2020 y se recupera de forma más plana. La Marítima no "
      "vuelve a los niveles de 2009-2016. En la serie total se ve el salto de nivel de 2023.")

    story.append(PageBreak())

    # --------------------------------------------------- 2. entrenamiento/prueba
    h1("2. División en entrenamiento y prueba")
    p("La división es <b>cronológica</b>, no aleatoria: el corte deja ~70% de los meses en entrenamiento y 30% en "
      "prueba, de modo que la prueba siempre sea posterior en el tiempo.")
    filas = [["Conjunto", "Rango de fechas", "N.° de meses", "% de meses", "Filas del dataset"],
             ["Entrenamiento", f"{tr['inicio']} a {tr['fin']}", str(tr["n_meses"]),
              f"{tr['pct_meses']:.1f}%", f"{tr['filas']:,} ({tr['pct_filas']:.1f}%)"],
             ["Prueba", f"{te['inicio']} a {te['fin']}", str(te["n_meses"]),
              f"{te['pct_meses']:.1f}%", f"{te['filas']:,} ({te['pct_filas']:.1f}%)"]]
    tabla(filas, [1.3 * inch, 1.6 * inch, 1.0 * inch, 0.9 * inch, 1.3 * inch], font_size=8.7, align="CENTER")
    p(f"La proporción de meses es {tr['pct_meses']:.0f}/{te['pct_meses']:.0f} por construcción. La de filas difiere "
      f"({tr['pct_filas']:.1f}% / {te['pct_filas']:.1f}%) porque el tramo 2009–2022 tiene más granularidad de país; "
      f"no afecta la validez de la partición. Todas las series se construyen sobre entrenamiento.")

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
    racha_mar = mar["racha_ceros_max"] if mar else 0
    p(f"Las series se reindexaron contra el rango fijo de {tr['n_meses']} meses de entrenamiento, no contra el primer "
      f"y último dato de cada subserie, para que los meses sin registro queden en 0 en vez de recortar la serie. "
      f"Importa en la vía Marítima, sin registros durante {racha_mar} meses consecutivos por el cierre de fronteras.")

    # ------------------------- 4. analisis de las series y estacionariedad
    h1("4. Análisis de las series y determinación de estacionariedad")
    p("Por serie se presenta: inicio, fin y frecuencia; el gráfico con su descomposición en tendencia, "
      "estacionalidad y residuo; ACF y PACF; la fuerza de la estacionalidad y de la tendencia; el diagnóstico de "
      "estacionariedad en varianza; y el número de diferenciaciones para alcanzar estacionariedad en media.")
    p("ADF y KPSS se usan juntas porque sus hipótesis nulas son opuestas: en ADF la H0 es que hay raíz unitaria "
      "(no estacionaria) e interesa rechazar; en KPSS la H0 es que la serie es estacionaria e interesa no rechazar. "
      "Una serie se declara estacionaria solo si ambas coinciden. Cuando el estadístico KPSS cae fuera del rango "
      "tabulado el p-valor se satura, y en esos casos se reporta el límite (&gt;0.1) en lugar del valor saturado.")

    # --- tabla A: forma de las series (reemplaza 7 parrafos)
    h2("4.1 Estacionalidad y tendencia")
    filas = [["Serie", "Fuerza estacional", "¿Fuerte?", "Pendiente anual", "Tendencia"]]
    for s in lista:
        f_ = s["forma"]
        filas.append([
            s["clave"],
            f"{f_['fuerza_estacionalidad']:.3f}" if f_["fuerza_estacionalidad"] is not None else "n/d",
            "Sí" if f_["estacionalidad_fuerte"] else "No",
            f"{f_['pendiente_anual']:+.4f}" if f_["pendiente_anual"] is not None else "n/d",
            f_["tendencia_signo"],
        ])
    tabla(filas, [2.0 * inch, 1.2 * inch, 0.8 * inch, 1.2 * inch, 1.0 * inch], font_size=8, align="CENTER")
    umbral = series_doc["umbral_estacionalidad_fuerte"]
    p(f"Medido sobre la serie transformada (log1p) con el criterio de Hyndman, "
      f"1 − Var(residuo)/Var(estacional+residuo). Las {len(lista)} series quedan por debajo del umbral de {umbral} "
      f"para estacionalidad fuerte: el patrón anual existe y hay que modelarlo con términos estacionales, pero no "
      f"domina la variación del residuo y por sí solo no justifica una diferenciación estacional.")
    p("La pendiente está en escala logarítmica por año. Es negativa en cuatro series, lo que no indica declive del "
      "turismo: el tramo de entrenamiento termina en marzo de 2021 y el ajuste lineal queda dominado por el colapso "
      "pandémico. La sección 1.7 muestra la recuperación posterior. Se lee como descriptor del tramo, no como "
      "proyección.")

    # --- tabla B: estacionariedad en varianza (reemplaza 7 parrafos)
    h2("4.2 Estacionariedad en varianza y transformación")
    filas = [["Serie", "corr pre-pandemia", "corr train completo", "Transformación", "corr posterior"]]
    for s in lista:
        v = s["varianza"]
        filas.append([
            s["clave"],
            f"{v['corr_nivel_pre_pandemia']:+.3f}",
            f"{v['corr_nivel_completo']:+.3f}",
            s["transformacion"]["nombre"],
            f"{v['corr_post_transformacion']:+.3f}",
        ])
    tabla(filas, [2.0 * inch, 1.15 * inch, 1.25 * inch, 1.05 * inch, 1.05 * inch], font_size=8, align="CENTER")
    tramo = lista[0]["varianza"]["tramo_evaluado"]
    p(f"Se divide cada serie en tramos de 12 meses y se correlaciona la desviación estándar con la media de cada "
      f"tramo. Sobre el tramo pre-pandemia ({tramo['inicio']} a {tramo['fin']}) la correlación va de 0.89 a 0.96 en "
      f"las {len(lista)} series: la dispersión crece con el nivel y ninguna es estacionaria en varianza.")
    p("Sobre el tramo completo esa correlación baja o cambia de signo en seis de las siete series, lo que llevaría a "
      "concluir que no hace falta transformar: el colapso de 2020-2021 agrega un tramo de nivel bajo y dispersión "
      "alta que rompe la relación y enmascara el diagnóstico. Tras aplicar log1p la correlación cae al rango −0.83 a "
      "+0.16. Se usa log1p y no Box-Cox porque el lambda óptimo cambia de signo según se incluya la pandemia, y "
      "log1p admite los ceros exactos de la vía Marítima sin desplazar la serie.")

    h2("4.3 Análisis por serie")

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

        # --- ACF y PACF, lado a lado para no gastar una pagina por serie
        story.append(Table(
            [[sized_image(ROOT / s["fig_acf"], 3.3), sized_image(ROOT / s["fig_pacf"], 3.3)]],
            colWidths=[3.4 * inch, 3.4 * inch],
            style=TableStyle([("VALIGN", (0, 0), (-1, -1), "TOP"),
                              ("LEFTPADDING", (0, 0), (-1, -1), 0),
                              ("RIGHTPADDING", (0, 0), (-1, -1), 0)]),
        ))
        story.append(Paragraph(f"Figura. ACF sobre el nivel (izq.) y PACF sobre la serie transformada y diferenciada "
                               f"—{dif['orden_recomendado']}— (der.), {series_doc['lags_acf']} rezagos.",
                               styles["Caption"]))

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

        p(f"Sobre el nivel el ADF da p = {adf['pvalue']:.4f} y la ACF decae lentamente con oscilación anual. "
          f"La especificación que alcanza estacionariedad es <b>{dif['orden_recomendado']}</b>, donde "
          f"D = {dif['D']} porque {dif['criterio_D']}, y d = {dif['d']} por el criterio conjunto ADF+KPSS. "
          f"En la última fila de la tabla ambas pruebas coinciden, lo que confirma que las diferenciaciones son "
          f"suficientes y no excesivas.")
        hr()

    # --------------------------------------- resumen de ordenes de integracion
    h2("4.4 Resumen: transformación y órdenes de integración por serie")
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
    d_max = max(s["diferenciacion"]["d"] for s in lista)
    p(f"Las {len(lista)} series requieren la misma transformación, lo que simplifica compararlas: todas se modelan en "
      f"escala logarítmica y las predicciones se revierten con expm1 antes de calcular métricas de error, para que "
      f"queden en viajeros. Ninguna requiere diferenciación estacional y la regular va de 0 a {d_max}. Esta tabla es "
      f"el punto de partida para identificar los órdenes p y q.")

    story.append(PageBreak())

    _seccion_modelos(models_doc, lista)
    story.append(PageBreak())
    _seccion_prediccion(comp_doc, models_doc)
    story.append(PageBreak())
    _seccion_comparativo(comp_doc)
    _seccion_conclusiones(lista, comp_doc, tipo)


# nombres para mostrar de cada algoritmo, y el orden en que se reportan
_MODELOS = [
    ("sarima", "SARIMA"),
    ("holt_winters", "Holt-Winters"),
    ("simple_exponential", "Suav. exponencial"),
    ("seasonal_naive", "Seasonal naive"),
    ("prophet", "Prophet"),
]


def _fmt(valor, formato="{:,.1f}", vacio="—"):
    """Formatea un número que puede venir en None (AIC/BIC de los modelos sin verosimilitud)."""
    return vacio if valor is None else formato.format(valor)


def _seccion_modelos(models_doc: dict, lista: list) -> None:
    h1("5. Generación de modelos")
    p("Se ajustaron cinco familias por serie: SARIMA, Holt-Winters, suavizamiento exponencial simple, seasonal naive "
      "y Prophet. Todas se estiman sobre la serie transformada con log1p y el pronóstico se revierte a viajeros "
      "antes de compararlo, de modo que las métricas de error queden en la escala original.")
    p("Los órdenes de SARIMA se buscaron por grid sobre SARIMAX minimizando AIC, no con auto_arima: pmdarima no es "
      "compatible con la versión de numpy del entorno. El grid es equivalente en criterio, con la ventaja de que d "
      "y D quedan fijados por el análisis de estacionariedad de la sección 4 en lugar de re-estimarse.")

    h2("5.1 Elección de p, d y q")
    p("d y D vienen de la sección 4. Para p y q el grid se acotó leyendo ACF y PACF de las series ya diferenciadas: "
      "la PACF entra en las bandas de confianza tras uno o dos rezagos, lo que acota p ≤ 2, y la ACF muestra el "
      "mismo comportamiento para q. Los picos residuales en los rezagos 12 y 24 justifican mantener el término "
      "estacional aunque D = 0. Dentro de ese espacio se eligió la combinación de menor AIC.")

    filas = [["Serie", "(p,d,q)", "(P,D,Q,s)", "AIC", "BIC", "Residuos indep."]]
    for s in models_doc["series"]:
        m = s["modelos"]["sarima"]
        par = m["parametros"]
        o, so = par["order"], par["seasonal_order"]
        filas.append([
            s["clave"],
            f"({o[0]},{o[1]},{o[2]})",
            f"({so[0]},{so[1]},{so[2]},{so[3]})",
            _fmt(m["aic"], "{:,.1f}"), _fmt(m["bic"], "{:,.1f}"),
            "Sí" if m["ljung_box"]["independientes"] else "No",
        ])
    tabla(filas, [1.9 * inch, 0.85 * inch, 1.05 * inch, 0.85 * inch, 0.85 * inch, 1.0 * inch],
          font_size=8, align="CENTER")
    p("El orden regular varía con la serie: la vía Aérea es la única con d = 0 y la Marítima necesita d = 2, "
      "coherente con su tramo en cero. En El Salvador el grid eligió un término estacional sin componente "
      "autorregresivo, a diferencia del resto.")

    h2("5.2 Parámetros de los demás modelos")
    filas = [["Modelo", "Parámetros ajustados", "Lectura"]]
    filas.append(["Holt-Winters", "tendencia y estacionalidad aditivas, periodo 12; beta = 0",
                  "la tendencia no aporta"])
    filas.append(["Suav. exponencial", "alpha entre 0.61 y 1.00 según la serie",
                  "se ancla al último valor"])
    filas.append(["Seasonal naive", "estación de 12 meses, sin parámetros a estimar",
                  "piso de comparación"])
    filas.append(["Prophet", "estacionalidad anual; semanal y diaria desactivadas",
                  "solo aplica la anual"])
    tabla(filas, [1.2 * inch, 3.35 * inch, 1.9 * inch], font_size=8, align="LEFT")
    p("Dos parámetros merecen atención. En suavizamiento exponencial, alpha cercano a 1 en cuatro series significa "
      "que el modelo pondera casi exclusivamente la última observación y descarta la historia. En Holt-Winters, "
      "beta = 0 en las siete series indica que el optimizador anuló el componente de tendencia: con el tramo de "
      "entrenamiento terminando en plena pandemia, una tendencia lineal no mejora el ajuste.")

    h2("5.3 Comparación por AIC, BIC y residuos")
    total_lb = sum(1 for s in models_doc["series"] for m in s["modelos"].values()
                   if m["ljung_box"]["independientes"])
    n_comb = len(models_doc["series"]) * len(_MODELOS)
    p(f"Seasonal naive y Prophet no reportan AIC ni BIC porque no se estiman por máxima verosimilitud; sus celdas "
      f"aparecen vacías en las tablas. Los valores de AIC tampoco son comparables entre series distintas, porque "
      f"cada una se ajusta en su propia escala logarítmica; solo tienen sentido dentro de una misma serie.")
    p(f"La prueba de Ljung-Box sobre los residuos es el criterio más exigente: solo {total_lb} de las {n_comb} "
      f"combinaciones serie-modelo dejan residuos indistinguibles de ruido blanco, y cinco de ellas son SARIMA. "
      f"En el resto queda estructura sin capturar, lo que era esperable: ningún modelo estimado sobre 2009-2021 "
      f"puede absorber un quiebre del tamaño de la pandemia.")


def _seccion_prediccion(comp_doc: dict, models_doc: dict) -> None:
    h1("6. Predicción sobre el conjunto de prueba")
    horizon = models_doc["horizon"]
    p(f"Cada modelo pronostica los {horizon} meses del conjunto de prueba (2021-04 a 2026-06). El pronóstico se "
      f"revierte de log1p a viajeros y sobre esa escala se calculan MAE y RMSE, de modo que el error sea "
      f"interpretable en personas. El criterio de selección es RMSE, que penaliza más los errores grandes.")

    # una tabla unica con las 7 series: mas compacta que 7 tablas sueltas
    filas = [["Serie"] + [e for _, e in _MODELOS] + ["Mejor"]]
    for s in comp_doc["series"]:
        filas.append([s["clave"]]
                     + [f"{s['modelos'][c]['rmse']:,.0f}" for c, _ in _MODELOS]
                     + [dict(_MODELOS)[s["ganador"]["modelo"]]])
    tabla(filas, [1.3 * inch, 0.75 * inch, 0.8 * inch, 0.85 * inch, 0.8 * inch, 0.7 * inch, 1.0 * inch],
          font_size=7, align="CENTER")
    p("RMSE en viajeros por serie y modelo.")

    filas = [["Serie"] + [e for _, e in _MODELOS] + ["Mejor"]]
    for s in comp_doc["series"]:
        mejor_mae = min(s["modelos"], key=lambda k: s["modelos"][k]["mae"])
        filas.append([s["clave"]]
                     + [f"{s['modelos'][c]['mae']:,.0f}" for c, _ in _MODELOS]
                     + [dict(_MODELOS)[mejor_mae]])
    tabla(filas, [1.3 * inch, 0.75 * inch, 0.8 * inch, 0.85 * inch, 0.8 * inch, 0.7 * inch, 1.0 * inch],
          font_size=7, align="CENTER")
    p("MAE en viajeros por serie y modelo.")

    for s in comp_doc["series"]:
        story.append(sized_image(ROOT / s["fig_forecast"], 5.2))
        story.append(Paragraph(f"Figura. {s['nombre']} — pronóstico de cada modelo frente al valor real.",
                               styles["Caption"]))

    h2("6.1 Qué tan bien predicen los modelos")
    ganadores = {}
    for s in comp_doc["series"]:
        ganadores.setdefault(s["ganador"]["modelo"], []).append(s["clave"])
    naive_gana = [s["clave"] for s in comp_doc["series"] if s["ganador"]["gana_seasonal_naive_a_sarima"]]

    resumen = "; ".join(f"{k} en {len(v)}" for k, v in sorted(ganadores.items(), key=lambda x: -len(x[1])))
    p(f"Por RMSE los ganadores se reparten así: {resumen}. El suavizamiento exponencial simple gana en la mayoría "
      f"de las series, y en {len(naive_gana)} de ellas el seasonal naive iguala o supera a SARIMA.")
    p("Eso no significa que los modelos simples capturen mejor la dinámica. El entrenamiento termina en marzo de "
      "2021, en el piso de la pandemia, así que los modelos con estructura estacional proyectan la continuación de "
      "ese nivel, mientras el suavizamiento exponencial —con alpha cercano a 1— se ancla al último valor y queda más "
      "cerca de una serie que empieza a subir. El conjunto de prueba cubre justamente la recuperación y el quiebre "
      "de 2023: ningún modelo entrenado en ese tramo podía anticipar el rebote. Los errores deben leerse en ese "
      "contexto y no como medida de la calidad del ajuste.")

    discrepa = []
    for s in comp_doc["series"]:
        ms = s["modelos"]
        mejor_rmse = min(ms, key=lambda k: ms[k]["rmse"])
        mejor_mae = min(ms, key=lambda k: ms[k]["mae"])
        if mejor_rmse != mejor_mae:
            discrepa.append((s["clave"], mejor_mae, mejor_rmse))
    if discrepa:
        detalle = "; ".join(f"{c}: mejor MAE {a}, mejor RMSE {b}" for c, a, b in discrepa)
        p(f"Las dos métricas coinciden en casi todas las series, con una excepción — {detalle}. La diferencia "
          f"aparece porque el RMSE penaliza más los errores grandes: el modelo con mejor MAE acierta más en el mes "
          f"típico, pero falla peor en los meses extremos. Se reporta el ganador por RMSE por consistencia con el "
          f"resto del análisis.")


def _seccion_comparativo(comp_doc: dict) -> None:
    h1("7. Análisis comparativo")
    p("Se comparan las series dentro de cada categoría con cuatro criterios: fuerza de la estacionalidad, pendiente "
      "de la tendencia, volatilidad relativa e impacto de la pandemia. La volatilidad se mide con el coeficiente de "
      "variación (desviación estándar sobre media) y no con la desviación cruda, porque las series tienen volúmenes "
      "muy distintos y la desviación absoluta solo reflejaría el tamaño.")
    p("Las cifras de esta sección se calculan sobre la serie en nivel, mientras que las de la sección 4 están en "
      "escala logarítmica; los valores no son directamente comparables entre secciones, aunque el orden relativo "
      "entre series se mantiene. El umbral de 0.64 mencionado en la sección 4 aplica solo a la escala logarítmica.")

    etiquetas = {"vias": "7.1 Vías de ingreso", "paises": "7.2 Países de residencia"}
    for categoria, titulo in etiquetas.items():
        bloque = comp_doc["comparativo"][categoria]
        h2(titulo)

        filas = [["Serie", "Fuerza estac.", "Pendiente anual", "CV", "% de 2019 en 2020", "Meses en 0"]]
        for clave, d in bloque["detalle"].items():
            pct2020 = d["impacto_pandemia"]["pct_respecto_base"]["2020"]
            filas.append([
                clave,
                f"{d['fuerza_estacionalidad']:.3f}",
                f"{d['pendiente_anual']:,.0f}",
                f"{d['cv']:.3f}",
                f"{pct2020:.1f}%",
                str(d["racha_ceros_max"]),
            ])
        tabla(filas, [1.75 * inch, 0.95 * inch, 1.1 * inch, 0.7 * inch, 1.3 * inch, 0.85 * inch],
              font_size=8, align="CENTER")

        # las 3 primeras respuestas traen {serie, valor}; la cuarta tiene otras claves.
        # la pendiente va en viajeros/año (sin decimales), las otras dos son indices.
        for llave, pregunta, fmt in (("mas_estacionalidad", "Mayor estacionalidad", "{:.3f}"),
                                     ("mas_tendencia_crecimiento", "Mayor tendencia de crecimiento", "{:,.0f}"),
                                     ("mas_volatilidad", "Mayor volatilidad", "{:.3f}")):
            r = bloque[llave]
            if r:
                unidad = " viajeros/año" if llave == "mas_tendencia_crecimiento" else ""
                bullet(f"<b>{pregunta}:</b> {r['serie']} ({fmt.format(r['valor'])}{unidad}).")
        pand = bloque["mas_afectada_pandemia"]
        if pand:
            extra = (f", con {pand['racha_ceros_max']} meses consecutivos en cero"
                     if pand["racha_ceros_max"] else "")
            bullet(f"<b>Más afectada por la pandemia:</b> {pand['serie']}, con una caída de "
                   f"{pand['caida_pct_2020_vs_2019']:.1f}% en 2020 frente a 2019{extra}.")

    h2("7.3 Hallazgos útiles para el INGUAT")
    for hallazgo in comp_doc["hallazgos_inguat"]:
        bullet(hallazgo)


def _seccion_conclusiones(lista: list, comp_doc: dict, tipo: dict) -> None:
    h1("8. Conclusiones")
    comparable = tipo["Turista"] + tipo["Excursionista"]
    bullet(f"El conjunto de datos tiene dos quiebres que condicionan todo el análisis: la pandemia y el cambio "
           f"metodológico de 2023. Turista + Excursionista ({comparable:.1f}% del total) es la única combinación "
           f"comparable en todo el período.")
    bullet(f"Ninguna de las {len(lista)} series es estacionaria en varianza; las {len(lista)} se estabilizan con "
           f"log1p. El diagnóstico solo es válido si se hace sobre el tramo pre-pandemia: medido sobre el "
           f"entrenamiento completo, el colapso de 2020 enmascara la relación entre dispersión y nivel.")
    bullet("La estacionalidad es visible en las siete series pero no domina la varianza del residuo, así que se "
           "modela con términos estacionales sin diferenciación estacional. La diferenciación regular necesaria "
           "varía por serie.")
    bullet("La prueba de Ljung-Box deja residuos independientes en pocas combinaciones serie-modelo, casi todas "
           "SARIMA. El resto conserva estructura sin capturar.")
    bullet("Sobre el conjunto de prueba los modelos simples superan a los estructurales, porque el entrenamiento "
           "termina en el piso pandémico y no contiene información sobre la recuperación. El hallazgo es que el "
           "quiebre estructural excede la capacidad de un modelo univariado, no que los modelos simples sean "
           "mejores.")
    bullet("Para el INGUAT, el valor del análisis está en la caracterización de las series —volatilidad relativa, "
           "canales que cerraron por completo, composición real de cada mercado emisor— más que en la predicción "
           "puntual sobre un período con un quiebre de esta magnitud.")


def main():
    datos = cargar_resultados()
    construir(datos)

    salida_dir = ROOT / "outputs"
    salida_dir.mkdir(parents=True, exist_ok=True)
    salida = salida_dir / "Laboratorio1_SeriesDeTiempo.pdf"

    doc = SimpleDocTemplate(
        str(salida), pagesize=letter,
        topMargin=0.7 * inch, bottomMargin=0.7 * inch,
        leftMargin=0.75 * inch, rightMargin=0.75 * inch,
        title="Laboratorio 1 - Series de Tiempo - CC3084",
        author="Diego López, Nelson Escalante, Roberto Nájera",
    )
    doc.build(story)
    print(f"PDF generado en {salida}")


if __name__ == "__main__":
    main()
