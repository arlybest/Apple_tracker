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

# ========================= HELPER FUNCTION =========================

def format_prices_with_month(prices_data, year=None, start_date="2024-01-01"):
    # Initialize a defaultdict to store prices by month
    month_prices = defaultdict(list)

    # Check if prices_data contains dictionaries with dates
    if all(isinstance(price, dict) for price in prices_data):
        # Group the prices by month
        for price in prices_data:
            date_str = price.get('date')  # Ensure 'date' exists
            price_value = price.get('price')  # Ensure 'price' exists
            if date_str and price_value:
                # Extract month and year from the date string
                date = datetime.strptime(date_str, "%Y-%m-%d")
                if not year or date.year == int(year):  # Only include prices for the given year
                    month_prices[date.month].append(price_value)
            else:
                logging.error(f"Format inattendu pour le prix : {price}")
    elif all(isinstance(price, (int, float)) for price in prices_data):
        logging.warning("Prices data does not contain dates, generating artificial dates.")
        # Generate artificial dates starting from the specified start_date
        current_date = datetime.strptime(start_date, "%Y-%m-%d")
        for price in prices_data:
            # Group prices by the month of the artificial date
            month_prices[current_date.month].append(price)
            # Increment the date by 1 day
            current_date += timedelta(days=1)
    else:
        logging.error("Format des données de prix non reconnu.")
        return []

    # Generate the formatted data
    formatted_data = []
    for month in range(1, 13):  # Loop through months 1 to 12
        if month_prices[month]:
            month_price = month_prices[month][-1]  # Choose the last price of the month
            month_name = datetime(year=int(year), month=month, day=1).strftime('%B')
            formatted_data.append({
                "année": year,
                "date": f"{year}-{str(month).zfill(2)}-01",  # Use the first day of the month
                "mois": month_name,
                "prix": month_price
            })

    return formatted_data


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


@main.route('/stock-data', methods=['GET'])
def stock_data():
    """
    Récupère les données historiques pour AAPL, y compris les prix des années précédentes (2021, 2022, 2023),
    de l'année actuelle jusqu'à aujourd'hui, et les prix du jour actuel.
    """
    try:
        stock_symbol = "AAPL"
        
        # Date ranges for previous years (2021, 2022, 2023)
        previous_years = [
            {"start_date": "2021-01-01", "end_date": "2021-12-31"},
            {"start_date": "2022-01-01", "end_date": "2022-12-31"},
            {"start_date": "2023-01-01", "end_date": "2023-12-31"},
        ]
        
        # Get prices for each previous year (2021, 2022, 2023)
        previous_year_prices = {}
        for year in previous_years:
            try:
                data = get_stock_data(stock_symbol, start_date=year["start_date"], end_date=year["end_date"], interval="1d")
                # Ensure the data is in the expected format
                if isinstance(data, dict) and "recent_prices" in data:
                    year_label = year["start_date"][:4]  # Extract the year (e.g., "2021")
                    previous_year_prices[year_label] = format_prices_with_month(data["recent_prices"], year=year_label)
                else:
                    raise ValueError(f"Data format unexpected for year {year['start_date'][:4]}")
            except Exception as e:
                logging.error(f"Erreur lors de la récupération des données pour {stock_symbol} pour l'année {year['start_date'][:4]}: {e}")
                previous_year_prices[year["start_date"][:4]] = []  # Fallback to an empty list

        # Get prices for the current year (2024) from Jan 1, 2024 to today
        current_year_start = "2024-01-01"
        current_year_end = datetime.now().strftime('%Y-%m-%d')
        try:
            current_year_prices_data = get_stock_data(stock_symbol, start_date=current_year_start, end_date=current_year_end, interval="1d")
            # Handle the response correctly based on its format
            if isinstance(current_year_prices_data, dict) and "recent_prices" in current_year_prices_data:
                current_year_prices = format_prices_with_month(current_year_prices_data["recent_prices"], year="2024")
            else:
                raise ValueError("Unexpected data format for current year prices.")
        except Exception as e:
            logging.error(f"Erreur lors de la récupération des données pour l'année actuelle {current_year_start}: {e}")
            current_year_prices_data = {"recent_prices": []}

        # Get the price for today (using 'period' as '1d')
        try:
            today_price_data = get_stock_data(stock_symbol, period="1d", interval="1d")
            today_price = today_price_data["recent_prices"][-1] if isinstance(today_price_data, dict) and "recent_prices" in today_price_data else None
        except Exception as e:
            logging.error(f"Erreur lors de la récupération du prix pour aujourd'hui: {e}")
            today_price = None
        
        return jsonify({
            "stock_symbol": stock_symbol,
            "2021_prices": previous_year_prices.get("2021", []),
            "2022_prices": previous_year_prices.get("2022", []),
            "2023_prices": previous_year_prices.get("2023", []),
            "2024_prices": current_year_prices,
            "today_price": {
                "date": datetime.now().strftime('%Y-%m-%d'),
                "price": today_price
            }
        }), 200
    except Exception as e:
        logging.error(f"Erreur dans stock_data: {e}")
        return jsonify({"error": "Impossible de récupérer les données boursières"}), 500
