from flask import Flask, Blueprint, jsonify, render_template, redirect, url_for, request, session
from flask_limiter import Limiter
from flask_limiter.util import get_remote_address
from app.utils.scraper import get_stock_data
from app.models.lstm import predict_lstm
from pydantic import BaseModel
from app.utils.metrics import get_financial_metrics
from flask_pydantic import validate
import yfinance as yf
import pyrebase
import smtplib
from email.mime.text import MIMEText
from dotenv import load_dotenv
import os
import logging
from collections import defaultdict
from datetime import datetime, timedelta
from firebase_admin import auth
import yfinance as yf

import yfinance as yf
from datetime import datetime
import logging

import yfinance as yf
from datetime import datetime
import logging

import pandas as pd

def get_historical_data(stock_symbol="AAPL", start_date="2020-01-01", end_date=None):
    """
    Fetch historical stock data (dates and actual prices) for a given stock symbol.
    Args:
        stock_symbol (str): The stock ticker symbol (e.g., 'AAPL').
        start_date (str): The start date for the data in the format 'YYYY-MM-DD'.
        end_date (str): The end date for the data in the format 'YYYY-MM-DD'. Defaults to today if not provided.

    Returns:
        dict: A dictionary containing 'dates' and 'actualPrices'.
    """
    try:
        # Default to today's date if end_date is not provided
        if end_date is None:
            end_date = datetime.now().strftime('%Y-%m-%d')
        
        # Fetch historical data using Yahoo Finance
        data = yf.download(stock_symbol, start=start_date, end=end_date, progress=False)

        # Log the raw data for debugging
        logging.debug(f"Données récupérées pour {stock_symbol} :\n{data.head()}")

        # Vérifiez si les données sont vides
        if data.empty:
            logging.error(f"Aucune donnée disponible pour {stock_symbol} entre {start_date} et {end_date}.")
            return {
                "dates": [],
                "actualPrices": []
            }

        # Aplatir les colonnes si elles sont multi-indexées
        if isinstance(data.columns, pd.MultiIndex):
            data.columns = [' '.join(col).strip() for col in data.columns]
            logging.debug(f"Colonnes après aplatissement : {data.columns}")

        # Vérifiez si la colonne 'Close' existe
        if 'Close' not in data.columns:
            logging.error(f"La colonne 'Close' est introuvable dans les données pour {stock_symbol}.")
            return {
                "dates": [],
                "actualPrices": []
            }

        # Extract dates and closing prices
        dates = list(data.index.strftime('%Y-%m-%d'))  # Format index and convert to a list
        actual_prices = data['Close'].tolist()  # Convert 'Close' column to a list
        
        return {
            "dates": dates,
            "actualPrices": actual_prices
        }
    except Exception as e:
        logging.error(f"Erreur lors de la récupération des données historiques : {e}")
        return {
            "dates": [],
            "actualPrices": []
        }

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

firebaseConfig = {
    "apiKey": os.getenv("FIREBASE_API_KEY"),
    "authDomain": "apple-stock-prediction.firebaseapp.com",
    "projectId": "apple-stock-prediction",
    "storageBucket": "apple-stock-prediction.appspot.com",
    "messagingSenderId": "830704283155",
    "appId": "1:830704283155:web:b399f596fe2201374859e6",
    "measurementId": "G-Z5QKF0PJNV",
    "databaseURL": "https://apple-stock-prediction-default-rtdb.firebaseio.com/"
}

firebase = pyrebase.initialize_app(firebaseConfig)
auth = firebase.auth()


# Vérification de la présence des variables d'environnement obligatoires
required_env_vars = {"SMTP_SERVER", "SMTP_PORT", "SMTP_EMAIL", "SMTP_PASSWORD", "FIREBASE_API_KEY"}
missing_vars = [var for var in required_env_vars if not os.getenv(var)]
if missing_vars:
    raise ValueError(f"Les variables d'environnement suivantes sont manquantes : {', '.join(missing_vars)}")
# ========================= FONCTIONS UTILES =========================

# Fonction pour créer un utilisateur
def create_user_and_update(email, password):
    try:
        # Créer l'utilisateur
        user = auth.create_user(
            email=email,
            password=password
        )
        user_id = user.uid

        # Définir le displayName (par exemple, l'email sans le domaine)
        display_name = email.split('@')[0]  # Utiliser la partie avant le '@' de l'email

        print(f"Compte créé pour l'e-mail {email} avec displayName {display_name}")
        return user
    except Exception as e:
        print(f"Erreur lors de la création ou mise à jour du compte : {e}")
        return None
# Décorateur pour enregistrer le filtre `datetimeformat` sur l'application Flask
# Enregistrement d'un filtre Jinja pour formater les timestamps
def datetimeformat(value):
    """
    Formate un timestamp UNIX en chaîne de date lisible.
    """
    return datetime.utcfromtimestamp(value).strftime('%Y-%m-%d %H:%M:%S')

