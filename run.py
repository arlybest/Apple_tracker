import logging
from app import create_app
from datetime import datetime

# Configuration du logging
logging.basicConfig(
    level=logging.INFO,  # Niveau d'information (DEBUG pour encore plus de détails)
    format="%(asctime)s - %(levelname)s - %(message)s",
    handlers=[
        logging.StreamHandler()  # Log dans la console
    ]
)

# Création de l'application Flask
app = create_app()

# Définir le filtre pour formater les timestamps
def datetimeformat(value):
    """
    Formate un timestamp UNIX en une chaîne de date lisible.
    """
    return datetime.utcfromtimestamp(value).strftime('%Y-%m-%d %H:%M:%S')

# Enregistrer le filtre dans l'environnement Jinja
app.jinja_env.filters['datetimeformat'] = datetimeformat
# Point d'entrée principal
if __name__ == '__main__':
    app.run(debug=True)
