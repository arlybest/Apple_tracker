from flask import Flask, Blueprint, jsonify, render_template, Response, request
from flask_limiter import Limiter
from flask_limiter.util import get_remote_address
from app.utils.scraper import get_stock_data as scraper_stock_data  # Évite les conflits de nom
from app.models.lstm import predict_lstm  # Modèle de prédiction LSTM
from pydantic import BaseModel
from app.utils.metrics import get_financial_metrics  # Fonction pour récupérer les métriques financières
from flask_pydantic import validate
import yfinance as yf
import pandas as pd
import smtplib
from email.mime.text import MIMEText
import os
import logging

# Configuration du logging pour capturer les erreurs
logging.basicConfig(level=logging.ERROR)

# Initialisation de l'application Flask et du rate limiter
app = Flask(__name__)
limiter = Limiter(get_remote_address, app=app)
main = Blueprint("main", __name__)

# Chargement des variables sensibles à partir des variables d'environnement
SMTP_SERVER = os.getenv("SMTP_SERVER")
SMTP_PORT = os.getenv("SMTP_PORT")
SMTP_EMAIL = os.getenv("SMTP_EMAIL")
SMTP_PASSWORD = os.getenv("SMTP_PASSWORD")

# Vérification des variables d'environnement essentielles
for var_name, var_value in {
    "SMTP_SERVER": SMTP_SERVER,
    "SMTP_PORT": SMTP_PORT,
    "SMTP_EMAIL": SMTP_EMAIL,
    "SMTP_PASSWORD": SMTP_PASSWORD,
}.items():
    if not var_value:
        raise ValueError(f"Variable d'environnement manquante : {var_name}")

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
    email: str  # Adresse e-mail du destinataire
    price: float  # Prix seuil de l'alerte

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

        # Connexion au serveur SMTP
        with smtplib.SMTP(SMTP_SERVER, int(SMTP_PORT)) as server:
            server.starttls()
            server.login(SMTP_EMAIL, SMTP_PASSWORD)
            server.sendmail(SMTP_EMAIL, email, msg.as_string())
    except Exception as e:
        logging.error(f"Échec de l'envoi de l'e-mail à {email}: {e}")

# Route pour définir une alerte sur le prix d'une action
@main.route('/set-alert/', methods=['POST'])
@validate()
@limiter.limit("10 per minute")  # Limite : 10 requêtes par minute
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

# Route pour afficher la page d'accueil
@main.route('/')
def home():
    """
    Affiche la page d'accueil de l'application.
    """
    return render_template('index.html')

# Route pour récupérer les données historiques d'une action
@main.route('/stock-data', methods=['GET'])
def stock_data():
    """
    Récupère les données historiques du symbole AAPL.

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

    Entreprises suivies :
        - Apple (AAPL)
        - Microsoft (MSFT)
        - Google (GOOGL)
        - Amazon (AMZN)
        - Tesla (TSLA)
        - Meta (META)
        - Nvidia (NVDA)

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
                    "latest_close": historical_data.iloc[-1],
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