# Enregistrement du filtre `datetimeformat` dans l'application Flask
app.jinja_env.filters['datetimeformat'] = datetimeformat
def format_prices_with_month(prices_data, year=None, start_date="2024-01-01"):
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
    send_email_alert(alert.email, alert.price)
    return jsonify({"message": "Alerte configurée avec succès !"}), 200


def send_password_reset_email(email):
    """Envoie un e-mail pour réinitialiser le mot de passe."""
    try:
        auth.send_password_reset_email(email)
        logging.info(f"Un e-mail de réinitialisation de mot de passe a été envoyé à {email}")
    except Exception as e:
        logging.error(f"Erreur lors de l'envoi de l'e-mail de réinitialisation : {e}")


# ========================= ROUTES =========================

@main.route('/register', methods=['GET', 'POST'])
def register():
    """Route pour la création de compte."""
    if request.method == 'POST':
        email = request.form.get('email')
        password = request.form.get('password')
        try:
            # Création de l'utilisateur
            user = auth.create_user_with_email_and_password(email, password)
            user_id = user['localId']

            # Définir le displayName (par exemple, l'email sans le domaine)
            display_name = email.split('@')[0]  # Utiliser la partie avant le '@' de l'email

            # Stocker le displayName dans la session pour l'utiliser plus tard
            session['user'] = display_name

            logging.info(f"Compte créé pour l'e-mail {email} avec displayName {display_name}")

            # Afficher un message de succès à l'utilisateur et rediriger après 2 secondes
            return render_template('create_account_success.html', success="Compte créé avec succès. Vous allez être redirigé vers la page de connexion.")

        except Exception as e:
            logging.error(f"Erreur lors de la création du compte : {e}")

            # Vérifier si l'erreur est liée à un e-mail déjà existant
            if "EMAIL_EXISTS" in str(e):
                return render_template('create_account.html', error="Un compte avec cet e-mail existe déjà.")
            else:
                return render_template('create_account.html', error="Erreur lors de la création du compte. Veuillez réessayer.")

    return render_template('create_account.html')


@main.route('/login', methods=['GET', 'POST'])
def login():
    """Route pour la connexion."""
    if request.method == 'POST':
        email = request.form.get('email')
        password = request.form.get('password')
        try:
            # Connexion de l'utilisateur
            user = auth.sign_in_with_email_and_password(email, password)
            user_id_token = user['idToken']

            # Récupérer les informations de l'utilisateur
            user_info = auth.get_account_info(user_id_token)
            user_name = user_info['users'][0].get('displayName', email.split('@')[0])  # Utiliser l'email si displayName est absent

            # Stocker le nom dans la session
            session['user'] = user_name
            session['idToken'] = user_id_token  # Stocker aussi l'idToken pour les futures requêtes

            logging.info(f"Utilisateur connecté : {user_name}")
            return redirect(url_for('main.home'))

        except Exception as e:
            logging.error(f"Erreur lors de la connexion : {e}")
            
            # Vérifier les erreurs spécifiques de connexion
            if "EMAIL_NOT_FOUND" in str(e):
                return render_template('login.html', error="Aucun compte trouvé avec cet email.")
            elif "INVALID_PASSWORD" in str(e):
                return render_template('login.html', error="Le mot de passe est incorrect.")
            else:
                return render_template('login.html', error="Erreur lors de la connexion. Veuillez vérifier vos identifiants.")
    
    return render_template('login.html')

@main.route('/logout')
def logout():
    """Route pour la déconnexion."""
    session.clear()  
    session.pop('user', None)
    logging.info("Utilisateur déconnecté.")
    return redirect(url_for('main.login'))


@main.route('/forgot_password', methods=['GET', 'POST'])
def forgot_password():
    """Route pour réinitialiser le mot de passe."""
    if request.method == 'POST':
        email = request.form.get('email')
        try:
            send_password_reset_email(email)
            return render_template('forgot_password.html', success="E-mail de réinitialisation envoyé.")
        except Exception as e:
            logging.error(f"Erreur lors de la réinitialisation du mot de passe : {e}")
            return render_template('forgot_password.html', error="Erreur lors de l'envoi de l'e-mail.")
    return render_template('forgot_password.html')

@main.route('/reset-password', methods=['GET', 'POST'])
def reset_password():
    if request.method == 'POST':
        email = request.form.get('email')
        try:
            auth.send_password_reset_email(email)
            return render_template('reset_password.html', success="Un e-mail de réinitialisation a été envoyé à votre adresse e-mail.")
        except Exception as e:
            logging.error(f"Erreur lors de la réinitialisation du mot de passe : {e}")
            return render_template('reset_password.html', error="Erreur lors de la réinitialisation du mot de passe.")
    return render_template('reset_password.html')

