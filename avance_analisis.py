"""
Laboratorio 1 - Series de Tiempo (CC3084 Data Science)
Avance: Análisis Exploratorio + Análisis preliminar de series de tiempo

Fuente: Base_Migracion_2009-2026jun.xlsx (INGUAT / IGM, uso académico)
"""

import pandas as pd
import numpy as np
import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
import matplotlib.ticker as mticker
from statsmodels.tsa.seasonal import seasonal_decompose
from statsmodels.tsa.stattools import adfuller
from statsmodels.graphics.tsaplots import plot_acf

plt.rcParams["figure.dpi"] = 110
plt.rcParams["font.size"] = 9

FIGDIR = "figs"
DATA_PATH = "Base_Migracion_2009-2026jun.xlsx"

# ---------------------------------------------------------------------------
# 1. CARGA DE DATOS
# ---------------------------------------------------------------------------
df = pd.read_excel(DATA_PATH, sheet_name="Datos")
df["Fecha"] = pd.to_datetime(dict(year=df["Año"], month=df["Mes cod"], day=1))

print("Dimensiones:", df.shape)
print(df.dtypes)

# ---------------------------------------------------------------------------
# 1.e CALIDAD DE DATOS: faltantes, duplicados, atípicos
# ---------------------------------------------------------------------------
print("\n--- Valores faltantes por columna ---")
print(df.isnull().sum())

print("\n--- Filas duplicadas (todas las columnas) ---")
print(df.duplicated().sum())

print("\n--- Registros por año (revela quiebres de granularidad) ---")
print(df.groupby("Año").size())

print("\n--- Estadísticos descriptivos de 'Viajero' ---")
print(df["Viajero"].describe())

print("\n--- Valores en cero ---", (df["Viajero"] == 0).sum())
print("--- Valores negativos ---", (df["Viajero"] < 0).sum())

# Outliers a nivel fila con IQR (referencial, la variable es de conteo muy sesgada)
q1, q3 = df["Viajero"].quantile([0.25, 0.75])
iqr = q3 - q1
upper = q3 + 1.5 * iqr
print(f"\nUmbral superior IQR: {upper:.1f} | filas por encima: {(df['Viajero'] > upper).sum()} "
      f"({(df['Viajero'] > upper).mean()*100:.1f}%)")

# ---------------------------------------------------------------------------
# 1.a COMPORTAMIENTO TEMPORAL (todo el período, para contexto exploratorio)
# ---------------------------------------------------------------------------
mensual_total = df.groupby("Fecha")["Viajero"].sum().sort_index()

fig, ax = plt.subplots(figsize=(9, 4))
ax.plot(mensual_total.index, mensual_total.values, color="#0b6e6e", linewidth=1.2)
ax.set_title("Total mensual de viajeros internacionales a Guatemala (2009-2026)")
ax.set_ylabel("Viajeros")
ax.axvspan(pd.Timestamp("2020-03-01"), pd.Timestamp("2021-12-01"), color="red", alpha=0.08, label="Pandemia")
ax.axvline(pd.Timestamp("2023-01-01"), color="orange", linestyle="--", linewidth=1, label="Quiebre metodológico 2023")
ax.yaxis.set_major_formatter(mticker.FuncFormatter(lambda x, _: f"{x/1000:.0f}k"))
ax.legend()
fig.tight_layout()
fig.savefig(f"{FIGDIR}/01_temporal_total.png")
plt.close(fig)

# Serie comparable turista+excursionista (recomendada por el enunciado)
tur_exc = df[df["Tipo de Viajero"].isin(["Turista", "Excursionista"])]
mensual_comparable = tur_exc.groupby("Fecha")["Viajero"].sum().sort_index()

fig, ax = plt.subplots(figsize=(9, 4))
ax.plot(mensual_comparable.index, mensual_comparable.values, color="#1f77b4", linewidth=1.2)
ax.set_title("Turista + Excursionista mensual (serie comparable 2009-2026)")
ax.set_ylabel("Viajeros")
ax.axvspan(pd.Timestamp("2020-03-01"), pd.Timestamp("2021-12-01"), color="red", alpha=0.08, label="Pandemia")
ax.yaxis.set_major_formatter(mticker.FuncFormatter(lambda x, _: f"{x/1000:.0f}k"))
ax.legend()
fig.tight_layout()
fig.savefig(f"{FIGDIR}/02_temporal_comparable.png")
plt.close(fig)

