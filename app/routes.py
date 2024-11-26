from flask import Flask, Blueprint, jsonify, render_template, Response, request
from app.utils.scraper import get_stock_data as scraper_stock_data  # Correct naming conflict
from app.models.lstm import predict_lstm  # LSTM prediction model
from pydantic import BaseModel
from flask_pydantic import validate
import yfinance as yf
import pandas as pd
import smtplib
from email.mime.text import MIMEText
import os  # For environment variables

app = Flask(__name__)
main = Blueprint("main", __name__)

# Load sensitive credentials from environment variables
SMTP_SERVER = os.getenv("SMTP_SERVER", "smtp-relay.sendinblue.com")
SMTP_PORT = int(os.getenv("SMTP_PORT", 587))
SMTP_EMAIL = os.getenv("SMTP_EMAIL", "your-email@example.com")
SMTP_PASSWORD = os.getenv("SMTP_PASSWORD", "your-password")

# Class for managing alerts with Pydantic
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

        with smtplib.SMTP(SMTP_SERVER, SMTP_PORT) as server:
            server.starttls()
            server.login(SMTP_EMAIL, SMTP_PASSWORD)
            server.sendmail(SMTP_EMAIL, email, msg.as_string())
    except Exception as e:
        print(f"Failed to send email: {e}")

# Route for setting a price alert
@main.route('/set-alert/', methods=['POST'])
@validate()
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
        return jsonify({"error": str(e)}), 500

# Route to fetch stock price predictions
@main.route('/predict', methods=['GET'])
def predict():
    try:
        prediction = predict_lstm()
        return jsonify({"stock_symbol": "AAPL", "Prediction": prediction}), 200
    except Exception as e:
        return jsonify({"error": str(e)}), 500

# Route to compare predicted vs. actual stock prices
@main.route('/predict-vs-actual', methods=['GET'])
def predict_vs_actual():
    try:
        stock_symbol = "AAPL"
        stock = yf.Ticker(stock_symbol)
        historical_data = stock.history(period="3mo")['Close']
        predicted_data = predict_lstm(historical_data)

        actual_vs_predicted = {
            "actual": historical_data.tolist(),
            "predicted": predicted_data.tolist()
        }
        return jsonify({"stock_symbol": stock_symbol, "data": actual_vs_predicted}), 200
    except Exception as e:
        return jsonify({"error": str(e)}), 500

# Route to download historical stock data as CSV
@main.route('/download-historical-data', methods=['GET'])
def download_historical_data():
    try:
        stock_symbol = "AAPL"
        stock = yf.Ticker(stock_symbol)
        historical_data = stock.history(period="3mo")
        historical_data.reset_index(inplace=True)
        csv = historical_data.to_csv(index=False)
        return Response(
            csv,
            mimetype="text/csv",
            headers={"Content-Disposition": f"attachment; filename={stock_symbol}_historical_data.csv"}
        )
    except Exception as e:
        return jsonify({"error": str(e)}), 500

# Route to fetch news related to AAPL
@main.route('/news', methods=['GET'])
def get_news():
    try:
        stock_symbol = "AAPL"
        stock = yf.Ticker(stock_symbol)
        news_data = stock.news
        return jsonify({"stock_symbol": stock_symbol, "news": news_data}), 200
    except Exception as e:
        return jsonify({"error": str(e)}), 500

@main.route('/track-price/<float:threshold>', methods=['GET'])
def track_price(threshold):
    try:
        stock_symbol = "AAPL"
        current_price_data = scraper_stock_data(stock_symbol)
        if not current_price_data or not isinstance(current_price_data, list):
            raise ValueError("Unexpected data format for current price.")

        current_price = float(current_price_data[0])  # Assume first item is the price
        alert_message = f"Price of {stock_symbol} {'exceeded' if current_price > threshold else 'is below'} ${threshold}."
        return jsonify({"alert": alert_message, "current_price": current_price}), 200
    except Exception as e:
        return jsonify({"error": str(e)}), 500


# Register the blueprint and launch the application
app.register_blueprint(main)

if __name__ == "__main__":
    app.run(debug=True)