@main.route('/')
def home():
    """Page d'accueil après connexion."""
    if 'user' not in session:
        # Récupérez l'idToken depuis la session
        user_id_token = session.get('idToken')
        if not user_id_token:
            return redirect(url_for('main.login'))  # Redirigez si l'utilisateur n'est pas connecté

        try:
            # Appelez Firebase pour obtenir les informations utilisateur
            user_info = auth.get_account_info(user_id_token)
            user_name = user_info['users'][0].get('displayName', 'Utilisateur')  # Utilisez un nom par défaut si displayName est absent
            
            # Stockez le nom de l'utilisateur dans la session
            session['user'] = user_name
        except Exception as e:
            logging.error(f"Erreur lors de la récupération des informations utilisateur : {e}")
            return redirect(url_for('main.login'))  # Redirigez si l'idToken est invalide ou expiré

    # Afficher la page d'accueil avec des métriques
    stock_symbol = "AAPL"
    try:
        previous_day_metrics = get_financial_metrics(stock_symbol)
        return render_template('index.html', stock_symbol=stock_symbol,
                               previous_day_metrics=previous_day_metrics or {},
                               user=session['user'])
    except Exception as e:
        logging.error(f"Erreur lors de la récupération des métriques pour {stock_symbol} : {e}")
        return render_template('index.html', stock_symbol=stock_symbol,
                               previous_day_metrics={},
                               error="Impossible de récupérer les métriques.",
                               user=session['user'])

@main.route('/stock-data', methods=['GET'])
def stock_data():
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
        return render_template("prediction.html")
    elif request.method == "POST":
        try:
            # Récupérer les données historiques (5 jours précédents)
            historical_data = get_stock_data(stock_symbol="AAPL", period="5d", interval="1d")
            actual_prices = historical_data["recent_prices"]

            # Ajouter le prix d'aujourd'hui s'il n'est pas déjà dans `actualPrices`
            today_data = get_stock_data(stock_symbol="AAPL", period="1d", interval="1d")
            today_price = today_data["recent_prices"][-1]  # Dernier prix du jour actuel

            # Vérifiez si le dernier prix historique est différent du prix d'aujourd'hui
            if actual_prices[-1] != today_price:
                actual_prices.append(today_price)  # Ajoute uniquement si nécessaire

            # Obtenir les prédictions
            prediction = predict_lstm()
            predicted_prices = prediction["predictions"]
            prediction_dates = prediction["dates"]

            # Combiner les dates historiques, la date d'aujourd'hui, et les dates de prédictions
            historical_dates = [(datetime.now() - timedelta(days=i)).strftime("%Y-%m-%d") for i in range(5, 0, -1)]
            today_date = datetime.now().strftime("%Y-%m-%d")

            # Évitez les doublons dans les dates
            combined_dates = historical_dates + [today_date] + prediction_dates

            response_data = {
                "dates": combined_dates,
                "actualPrices": actual_prices,
                "predictions": predicted_prices,
            }

            return jsonify(response_data), 200

        except Exception as e:
            logging.error(f"Erreur lors de la génération des prédictions : {e}")
            return jsonify({"error": "Une erreur est survenue."}), 500


@main.route('/investisseur', methods=['GET'])
def investisseur():
    # Liste des symboles boursiers des entreprises à analyser
    companies = ["AAPL", "GOOGL", "MSFT", "TSLA", "AMZN", "NFLX", "META", "NVDA"]

    # Liste pour stocker les informations des entreprises
    data = []

    # Boucle sur chaque entreprise de la liste
    for company in companies:
        try:
            # Initialisation d'un objet `Ticker` pour récupérer les données de l'entreprise
            stock = yf.Ticker(company)

            # Récupère les 5 dernières actualités uniquement pour Apple
            if company == "AAPL":
                news = stock.news[:5] if stock.news else []  # Dernières actualités (max 5 articles)
            else:
                news = []  # Pas d'actualités pour les autres entreprises
            info = {                "symbol": company,
                "price": stock.history(period="1d")['Close'].iloc[-1],  # Dernier prix de clôture
                "news": news  # Dernières actualités pour Apple ou vide pour les autres entreprises
            }

            # Ajout des informations de l'entreprise à la liste principale
            data.append(info)

        # Gestion des exceptions (si une erreur survient, elle est affichée dans la console)
        except Exception as e:
            print(f"Erreur lors de la récupération des données pour {company} : {e}")

    # Rendu de la page HTML `financial_corner.html`, en passant les données récupérées
    return render_template('financial_corner.html', data=data)
@main.get("/news")
def get_news():
    stock = yf.Ticker("AAPL")
    news_data = stock.news
    return {"news": news_data}