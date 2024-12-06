import yfinance as yf

def get_stock_data(stock_symbol, period="3mo", interval="1d"):
    """
    Récupère les données historiques d'un symbole boursier spécifique pour une période et un intervalle donnés.

    Paramètres:
        stock_symbol (str): Le symbole boursier (exemple : 'AAPL' pour Apple).
        period (str): La période pour laquelle les données doivent être récupérées 
                      (valeurs possibles : '1d', '5d', '1mo', '3mo', '6mo', '1y', '5y', 'max').
                      Par défaut : '3mo'.
        interval (str): L'intervalle de temps entre chaque point de donnée 
                        (valeurs possibles : '1m', '2m', '5m', '15m', '1d', '1wk', '1mo').
                        Par défaut : '1d'.

    Retourne:
        list: Une liste des prix de clôture pour la période et l'intervalle spécifiés.
    """
    try:
        # Initialisation de l'objet Ticker pour le symbole boursier donné
        stock = yf.Ticker(stock_symbol)
        
        # Récupération des données historiques pour la période et l'intervalle spécifiés
        historical_data = stock.history(period=period, interval=interval)
        
        # Vérifie si des données ont été récupérées
        if historical_data.empty:
            raise ValueError(f"Aucune donnée disponible pour le symbole '{stock_symbol}' avec la période '{period}' et l'intervalle '{interval}'.")
        
        # Extraction des prix de clôture dans une liste
        prices = historical_data['Close'].tolist()
        
        return prices
    except Exception as e:
        # Gestion des erreurs, renvoie un message détaillé
        raise RuntimeError(f"Erreur lors de la récupération des données pour '{stock_symbol}': {str(e)}")
