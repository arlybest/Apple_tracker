from flask import Blueprint, jsonify, render_template
from app.utils.scraper import scrape_stock_data

# Blueprint for routes
main = Blueprint('main', __name__)

# Home route
@main.route('/')
def home():
    return render_template('index.html')  # Render an HTML template (if required)

# Route for fetching Apple stock price
@main.route('/stock-data/<string:stock_symbol>', methods=['GET'])
def get_stock_data(stock_symbol):
    try:
        prices = scrape_stock_data(stock_symbol)
        return jsonify({"stock_symbol": stock_symbol, "prices": prices}), 200
    except Exception as e:
        return jsonify({"error": str(e)}), 500
