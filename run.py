import logging
from app import create_app

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

# Point d'entrée principal
if __name__ == '__main__':
    app.run(debug=True)
