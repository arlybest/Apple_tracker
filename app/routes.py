from flask import Flask, Blueprint, jsonify, render_template, Response, request
from flask_limiter import Limiter
from flask_limiter.util import get_remote_address
from app.utils.scraper import get_stock_data
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
from collections import defaultdict
from datetime import datetime, timedelta

# ========================= CONFIGURATION =========================

# Configuration du système de logs pour capturer les erreurs
logging.basicConfig(level=logging.ERROR)

# Initialisation de l'application Flask et du middleware de limitation de débit (rate limiting)
app = Flask(__name__)
limiter = Limiter(get_remote_address, app=app)
main = Blueprint("main", __name__)

# Chargement des variables d'environnement depuis un fichier .env
load_dotenv()

# Lecture des variables sensibles pour l'envoi d'e-mails
SMTP_SERVER = os.getenv("SMTP_SERVER")
SMTP_PORT = os.getenv("SMTP_PORT")
SMTP_EMAIL = os.getenv("SMTP_EMAIL")
SMTP_PASSWORD = os.getenv("SMTP_PASSWORD")

# Vérification de la présence des variables d'environnement obligatoires
required_env_vars = {"SMTP_SERVER", "SMTP_PORT", "SMTP_EMAIL", "SMTP_PASSWORD"}
missing_vars = [var for var in required_env_vars if not os.getenv(var)]
if missing_vars:
    raise ValueError(f"Les variables d'environnement suivantes sont manquantes : {', '.join(missing_vars)}")

# ========================= FONCTIONS UTILES =========================

def format_prices_with_month(prices_data, year=None, start_date="2024-01-01"):
    """
    Formate les données des prix en regroupant les prix par mois.
    Si aucune date n'est spécifiée, génère des dates artificielles en commençant par `start_date`.

    Paramètres :
        prices_data (list): Liste des prix avec ou sans dates associées.
        year (str, optionnel): Année pour laquelle les données doivent être traitées.
        start_date (str, optionnel): Date de début pour générer des dates artificielles.

    Retourne :
        list : Données formatées avec mois, année, date et dernier prix du mois.
    """
    month_prices = defaultdict(list)  # Dictionnaire pour regrouper les prix par mois

    # Vérifie si les données contiennent des dates associées aux prix
    if all(isinstance(price, dict) for price in prices_data):
        for price in prices_data:
            date_str = price.get('date')
            price_value = price.get('price')
            if date_str and price_value:
                date = datetime.strptime(date_str, "%Y-%m-%d")
                if not year or date.year == int(year):
                    month_prices[date.month].append(price_value)
            else:
                logging.error(f"Format inattendu pour les données de prix : {price}")
    elif all(isinstance(price, (int, float)) for price in prices_data):
        logging.warning("Données sans date détectées, création de dates artificielles.")
        current_date = datetime.strptime(start_date, "%Y-%m-%d")
        for price in prices_data:
            month_prices[current_date.month].append(price)
            current_date += timedelta(days=1)
    else:
        logging.error("Format des données de prix non reconnu.")
        return []

    # Génère les données formatées en choisissant le dernier prix pour chaque mois
    formatted_data = []
    for month in range(1, 13):
        if month_prices[month]:
            month_price = month_prices[month][-1]
            month_name = datetime(year=int(year), month=month, day=1).strftime('%B')
            formatted_data.append({
                "année": year,
                "date": f"{year}-{str(month).zfill(2)}-01",
                "mois": month_name,
                "prix": month_price
            })

    return formatted_data

# ========================= ROUTES =========================

@main.route('/financial-metrics/<string:stock_symbol>', methods=['GET'])
def financial_metrics(stock_symbol):
    """
    Récupère les métriques financières d'un symbole boursier.

    Paramètres :
        stock_symbol (str): Le symbole boursier (ex. : 'AAPL').

    Retourne :
        JSON : Contient les métriques financières ou un message d'erreur.
    """
    try:
        metrics = get_financial_metrics(stock_symbol)
        return jsonify({"stock_symbol": stock_symbol, "metrics": metrics}), 200
    except RuntimeError as e:
        logging.error(f"Erreur lors de la récupération des métriques pour {stock_symbol} : {e}")
        return jsonify({"error": str(e)}), 500


