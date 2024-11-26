import yfinance as yf

def get_apple_news():
    """
    Récupère les actualités récentes concernant l'action Apple (AAPL) via l'API Yahoo Finance.

    Retourne:
        list: Une liste contenant les actualités relatives à Apple, où chaque élément est un dictionnaire
              avec des informations telles que le titre, le lien, la source et la date de publication.

    Raises:
        RuntimeError: Si aucune actualité n'est trouvée ou en cas d'erreur lors de la récupération.
    """
    try:
        # Initialisation de l'objet Ticker pour le symbole Apple (AAPL)
        stock = yf.Ticker("AAPL")
        
        # Récupération des données d'actualités liées à l'action
        news_data = stock.news
        
        # Vérification que des données ont été récupérées
        if not news_data or len(news_data) == 0:
            raise ValueError("Aucune actualité disponible pour l'action AAPL.")
        
        return news_data
    except Exception as e:
        # Gestion des erreurs, renvoie une exception détaillée
        raise RuntimeError(f"Erreur lors de la récupération des actualités pour AAPL : {str(e)}")
