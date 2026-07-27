# Laboratorio 1 — Series de Tiempo

CC3084 Data Science · Universidad del Valle de Guatemala · Semestre II 2026

Análisis del ingreso de viajeros internacionales a Guatemala (enero 2009 – junio 2026)
a partir de `Base_Migracion_2009-2026jun.xlsx`.

> Los datos son de uso exclusivamente académico. No corresponden a cifras oficiales
> del INGUAT ni del Instituto Guatemalteco de Migración.

## Instalación

```bash
pip install -r requirements.txt
```

## Uso

```bash
python main.py all       # pipeline completo: figuras + results/*.json
python main.py eda       # solo exploratorio (6 figuras + eda.json)
python main.py series    # partición 70/30 + las 7 series (14 figuras)
python main.py report    # arma el PDF a partir de results/*.json
```

La primera corrida tarda ~45 s porque lee el Excel; después usa un cache en
`.cache/` y baja a menos de un segundo. Con `--no-cache` se fuerza la lectura
del Excel.

## Estructura

```
src/config.py        rutas y constantes
src/data.py          carga del Excel + cache
src/series.py        partición temporal y construcción de las series
src/eda.py           métricas del exploratorio
src/stationarity.py  pruebas de estacionariedad (ADF)
src/plots.py         figuras (único módulo que usa matplotlib)
src/pipeline.py      orquestación; escribe results/*.json
report/build.py      arma el PDF leyendo results/*.json
main.py              CLI
```

`results/*.json` es la única fuente de verdad de los números del informe: el
pipeline los calcula y `report/build.py` solo los lee. Ningún número del PDF se
escribe a mano.

## Series construidas

Serie obligatoria (total mensual) más dos categorías de análisis, sobre el
conjunto de entrenamiento (2009-01 a 2021-03, 147 meses):

- **Vías de ingreso:** Aérea, Terrestre, Marítima
- **Países de residencia** (top 3 por acumulado de todo el período): El Salvador,
  Guatemala, Estados Unidos de América

## Notas metodológicas

- La partición es **cronológica** (70 % / 30 % de los meses), no aleatoria: el
  conjunto de prueba es posterior en el tiempo al de entrenamiento.
- Las series se reindexan contra el rango fijo de meses de entrenamiento, así los
  meses sin ningún registro quedan en 0 en vez de recortar la serie. Importa para
  la vía Marítima, que tiene 12 meses consecutivos en cero por el cierre de
  fronteras.
- El dataset combina tres tramos con metodologías distintas. Para comparar en
  todo el rango se usa Turista + Excursionista, según indica el enunciado.
