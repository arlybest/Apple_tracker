import yfinance as yf
import logging

def get_financial_metrics(stock_symbol):
    """
    Récupère les métriques financières clés pour un symbole boursier spécifique.

    Paramètres:
        stock_symbol (str): Le symbole boursier (exemple : 'AAPL' pour Apple).

    Retourne:
        dict: Un dictionnaire contenant les métriques financières du jour précédent.

    Raises:
        RuntimeError: En cas d'erreur lors de la récupération des données.
    """
    try:
        # Initialisation de l'objet Ticker
        stock = yf.Ticker(stock_symbol)

        # Récupération des informations de base
        info = stock.info

        # Extraction des métriques financières importantes
        metrics = {
            "pe_ratio": info.get("trailingPE"),
            "dividend_yield": info.get("dividendYield"),
            "beta": info.get("beta"),
            "market_cap": info.get("marketCap"),
        }

        # Log des métriques actuelles
        logging.info(f"Métriques actuelles pour {stock_symbol} : {metrics}")

        # Récupérer les données historiques pour les 5 derniers jours
        historical_data = stock.history(period="5d")  # Getting data for the last 5 days

        # Log des données historiques
        logging.info(f"Données historiques pour {stock_symbol} :\n{historical_data}")

        # Vérification que les données historiques contiennent au moins 2 jours
        if len(historical_data) >= 2:
            # Check if the most recent data is for today or the previous day
            previous_day_data = historical_data.iloc[-2]  # Get the data for the previous day

            # Extraction des métriques du jour précédent
            previous_day_metrics = {
                "pe_ratio": info.get("trailingPE"),
                "dividend_yield": info.get("dividendYield"),
                "beta": info.get("beta"),
                "market_cap": info.get("marketCap"),
                "date": previous_day_data.name.strftime("%Y-%m-%d"),
            }

            # Log des métriques du jour précédent
            logging.info(f"Métriques du jour précédent pour {stock_symbol} : {previous_day_metrics}")
        else:
            # Si les données historiques sont insuffisantes
            logging.warning(f"Pas assez de données historiques pour {stock_symbol}.")
            previous_day_metrics = {}

        return previous_day_metrics

    except Exception as e:
        # Log des erreurs
        logging.error(f"Erreur lors de la récupération des métriques financières pour {stock_symbol} : {str(e)}")
        raise RuntimeError(f"Erreur lors de la récupération des métriques financières pour {stock_symbol} : {str(e)}")
