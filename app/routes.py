from flask import Flask, Blueprint, jsonify, render_template, Response, request
from flask_limiter import Limiter
from flask_limiter.util import get_remote_address
from app.utils.scraper import get_stock_data as scraper_stock_data
from app.models.lstm import predict_lstm
from pydantic import BaseModel
from app.utils.metrics import get_financial_metrics
from flask_pydantic import validate
import yfinance as yf
import smtplib
from email.mime.text import MIMEText
from dotenv import load_dotenv
import os
import logging

# Configuration du logging pour capturer les erreurs
logging.basicConfig(level=logging.ERROR)

# Initialisation de l'application Flask et du rate limiter
app = Flask(__name__)
limiter = Limiter(get_remote_address, app=app)
main = Blueprint("main", __name__)

# Chargement des variables d'environnement
load_dotenv()

# Chargement des variables sensibles
SMTP_SERVER = os.getenv("SMTP_SERVER")
SMTP_PORT = os.getenv("SMTP_PORT")
SMTP_EMAIL = os.getenv("SMTP_EMAIL")
SMTP_PASSWORD = os.getenv("SMTP_PASSWORD")

# Vérification des variables d'environnement essentielles
required_env_vars = {"SMTP_SERVER", "SMTP_PORT", "SMTP_EMAIL", "SMTP_PASSWORD"}
missing_vars = [var for var in required_env_vars if not os.getenv(var)]
if missing_vars:
    raise ValueError(f"Les variables d'environnement suivantes sont manquantes : {', '.join(missing_vars)}")


# ========================= ROUTES =========================

# Route pour récupérer les métriques financières d'une action spécifique
@main.route('/financial-metrics/<string:stock_symbol>', methods=['GET'])
def financial_metrics(stock_symbol):
    """
    Récupère les métriques financières d'un symbole boursier.

    Paramètres:
        stock_symbol (str): Le symbole boursier (ex. : 'AAPL').

    Retourne:
        JSON contenant les métriques financières.
    """
    try:
        metrics = get_financial_metrics(stock_symbol)
        return jsonify({"stock_symbol": stock_symbol, "metrics": metrics}), 200
    except RuntimeError as e:
        logging.error(f"Erreur lors de la récupération des métriques pour {stock_symbol}: {e}")
        return jsonify({"error": str(e)}), 500


# Classe Pydantic pour gérer les alertes
class Alert(BaseModel):
    email: str
    price: float


# Fonction pour envoyer une alerte par e-mail
def send_email_alert(email: str, price: float):
    """
    Envoie une alerte e-mail lorsque le prix de l'action atteint un seuil.

    Paramètres:
        email (str): Adresse e-mail du destinataire.
        price (float): Prix déclencheur de l'alerte.
    """
    try:
        msg = MIMEText(f"Le prix de l'action Apple a atteint votre seuil : ${price}")
        msg['Subject'] = 'Alerte de prix !'
        msg['From'] = SMTP_EMAIL
        msg['To'] = email

        with smtplib.SMTP(SMTP_SERVER, int(SMTP_PORT)) as server:
            server.starttls()
            server.login(SMTP_EMAIL, SMTP_PASSWORD)
            server.sendmail(SMTP_EMAIL, email, msg.as_string())
    except Exception as e:
        logging.error(f"Échec de l'envoi de l'e-mail à {email}: {e}")


# Route pour définir une alerte sur le prix d'une action
@main.route('/set-alert/', methods=['POST'])
@validate()
@limiter.limit("10 per minute")
def set_alert(alert: Alert):
    """
    Définit une alerte de prix pour l'action AAPL.

    Paramètres:
        alert (Alert): Contient l'e-mail et le prix seuil.

    Retourne:
        JSON confirmant la configuration de l'alerte.
    """
    send_email_alert(alert.email, alert.price)
    return jsonify({"message": "Alerte configurée avec succès !"}), 200


@main.route('/')
def home():
    """
    Affiche la page d'accueil de l'application.
    """
    stock_symbol = "AAPL"  # This can be dynamic if needed
    try:
        # Fetch the previous day's metrics
        previous_day_metrics = get_financial_metrics(stock_symbol)

        # Ensure previous_day_metrics are available or fallback to an empty dict
        return render_template('index.html', stock_symbol=stock_symbol, 
                               previous_day_metrics=previous_day_metrics or {}, 
                               error=None)
    except Exception as e:
        logging.error(f"Erreur lors de la récupération des métriques pour {stock_symbol}: {e}")
        # Return the error message to the template
        return render_template('index.html', stock_symbol=stock_symbol, 
                               previous_day_metrics={}, 
                               error="Impossible de récupérer les métriques.")





# Route pour récupérer les données historiques d'une action
@main.route('/stock-data', methods=['GET'])
def stock_data():
    """
    Récupère les données historiques pour AAPL.

    Retourne:
        JSON contenant les prix historiques.
    """
    try:
        stock_symbol = "AAPL"
        prices = scraper_stock_data(stock_symbol)
        return jsonify({"stock_symbol": stock_symbol, "prices": prices}), 200
    except Exception as e:
        logging.error(f"Erreur dans stock_data: {e}")
        return jsonify({"error": "Impossible de récupérer les données boursières"}), 500


# Route pour récupérer les données de plusieurs entreprises
@main.route('/multi-stock-data', methods=['GET'])
def multi_stock_data():
    """
    Récupère les données de clôture des actions de plusieurs entreprises.

    Retourne:
        JSON contenant les prix les plus récents.
    """
    try:
        stock_symbols = ["AAPL", "MSFT", "GOOGL", "AMZN", "TSLA", "META", "NVDA"]
        stock_data = {}

        for symbol in stock_symbols:
            stock = yf.Ticker(symbol)
            historical_data = stock.history(period="1d")['Close']
            if not historical_data.empty:
                stock_data[symbol] = {
                    "latest_close": round(historical_data.iloc[-1], 2),
                    "name": stock.info.get("longName", "N/A")
                }
            else:
                stock_data[symbol] = {"error": "Aucune donnée disponible"}

        return jsonify(stock_data), 200
    except Exception as e:
        logging.error(f"Erreur dans multi_stock_data: {e}")
        return jsonify({"error": "Impossible de récupérer les données boursières"}), 500


# Enregistrement du blueprint et lancement de l'application
app.register_blueprint(main)

if __name__ == "__main__":
    app.run(debug=True)
