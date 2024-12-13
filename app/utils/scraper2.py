import yfinance as yf

def get_stock_data(stock_symbol):
    stock = yf.Ticker(stock_symbol)
    # Fetch historical data for the last 3 months
    historical_data = stock.history(period="3mo")
    prices = historical_data['Close'].tolist()  # List of closing prices
    return prices