# ---------------------------------------------------------------------------
# 1.b PAÍSES CON MAYOR CANTIDAD DE VIAJEROS (acumulado histórico)
# ---------------------------------------------------------------------------
top_paises = df.groupby("País")["Viajero"].sum().sort_values(ascending=False)
print("\n--- Top 10 países (acumulado 2009-2026) ---")
print(top_paises.head(10))

fig, ax = plt.subplots(figsize=(8, 5))
top_paises.head(15).sort_values().plot(kind="barh", ax=ax, color="#0b6e6e")
ax.set_title("Top 15 países/agrupaciones por viajeros acumulados (2009-2026)")
ax.set_xlabel("Viajeros acumulados")
fig.tight_layout()
fig.savefig(f"{FIGDIR}/03_top_paises.png")
plt.close(fig)

# ---------------------------------------------------------------------------
# 1.c REGIONES CON MAYOR CANTIDAD DE VIAJEROS
# ---------------------------------------------------------------------------
top_regiones = df.groupby("Región dos")["Viajero"].sum().sort_values(ascending=False)
print("\n--- Regiones (Región dos) acumulado ---")
print(top_regiones)

fig, ax = plt.subplots(figsize=(8, 4.5))
top_regiones.sort_values().plot(kind="barh", ax=ax, color="#c1440e")
ax.set_title("Viajeros acumulados por región (Región dos), 2009-2026")
ax.set_xlabel("Viajeros acumulados")
fig.tight_layout()
fig.savefig(f"{FIGDIR}/04_top_regiones.png")
plt.close(fig)

# ---------------------------------------------------------------------------
# 1.d VÍAS DE INGRESO Y FRONTERAS
# ---------------------------------------------------------------------------
via_tot = df.groupby("Vía")["Viajero"].sum().sort_values(ascending=False)
frontera_tot = df.groupby("Frontera")["Viajero"].sum().sort_values(ascending=False)
print("\n--- Vías de ingreso (acumulado) ---")
print(via_tot)
print("\n--- Top 10 fronteras (acumulado) ---")
print(frontera_tot.head(10))

fig, axes = plt.subplots(1, 2, figsize=(11, 4.5))
via_tot.sort_values().plot(kind="barh", ax=axes[0], color="#4c72b0")
axes[0].set_title("Viajeros acumulados por vía de ingreso")
frontera_tot.head(10).sort_values().plot(kind="barh", ax=axes[1], color="#55a868")
axes[1].set_title("Top 10 fronteras por viajeros acumulados")
fig.tight_layout()
fig.savefig(f"{FIGDIR}/05_vias_fronteras.png")
plt.close(fig)

# ---------------------------------------------------------------------------
# 1.f DISTRIBUCIONES ADICIONALES
# ---------------------------------------------------------------------------
fig, axes = plt.subplots(1, 2, figsize=(11, 4))
np.log1p(df["Viajero"]).plot(kind="hist", bins=50, ax=axes[0], color="#8172b2")
axes[0].set_title("Distribución de 'Viajero' por registro (log1p)")
axes[0].set_xlabel("log(1 + viajeros por registro)")

tipo_tot = df.groupby("Tipo de Viajero")["Viajero"].sum().sort_values(ascending=False)
tipo_tot.plot(kind="bar", ax=axes[1], color="#dd8452")
axes[1].set_title("Viajeros acumulados por tipo de viajero")
axes[1].tick_params(axis="x", rotation=30)
fig.tight_layout()
fig.savefig(f"{FIGDIR}/06_distribuciones.png")
plt.close(fig)

print("\n--- Viajeros acumulados por tipo de viajero ---")
print(tipo_tot)

# ---------------------------------------------------------------------------
# 2. DIVISIÓN ENTRENAMIENTO (70%) / PRUEBA (30%), CRONOLÓGICA
# ---------------------------------------------------------------------------
meses = pd.date_range(df["Fecha"].min(), df["Fecha"].max(), freq="MS")
n_train = int(len(meses) * 0.7)
corte = meses[n_train - 1]          # último mes de entrenamiento
inicio_test = meses[n_train]        # primer mes de prueba

print(f"\nTotal de meses: {len(meses)} | Entrenamiento: {n_train} meses "
      f"({meses[0]:%Y-%m} a {corte:%Y-%m}) | Prueba: {len(meses)-n_train} meses "
      f"({inicio_test:%Y-%m} a {meses[-1]:%Y-%m})")

