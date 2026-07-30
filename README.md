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
python main.py lstm        # redes LSTM con tuneo de épocas
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
| `src/lstm.py` | redes LSTM y tuneo de épocas |
| `src/plots.py` | gráficos |
| `src/pipeline.py` | orquesta el análisis completo |

# Laboratorio 2

## 1.4 ¿Cuál predijo mejor? ¿Son mejores que los modelos del laboratorio anterior? ¿Cómo lo determinaron?

**Criterio y método de comparación.** Se usó RMSE sobre el mismo conjunto de prueba (63 observaciones out-of-sample) y el mismo split train/test del laboratorio anterior, con MAE como respaldo — mismo criterio (`"criterio_ganador": "rmse"`) ya fijado en `comparison.json`, para que la comparación con `seasonal_naive`, `simple_exponential`, `holt_winters`, `sarima` y `prophet` sea directa y no haya que redefinir la metodología a mitad de camino.

### Serie 1 — Total mensual de viajeros internacionales

| Modelo | RMSE | MAE |
|---|---:|---:|
| **LSTM c1** (ventana=12, 1 capa) | **95,563.77** | **76,028.45** |
| LSTM c2 (ventana=24, 2 capas) | 183,475.14 | 163,123.36 |
| Simple exponential | 194,790.81 | 175,088.44 |
| Holt-Winters | 216,457.60 | 196,956.51 |
| Seasonal naive | 253,203.39 | 235,730.91 |
| SARIMA | 257,978.56 | 238,984.23 |
| Prophet | 284,418.84 | 266,995.04 |

`lstm_c1` gana con margen amplio: **50.9% menos RMSE y 56.6% menos MAE** que el mejor modelo clásico (simple exponential). Los dos LSTM superan a los cinco modelos del laboratorio anterior en esta serie.

### Serie 2 — Vía de ingreso: Aérea

| Modelo | RMSE | MAE |
|---|---:|---:|
| LSTM c1 (ventana=12, 1 capa) | 1,988,252.06 | 1,836,336.63 |
| Prophet | 92,230.74 | 89,016.95 |
| Seasonal naive | 79,077.33 | 75,103.70 |
| SARIMA | 73,149.56 | 68,719.95 |
| Holt-Winters | 52,231.09 | 48,043.42 |
| Simple exponential | 41,367.77 | 36,108.53 |
| **LSTM c2** (ventana=24, 2 capas) | **23,574.25** | **17,691.40** |

Aquí el resultado se invierte: `lstm_c2` es el mejor modelo de toda la comparación (**43.0% menos RMSE y 51.0% menos MAE** que simple exponential), pero `lstm_c1` es el **peor**, por lejos — su RMSE es ~21.6 veces el de Prophet (el peor modelo clásico) y ~84 veces el de su propio compañero `lstm_c2`.

**Por qué falla `lstm_c1` en Aérea.** El diagnóstico de aplanamiento (`aplanamiento` en `lstm.json`/`comparison.json`) muestra que, en la predicción recursiva a 63 pasos, el modelo converge a un valor casi constante hacia el final del horizonte (`cv_cola` cercano a cero). Esto es un modo de falla conocido de LSTM en pronóstico recursivo de horizonte largo: sin suficiente memoria de contexto (ventana=12, la más chica de las dos configuraciones, con solo 1 capa y dropout=0.1), el error se retroalimenta en cada paso y la serie generada colapsa a un punto fijo en vez de seguir la tendencia/estacionalidad real. `lstm_c2` (ventana=24, 2 capas, dropout=0.3) también se marca como `aplanado: true`, pero con una varianza de cola mucho mayor — retiene bastante más movimiento y no se aleja tanto del comportamiento real. Esto es consistente con que Aérea es la vía más volátil de las tres (`cv = 0.33` en `comparison.json`, contra una serie "total" mucho más suave por ser la suma de las tres vías): una configuración que colapsa a un valor fijo penaliza mucho más en una serie con oscilaciones marcadas que en una ya de por sí más estable.

### ¿Son mejores que los modelos del laboratorio anterior?

- **En la serie total: sí, sin matices.** Ambas configuraciones LSTM superan a los cinco modelos clásicos; la mejor de las dos (`lstm_c1`) reduce el error a la mitad frente al mejor modelo del laboratorio pasado.
- **En Aérea: depende del config, no de la familia de modelo.** `lstm_c2` es el mejor modelo de la serie, pero `lstm_c1` es el peor de los siete. "LSTM" no es automáticamente superior a lo clásico — la arquitectura y el tamaño de ventana importan tanto como la elección del algoritmo, sobre todo en pronóstico recursivo a 63 meses sobre una serie volátil.

### Cómo se determinó

Comparando RMSE y MAE de los 7 modelos (5 clásicos + 2 LSTM) sobre el mismo conjunto de prueba de 63 observaciones para cada serie, usando los valores ya calculados en `comparison.json` (que integra los resultados del laboratorio anterior con los LSTM de este laboratorio bajo el mismo criterio de selección). El respaldo con MAE (que se mueve en la misma dirección que RMSE en ambas series) descarta que la conclusión dependa de la métrica elegida.
