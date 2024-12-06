import tensorflow as tf
import numpy as np
import pandas as pd
from sklearn.preprocessing import MinMaxScaler
from app.utils.scraper import get_stock_data
from datetime import datetime, timedelta

def get_next_prediction_dates(num_days=5):
    """
    Génère une liste des prochaines dates pour lesquelles les prédictions sont effectuées.

    Paramètres:
        num_days (int): Nombre de jours à prédire (par défaut 5).
    
    Retourne:
        list: Liste des dates (format 'YYYY-MM-DD') correspondant aux prochaines prédictions.
    """
    return [(datetime.now() + timedelta(days=i)).strftime('%Y-%m-%d') for i in range(1, num_days + 1)]

def predict_lstm():
    """
    Prédit les prix futurs d'une action (AAPL dans cet exemple) pour les 5 prochains jours
    en utilisant un modèle LSTM.

    Retourne:
        dict: Un dictionnaire contenant les dates de prédiction et les prix prédits.
    """
    # Étape 1 : Récupération des données boursières
    data = get_stock_data("AAPL")
    if len(data) < 10:
        raise ValueError("Pas assez de données pour entraîner le modèle. Veuillez vérifier les données.")

    # Étape 2 : Normalisation des données avec MinMaxScaler
    scaler = MinMaxScaler(feature_range=(0, 1))
    data = scaler.fit_transform(np.array(data).reshape(-1, 1))

    # Étape 3 : Préparation des données pour l'entrée du modèle LSTM
    X_train = []
    y_train = []
    for i in range(5, len(data)):
        X_train.append(data[i-5:i, 0])  # 5 jours précédents
        y_train.append(data[i, 0])     # Prix du jour actuel
    
    X_train = np.array(X_train)
    y_train = np.array(y_train)
    X_train = np.reshape(X_train, (X_train.shape[0], X_train.shape[1], 1))  # Reshape pour LSTM

    # Étape 4 : Construction du modèle LSTM
    model = tf.keras.Sequential([
        tf.keras.layers.LSTM(50, return_sequences=True, input_shape=(X_train.shape[1], 1)),
        tf.keras.layers.LSTM(50),
        tf.keras.layers.Dense(1)
    ])
    model.compile(optimizer="adam", loss="mean_squared_error")

    # Étape 5 : Entraînement du modèle
    model.fit(X_train, y_train, epochs=50, batch_size=32, verbose=1)

    # Étape 6 : Préparation des données pour la prédiction
    last_5_days = data[-5:].reshape(1, 5, 1)  # Les 5 derniers jours pour prédire le futur
    predictions = []

    # Génération des prédictions pour les 5 prochains jours
    for _ in range(5):
        prediction = model.predict(last_5_days, verbose=0)
        predictions.append(prediction[0, 0])
        # Met à jour les 5 derniers jours avec la nouvelle prédiction
        last_5_days = np.append(last_5_days[:, 1:, :], [[[prediction[0, 0]]]], axis=1)

    # Étape 7 : Transformation inverse pour obtenir les prix réels
    predicted_prices = scaler.inverse_transform(np.array(predictions).reshape(-1, 1)).flatten()

    # Étape 8 : Génération des dates correspondantes
    prediction_dates = get_next_prediction_dates()

    # Étape 9 : Retour des résultats sous forme de dictionnaire
    return {
        "predictions": predicted_prices.tolist(),
        "dates": prediction_dates
    }
