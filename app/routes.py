from flask import Flask, Blueprint, jsonify, render_template, Response, request
from flask_limiter import Limiter
from flask_limiter.util import get_remote_address
from app.utils.scraper import get_stock_data as scraper_stock_data  # Avoid naming conflicts
from app.models.lstm import predict_lstm  # LSTM prediction model
from pydantic import BaseModel
from flask_pydantic import validate
import yfinance as yf
import pandas as pd
import smtplib
from email.mime.text import MIMEText
import os
import logging

# Configure logging
logging.basicConfig(level=logging.ERROR)

app = Flask(__name__)
limiter = Limiter(get_remote_address, app=app)
main = Blueprint("main", __name__)

# Load sensitive credentials from environment variables
SMTP_SERVER = os.getenv("SMTP_SERVER")
SMTP_PORT = os.getenv("SMTP_PORT")
SMTP_EMAIL = os.getenv("SMTP_EMAIL")
SMTP_PASSWORD = os.getenv("SMTP_PASSWORD")

# Validate environment variables
for var_name, var_value in {
    "SMTP_SERVER": SMTP_SERVER,
    "SMTP_PORT": SMTP_PORT,
    "SMTP_EMAIL": SMTP_EMAIL,
    "SMTP_PASSWORD": SMTP_PASSWORD,
}.items():
    if not var_value:
        raise ValueError(f"Missing environment variable: {var_name}")

# Pydantic class for managing alerts
class Alert(BaseModel):
    email: str
    price: float

# Function to send an email alert
def send_email_alert(email: str, price: float):
    """
    Sends a stock price alert email.

    Parameters:
        email (str): Recipient's email address.
        price (float): Stock price triggering the alert.
    """
    try:
        msg = MIMEText(f"Apple stock price has reached your alert level: ${price}")
        msg['Subject'] = 'Price Alert!'
        msg['From'] = SMTP_EMAIL
        msg['To'] = email

        with smtplib.SMTP(SMTP_SERVER, int(SMTP_PORT)) as server:
            server.starttls()
            server.login(SMTP_EMAIL, SMTP_PASSWORD)
            server.sendmail(SMTP_EMAIL, email, msg.as_string())
    except Exception as e:
        logging.error(f"Failed to send email to {email}: {e}")

# Route for setting a price alert
@main.route('/set-alert/', methods=['POST'])
@validate()
@limiter.limit("10 per minute")  # Limit to 10 requests per minute
def set_alert(alert: Alert):
    """
    Set a price alert for AAPL stock.

    Parameters:
        alert (Alert): Contains the email and price threshold.

    Returns:
        JSON response confirming the alert.
    """
    send_email_alert(alert.email, alert.price)
    return jsonify({"message": "Alert set!"}), 200

# Route to display the homepage
@main.route('/')
def home():
    return render_template('index.html')

# Route to fetch historical stock prices
@main.route('/stock-data', methods=['GET'])
def stock_data():
    try:
        stock_symbol = "AAPL"
        prices = scraper_stock_data(stock_symbol)
        return jsonify({"stock_symbol": stock_symbol, "prices": prices}), 200
    except Exception as e:
        logging.error(f"Error in stock_data: {e}")
        return jsonify({"error": "Failed to fetch stock data"}), 500

# Route to fetch stock price predictions
@main.route('/predict', methods=['GET'])
def predict():
    try:
        prediction = predict_lstm()
        return jsonify({"stock_symbol": "AAPL", "Prediction": prediction}), 200
    except Exception as e:
        logging.error(f"Error in predict: {e}")
        return jsonify({"error": "Failed to generate predictions"}), 500

# Route to compare predicted vs. actual stock prices
@main.route('/predict-vs-actual', methods=['GET'])
def predict_vs_actual():
    try:
        stock_symbol = "AAPL"
        stock = yf.Ticker(stock_symbol)
        historical_data = stock.history(period="3mo")['Close']
        if historical_data.empty:
            raise ValueError("No historical data available")
        
        predicted_data = predict_lstm(historical_data)

        actual_vs_predicted = {
            "actual": historical_data.tolist(),
            "predicted": predicted_data.tolist()
        }
        return jsonify({"stock_symbol": stock_symbol, "data": actual_vs_predicted}), 200
    except Exception as e:
        logging.error(f"Error in predict_vs_actual: {e}")
        return jsonify({"error": "Failed to fetch prediction and comparison data"}), 500

# Route to download historical stock data as CSV
@main.route('/download-historical-data', methods=['GET'])
def download_historical_data():
    try:
        stock_symbol = "AAPL"
        stock = yf.Ticker(stock_symbol)
        historical_data = stock.history(period="3mo")
        if historical_data.empty:
            raise ValueError("No historical data available")
        
        historical_data.reset_index(inplace=True)
        csv = historical_data.to_csv(index=False)
        return Response(
            csv,
            mimetype="text/csv",
            headers={"Content-Disposition": f"attachment; filename={stock_symbol}_historical_data.csv"}
        )
    except Exception as e:
        logging.error(f"Error in download_historical_data: {e}")
        return jsonify({"error": "Failed to download historical data"}), 500

# Route to fetch stock prices for multiple enterprises
@main.route('/multi-stock-data', methods=['GET'])
def multi_stock_data():
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
                stock_data[symbol] = {"error": "No data available"}

        return jsonify(stock_data), 200
    except Exception as e:
        logging.error(f"Error in multi_stock_data: {e}")
        return jsonify({"error": "Failed to fetch multiple stock data"}), 500

# Route to fetch news related to AAPL
@main.route('/news', methods=['GET'])
def get_news():
    try:
        stock_symbol = "AAPL"
        stock = yf.Ticker(stock_symbol)
        news_data = getattr(stock, "news", [])
        return jsonify({"stock_symbol": stock_symbol, "news": news_data}), 200
    except Exception as e:
        logging.error(f"Error in get_news: {e}")
        return jsonify({"error": "Failed to fetch news data"}), 500

# Route to track stock price against a threshold
@main.route('/track-price/<float:threshold>', methods=['GET'])
def track_price(threshold):
    try:
        stock_symbol = "AAPL"
        current_price_data = scraper_stock_data(stock_symbol)
        if not current_price_data or not isinstance(current_price_data, list):
            raise ValueError("Unexpected data format for current price")

        current_price = float(current_price_data[0])
        alert_message = f"Price of {stock_symbol} {'exceeded' if current_price > threshold else 'is below'} ${threshold}."
        return jsonify({"alert": alert_message, "current_price": current_price}), 200
    except Exception as e:
        logging.error(f"Error in track_price: {e}")
        return jsonify({"error": "Failed to track price"}), 500

# Register the blueprint and launch the application
app.register_blueprint(main)

if __name__ == "__main__":
    app.run(debug=True)