train = df[df["Fecha"] <= corte].copy()
test = df[df["Fecha"] > corte].copy()
print("Filas train:", len(train), " | Filas test:", len(test))
print(f"Proporción train: {len(train)/len(df)*100:.1f}%  |  test: {len(test)/len(df)*100:.1f}%")

# ---------------------------------------------------------------------------
# 3. CONSTRUCCIÓN DE SERIES MENSUALES (a partir de TRAIN)
# ---------------------------------------------------------------------------
# IMPORTANTE: se reindexa contra el rango FIJO de meses de entrenamiento
# (no contra el propio min/max de cada subserie), porque algunas categorías
# (p.ej. vía Marítima) tienen meses sin NINGÚN registro -- ausencia real de
# datos (cierre de fronteras en pandemia), que debe verse como 0, no recortarse.
train_months = meses[:n_train]

serie_total = train.groupby("Fecha")["Viajero"].sum().reindex(train_months, fill_value=0)
serie_total.index.name = "Fecha"

# Categoría 1: Vías de ingreso
series_via = {}
for via in ["Aérea", "Terrestre", "Marítima"]:
    s = train[train["Vía"] == via].groupby("Fecha")["Viajero"].sum().reindex(train_months, fill_value=0)
    series_via[via] = s

# Categoría 2: Top-3 países (criterio: acumulado TOTAL del período completo, no solo train)
top3_paises = top_paises.head(3).index.tolist()
print("\nTop 3 países (criterio: todo el período):", top3_paises)
series_pais = {}
for pais in top3_paises:
    s = train[train["País"] == pais].groupby("Fecha")["Viajero"].sum().reindex(train_months, fill_value=0)
    series_pais[pais] = s

# ---------------------------------------------------------------------------
# 4. ANÁLISIS PRELIMINAR DE SERIES (inicio/fin/frecuencia, gráfico, descomposición)
# ---------------------------------------------------------------------------
def analizar_serie(s, nombre, archivo, periodo=12):
    print(f"\n=== {nombre} ===")
    print(f"Inicio: {s.index.min():%Y-%m} | Fin: {s.index.max():%Y-%m} | "
          f"Frecuencia: Mensual (MS) | N obs: {len(s)}")
    print(s.describe())

    fig, axes = plt.subplots(4, 1, figsize=(9, 9), sharex=True)
    axes[0].plot(s.index, s.values, color="#0b6e6e")
    axes[0].set_title(f"{nombre} — serie mensual (train)")

    try:
        dec = seasonal_decompose(s.replace(0, np.nan).interpolate(), model="additive", period=periodo)
        axes[1].plot(dec.trend, color="#c1440e"); axes[1].set_title("Tendencia")
        axes[2].plot(dec.seasonal, color="#4c72b0"); axes[2].set_title("Estacionalidad")
        axes[3].plot(dec.resid, color="#55a868", marker="o", markersize=2, linestyle="None")
        axes[3].set_title("Residuo")
    except Exception as e:
        print("No se pudo descomponer:", e)

    fig.tight_layout()
    fig.savefig(f"{FIGDIR}/{archivo}")
    plt.close(fig)

    # ACF + prueba ADF preliminar (media)
    fig2, ax2 = plt.subplots(figsize=(6, 3.2))
    plot_acf(s, lags=36, ax=ax2)
    ax2.set_title(f"ACF — {nombre}")
    fig2.tight_layout()
    fig2.savefig(f"{FIGDIR}/{archivo.replace('.png', '_acf.png')}")
    plt.close(fig2)

    adf_stat, adf_p, *_ = adfuller(s.dropna())
    print(f"ADF estadístico: {adf_stat:.3f} | p-valor: {adf_p:.4f} -> "
          f"{'estacionaria en media (rechaza H0)' if adf_p < 0.05 else 'NO estacionaria en media (no rechaza H0)'}")

    return s

analizar_serie(serie_total, "Total mensual de viajeros internacionales", "10_serie_total.png")
for via, s in series_via.items():
    analizar_serie(s, f"Vía de ingreso: {via}", f"11_serie_via_{via}.png")
for pais, s in series_pais.items():
    safe = pais.replace(" ", "_")
    analizar_serie(s, f"País de residencia: {pais}", f"12_serie_pais_{safe}.png")

print("\nListo. Figuras guardadas en", FIGDIR)