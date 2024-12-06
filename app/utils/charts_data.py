import numpy as np

def prepare_chart_data(dates, actual_prices, predicted_prices):
    """
    Prépare les données pour les graphiques.

    Paramètres:
        dates (list): Liste des dates.
        actual_prices (list): Liste des prix réels.
        predicted_prices (list): Liste des prix prévus.

    Retourne:
        dict: Données formatées pour un graphique.
    """
    return {
        "labels": dates,
        "actual": actual_prices,
        "predicted": predicted_prices
    }