class Alert(BaseModel):
    """
    Modèle de données pour gérer les alertes via Pydantic.
    """
    email: str
    price: float


def send_email_alert(email: str, price: float):
    """
    Envoie une alerte e-mail lorsqu'un seuil de prix est atteint.

    Paramètres :
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
        logging.error(f"Échec de l'envoi de l'e-mail à {email} : {e}")


@main.route('/set-alert/', methods=['POST'])
@validate()
@limiter.limit("10 per minute")
def set_alert(alert: Alert):
    """
    Configure une alerte pour un prix spécifique.

    Paramètres :
        alert (Alert): Données de l'alerte contenant l'e-mail et le prix.

    Retourne :
        JSON : Confirmation de la configuration de l'alerte.
    """
    send_email_alert(alert.email, alert.price)
    return jsonify({"message": "Alerte configurée avec succès !"}), 200


@main.route('/')
def home():
    """
    Affiche la page d'accueil avec des métriques pour l'action AAPL.
    """
    stock_symbol = "AAPL"
    try:
        previous_day_metrics = get_financial_metrics(stock_symbol)
        return render_template('index.html', stock_symbol=stock_symbol, 
                               previous_day_metrics=previous_day_metrics or {}, 
                               error=None)
    except Exception as e:
        logging.error(f"Erreur lors de la récupération des métriques pour {stock_symbol} : {e}")
        return render_template('index.html', stock_symbol=stock_symbol, 
                               previous_day_metrics={}, 
                               error="Impossible de récupérer les métriques.")


@main.route('/stock-data', methods=['GET'])
def stock_data():
    """
    Récupère les données historiques pour AAPL (2021-2024) et le prix du jour.

    Retourne :
        JSON : Données des prix historiques et prix du jour actuel.
    """
    try:
        stock_symbol = "AAPL"
        previous_years = [
            {"start_date": "2021-01-01", "end_date": "2021-12-31"},
            {"start_date": "2022-01-01", "end_date": "2022-12-31"},
            {"start_date": "2023-01-01", "end_date": "2023-12-31"},
        ]
        
        # Collecte des prix pour les années précédentes
        previous_year_prices = {}
        for year in previous_years:
            try:
                data = get_stock_data(stock_symbol, start_date=year["start_date"], end_date=year["end_date"], interval="1d")
                if isinstance(data, dict) and "recent_prices" in data:
                    year_label = year["start_date"][:4]
                    previous_year_prices[year_label] = format_prices_with_month(data["recent_prices"], year=year_label)
                else:
                    raise ValueError(f"Format inattendu pour {year['start_date'][:4]}")
            except Exception as e:
                logging.error(f"Erreur pour {year['start_date'][:4]} : {e}")
                previous_year_prices[year["start_date"][:4]] = []

        # Collecte des prix pour l'année actuelle
        current_year_start = "2024-01-01"
        current_year_end = datetime.now().strftime('%Y-%m-%d')
        current_year_prices = format_prices_with_month(
            get_stock_data(stock_symbol, start_date=current_year_start, end_date=current_year_end)["recent_prices"], year="2024"
        )

        # Prix du jour actuel
        today_price = get_stock_data(stock_symbol, period="1d", interval="1d")["recent_prices"][-1]

        return jsonify({
            "stock_symbol": stock_symbol,
            "2021_prices": previous_year_prices.get("2021", []),
            "2022_prices": previous_year_prices.get("2022", []),
            "2023_prices": previous_year_prices.get("2023", []),
            "2024_prices": current_year_prices,
            "today_price": today_price
        }), 200
    except Exception as e:
        logging.error(f"Erreur lors de la récupération des données boursières : {e}")
        return jsonify({"error": str(e)}), 500


@main.route('/prediction', methods=['GET', 'POST'])
def prediction():
    if request.method == "GET":
        # Render the prediction page
        return render_template("prediction.html")
    
    elif request.method == "POST":
        # Perform your prediction logic
        prediction = predict_lstm()  # This is your function to generate predictions

        # Structure the prediction result
        response_data = {
            "dates": prediction["dates"],  # e.g., ["2024-12-14", "2024-12-15", ...]
            "predictions": prediction["predictions"],  # e.g., [248.85, 250.44, ...]
        }
        return jsonify(response_data)  # Return the prediction as JSON





