# Laboratorio 1 — Series de Tiempo

CC3084 Data Science · Universidad del Valle de Guatemala · Semestre II 2026
Sección 20 · Diego López, Nelson Escalante, Roberto Nájera

Ingreso de viajeros internacionales a Guatemala (2009 – junio 2026), a partir
de `Base_Migracion_2009-2026jun.xlsx`.

## Entregables

- **Informe:** `outputs/Laboratorio1_SeriesDeTiempo.pdf`
- **Código:** `main.py` + `src/`
- **Resultados:** `results/*.json`, `figs/*.png`

## Instalación y uso

```bash
pip install -r requirements.txt

python main.py all         # pipeline completo
python main.py eda         # análisis exploratorio
python main.py series      # series, componentes y estacionariedad
python main.py modelos     # ARIMA, Holt-Winters, exponencial, naive, Prophet
python main.py prediccion  # conjunto de prueba, MAE/RMSE, comparativo
```

## Series analizadas

Serie obligatoria (total mensual) más dos categorías:

- **Vías de ingreso:** Aérea, Terrestre, Marítima
- **Países de residencia** (top 3 por acumulado histórico): El Salvador,
  Guatemala, Estados Unidos de América

## Código

| Archivo | Contiene |
|---|---|
| `src/data.py` | carga y limpieza del dataset |
| `src/eda.py` | análisis exploratorio |
| `src/series.py` | partición entrenamiento/prueba y construcción de series |
| `src/decomposition.py` | tendencia y estacionalidad |
| `src/transform.py` | estacionariedad en varianza |
| `src/stationarity.py` | estacionariedad en media (ADF, KPSS, diferenciación) |
| `src/models.py` | ARIMA, Holt-Winters, suavizamiento exponencial, naive, Prophet |
| `src/evaluation.py` | AIC, BIC, Ljung-Box, MAE, RMSE |
| `src/comparison.py` | comparación entre series y hallazgos |
| `src/plots.py` | gráficos |
| `src/pipeline.py` | orquesta el análisis completo |
