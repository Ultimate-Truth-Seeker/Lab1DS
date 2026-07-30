"""
Modelo LSTM profundo (PyTorch)

Este módulo únicamente ajusta modelos y devuelve sus resultados.
No escribe archivos.
No genera figuras.
No conoce el pipeline.
"""

from __future__ import annotations

import numpy as np
import pandas as pd

import torch
import torch.nn as nn
import torch.optim as optim

from sklearn.preprocessing import MinMaxScaler

from src import config

def _resultado(
    modelo: str,
    parametros: dict,
    forecast: pd.Series,
    history=None,
    ajuste=None,
):
    return {
        "modelo": modelo,
        "parametros": parametros,
        "forecast": forecast,
        "history": history,
        "fit": ajuste,
    }


def _pronostico_index(
    serie: pd.Series,
    horizon: int,
):

    inicio = serie.index[-1] + pd.offsets.MonthBegin()

    return pd.date_range(
        start=inicio,
        periods=horizon,
        freq=config.FREQ,
    )

def preparar_datos(
    serie,
    ventana=24,
):
    """
    Convierte la serie de entrenamiento
    en ventanas para el LSTM.
    """

    scaler = MinMaxScaler()

    valores = scaler.fit_transform(
        serie.values.reshape(-1, 1)
    )

    X = []
    y = []

    for i in range(ventana, len(valores)):

        X.append(
            valores[i-ventana:i]
        )

        y.append(
            valores[i]
        )

    X = np.array(
        X,
        dtype=np.float32,
    ).reshape(-1, ventana, 1)

    y = np.array(
        y,
        dtype=np.float32,
    ).reshape(-1, 1)

    return X, y, scaler

class DeepLSTM(nn.Module):

    def __init__(self):

        super().__init__()

        self.lstm1 = nn.LSTM(
            1,
            64,
            batch_first=True,
        )

        self.drop1 = nn.Dropout(0.5)

        self.lstm2 = nn.LSTM(
            64,
            32,
            batch_first=True,
        )

        self.drop2 = nn.Dropout(0.5)

        self.fc = nn.Linear(
            32,
            1,
        )

    def forward(self, x):

        x, _ = self.lstm1(x)

        x = self.drop1(x)

        x, _ = self.lstm2(x)

        x = self.drop2(x)

        x = x[:, -1, :]

        return self.fc(x)

def entrenar(
    model,
    X,
    y,
    epochs=100,
    lr=1e-3,
):

    device = torch.device(
        "cuda"
        if torch.cuda.is_available()
        else "cpu"
    )

    model.to(device)

    X = torch.tensor(X).to(device)
    y = torch.tensor(y).to(device)

    optimizer = optim.Adam(
        model.parameters(),
        lr=lr,
    )

    criterion = nn.MSELoss()

    history = []

    model.train()

    for _ in range(epochs):

        optimizer.zero_grad()

        pred = model(X)

        loss = criterion(pred, y)

        loss.backward()

        optimizer.step()

        history.append(loss.item())

    return history

# ---------------------------------------------------------------------
# Deep LSTM
# ---------------------------------------------------------------------

def deep_lstm(
    serie: pd.Series,
    horizon: int,
    ventana: int = 24,
    epochs: int = 100,
):

    X, y, scaler = preparar_datos(
        serie,
        ventana,
    )

    model = DeepLSTM()

    history = entrenar(
        model,
        X,
        y,
        epochs=epochs,
    )

    device = torch.device(
        "cuda"
        if torch.cuda.is_available()
        else "cpu"
    )

    model.eval()

    ventana_actual = (
        scaler.transform(
            serie.values.reshape(-1, 1)
        )[-ventana:]
    )

    ventana_actual = ventana_actual.reshape(
        1,
        ventana,
        1,
    )

    predicciones = []

    with torch.no_grad():

        for _ in range(horizon):

            entrada = torch.tensor(
                ventana_actual,
                dtype=torch.float32,
            ).to(device)

            salida = model(entrada)

            valor = (
                salida
                .cpu()
                .numpy()
                .flatten()[0]
            )

            predicciones.append(valor)

            ventana_actual = np.concatenate(
                [
                    ventana_actual[:, 1:, :],
                    [[[valor]]],
                ],
                axis=1,
            )

    predicciones = scaler.inverse_transform(
        np.array(predicciones).reshape(-1, 1)
    ).flatten()

    forecast = pd.Series(
        predicciones,
        index=_pronostico_index(
            serie,
            horizon,
        ),
        name="forecast",
    )

    return _resultado(
        modelo="deep_lstm",
        parametros={
            "window": ventana,
            "layers": 2,
            "hidden": [64, 32],
            "dropout": 0.5,
            "epochs": epochs,
        },
        forecast=forecast,
        history=history,
        ajuste=model,
    )

# ---------------------------------------------------------------------
# Ejecutar modelos
# ---------------------------------------------------------------------
def ajustar_todos(
    serie: pd.Series,
    horizon: int,
):

    resultados = {}

    resultados["deep_lstm"] = deep_lstm(
        serie,
        horizon,
    )

    return resultados