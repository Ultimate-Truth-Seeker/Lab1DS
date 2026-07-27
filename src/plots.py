"""
Generacion de figuras. Es el unico modulo que toca matplotlib.

Regla: aca no se produce ningun numero que el informe cite. La descomposicion
estacional vive aca porque sus tres componentes solo existen para dibujarse:
ninguna metrica derivada de ellas entra al reporte. Si algun dia se cita la
fuerza de la estacionalidad, la descomposicion se muda a series.py.
"""

import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
import matplotlib.ticker as mticker
import numpy as np
import pandas as pd
from statsmodels.graphics.tsaplots import plot_acf
from statsmodels.tsa.seasonal import seasonal_decompose

from src import config

plt.rcParams["figure.dpi"] = config.DPI
plt.rcParams["font.size"] = config.FONT_SIZE


def _miles(x, _):
    return f"{x/1000:.0f}k"


def _guardar(fig, ruta):
    config.FIGDIR.mkdir(parents=True, exist_ok=True)
    fig.tight_layout()
    fig.savefig(ruta)
    plt.close(fig)


def temporal_total(serie_mensual: pd.Series, ruta):
    """Serie total de todo el periodo, con pandemia y quiebre metodologico."""
    fig, ax = plt.subplots(figsize=(9, 4))
    ax.plot(serie_mensual.index, serie_mensual.values, color=config.TEAL, linewidth=1.2)
    ax.set_title("Total mensual de viajeros internacionales a Guatemala (2009-2026)")
    ax.set_ylabel("Viajeros")
    ax.axvspan(pd.Timestamp(config.PANDEMIA_INICIO), pd.Timestamp(config.PANDEMIA_FIN),
               color="red", alpha=0.08, label="Pandemia")
    ax.axvline(pd.Timestamp(config.QUIEBRE_METODOLOGICO), color="orange", linestyle="--",
               linewidth=1, label="Quiebre metodológico 2023")
    ax.yaxis.set_major_formatter(mticker.FuncFormatter(_miles))
    ax.legend()
    _guardar(fig, ruta)


def temporal_comparable(serie_mensual: pd.Series, ruta):
    """Turista + Excursionista: la unica combinacion comparable en todo el rango."""
    fig, ax = plt.subplots(figsize=(9, 4))
    ax.plot(serie_mensual.index, serie_mensual.values, color=config.AZUL, linewidth=1.2)
    ax.set_title("Turista + Excursionista mensual (serie comparable 2009-2026)")
    ax.set_ylabel("Viajeros")
    ax.axvspan(pd.Timestamp(config.PANDEMIA_INICIO), pd.Timestamp(config.PANDEMIA_FIN),
               color="red", alpha=0.08, label="Pandemia")
    ax.yaxis.set_major_formatter(mticker.FuncFormatter(_miles))
    ax.legend()
    _guardar(fig, ruta)


def top_paises(acumulado: pd.Series, ruta):
    fig, ax = plt.subplots(figsize=(8, 5))
    acumulado.head(15).sort_values().plot(kind="barh", ax=ax, color=config.TEAL)
    ax.set_title("Top 15 países/agrupaciones por viajeros acumulados (2009-2026)")
    ax.set_xlabel("Viajeros acumulados")
    _guardar(fig, ruta)


def top_regiones(acumulado: pd.Series, ruta):
    fig, ax = plt.subplots(figsize=(8, 4.5))
    acumulado.sort_values().plot(kind="barh", ax=ax, color=config.NARANJA_OSCURO)
    ax.set_title("Viajeros acumulados por región (Región dos), 2009-2026")
    ax.set_xlabel("Viajeros acumulados")
    _guardar(fig, ruta)


def vias_fronteras(via_tot: pd.Series, frontera_tot: pd.Series, ruta):
    fig, axes = plt.subplots(1, 2, figsize=(11, 4.5))
    via_tot.sort_values().plot(kind="barh", ax=axes[0], color=config.AZUL_MEDIO)
    axes[0].set_title("Viajeros acumulados por vía de ingreso")
    frontera_tot.head(10).sort_values().plot(kind="barh", ax=axes[1], color=config.VERDE)
    axes[1].set_title("Top 10 fronteras por viajeros acumulados")
    _guardar(fig, ruta)


def distribuciones(viajero: pd.Series, tipo_tot: pd.Series, ruta):
    """Histograma en log1p (la variable es de conteo, muy sesgada) + total por tipo."""
    fig, axes = plt.subplots(1, 2, figsize=(11, 4))
    np.log1p(viajero).plot(kind="hist", bins=50, ax=axes[0], color=config.MORADO)
    axes[0].set_title("Distribución de 'Viajero' por registro (log1p)")
    axes[0].set_xlabel("log(1 + viajeros por registro)")

    tipo_tot.plot(kind="bar", ax=axes[1], color=config.DURAZNO)
    axes[1].set_title("Viajeros acumulados por tipo de viajero")
    axes[1].tick_params(axis="x", rotation=30)
    _guardar(fig, ruta)


def panel_serie(s: pd.Series, nombre: str, ruta, period: int = config.PERIOD):
    """
    Serie + tendencia + estacionalidad + residuo.

    Si la descomposicion falla, el panel queda con el primer subplot dibujado y
    los otros tres vacios: preferimos una figura degradada a perder la corrida.
    """
    fig, axes = plt.subplots(4, 1, figsize=(9, 9), sharex=True)
    axes[0].plot(s.index, s.values, color=config.TEAL)
    axes[0].set_title(f"{nombre} — serie mensual (train)")

    # se descompone la serie tal cual. Antes se hacia replace(0, nan).interpolate(),
    # que inventaba datos justo en los meses que de verdad valen 0 -- por ejemplo
    # los 12 meses seguidos de la via Maritima con las fronteras cerradas, que es
    # el evento mas interesante de esa serie.
    try:
        dec = seasonal_decompose(s, model="additive", period=period)
        axes[1].plot(dec.trend, color=config.NARANJA_OSCURO)
        axes[1].set_title("Tendencia")
        axes[2].plot(dec.seasonal, color=config.AZUL_MEDIO)
        axes[2].set_title("Estacionalidad")
        axes[3].plot(dec.resid, color=config.VERDE, marker="o", markersize=2, linestyle="None")
        axes[3].set_title("Residuo")
    except Exception as e:
        print("No se pudo descomponer:", e)

    _guardar(fig, ruta)


def acf_serie(s: pd.Series, nombre: str, ruta, lags: int = config.LAGS_ACF):
    fig, ax = plt.subplots(figsize=(6, 3.2))
    plot_acf(s, lags=lags, ax=ax)
    ax.set_title(f"ACF — {nombre}")
    _guardar(fig, ruta)
