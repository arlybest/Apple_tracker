import yfinance as yf
from datetime import datetime, timedelta

def get_stock_data(stock_symbol, period="5y", interval="1d", start_date=None, end_date=None):
    """
    Récupère les données historiques d'un symbole boursier pour la période spécifiée.
    Si start_date et end_date sont fournis, ils seront utilisés pour récupérer les données spécifiques.

    Paramètres:
        stock_symbol (str): Le symbole boursier (exemple : 'AAPL').
        period (str): La période pour laquelle les données doivent être récupérées (ex. : '1d', '5y').
        interval (str): L'intervalle de temps entre chaque point de donnée (ex. : '1d', '1mo').
        start_date (str): La date de début (format : 'YYYY-MM-DD') si spécifique.
        end_date (str): La date de fin (format : 'YYYY-MM-DD') si spécifique.

    Retourne:
        dict: Données boursières pour la période donnée.
    """
    try:
        stock = yf.Ticker(stock_symbol)

        # Si start_date et end_date sont fournis, on les utilise, sinon on se base sur 'period'
        if start_date and end_date:
            historical_data = stock.history(start=start_date, end=end_date, interval=interval)
        else:
            historical_data = stock.history(period=period, interval=interval)

        if historical_data.empty:
            raise ValueError(f"Aucune donnée disponible pour {stock_symbol}.")

        # Extraction des prix de clôture
        return {
            "recent_prices": historical_data['Close'].tolist(),
        }

    except Exception as e:
        raise RuntimeError(f"Erreur lors de la récupération des données pour {stock_symbol}: {str(e)}")
