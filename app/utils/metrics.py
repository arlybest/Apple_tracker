import yfinance as yf

def get_financial_metrics(stock_symbol):
    """
    Récupère les métriques financières clés pour un symbole boursier spécifique.

    Paramètres:
        stock_symbol (str): Le symbole boursier (exemple : 'AAPL' pour Apple).

    Retourne:
        dict: Un dictionnaire contenant des informations telles que le ratio P/E, la capitalisation boursière, etc.

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
        
        return metrics
    except Exception as e:
        raise RuntimeError(f"Erreur lors de la récupération des métriques financières pour {stock_symbol} : {str(e)}")
