import pytest
from app import app
from flask import jsonify
from unittest.mock import patch
import json

# Test configuration
@pytest.fixture
def client():
    with app.test_client() as client:
        yield client

# ============================ Test Routes ============================

# Test: Home route (GET /)
def test_home(client):
    """Test the home page route"""
    response = client.get('/')
    assert response.status_code == 200
    assert b"Bienvenue sur la page d'accueil" in response.data  # Adjust this based on your template content

# Test: Register route (GET /register)
def test_register_get(client):
    """Test the registration page (GET)"""
    response = client.get('/register')
    assert response.status_code == 200
    assert b"Créer un compte" in response.data  # Adjust based on your template content

# Test: Register route (POST /register)
def test_register_post(client):
    """Test the registration form submission (POST)"""
    response = client.post('/register', data={'email': 'testuser@example.com', 'password': 'password123'})
    assert response.status_code == 200
    assert b"Compte créé avec succès" in response.data  # Adjust based on your template content

# Test: Login route (GET /login)
def test_login_get(client):
    """Test the login page (GET)"""
    response = client.get('/login')
    assert response.status_code == 200
    assert b"Se connecter" in response.data  # Adjust based on your template content

# Test: Login route (POST /login)
def test_login_post(client):
    """Test the login form submission (POST)"""
    response = client.post('/login', data={'email': 'testuser@example.com', 'password': 'password123'})
    assert response.status_code == 200
    assert b"Utilisateur connecté" in response.data  # Adjust based on successful login message

# Test: Prediction route (GET /prediction)
def test_prediction_get(client):
    """Test the prediction page (GET)"""
    response = client.get('/prediction')
    assert response.status_code == 200
    assert b"Faire une prédiction" in response.data  # Adjust based on your template content

# Test: Prediction route (POST /prediction)
@patch('app.models.lstm.predict_lstm')
def test_prediction_post(mock_predict, client):
    """Test the prediction form submission (POST)"""
    mock_predict.return_value = {"dates": ["2024-01-01", "2024-01-02"], "predictions": [150, 155]}
    response = client.post('/prediction')
    data = json.loads(response.data)
    assert response.status_code == 200
    assert "dates" in data
    assert "predictions" in data
    assert len(data["dates"]) == 2
    assert data["predictions"] == [150, 155]

# Test: Financial Metrics route (GET /financial-metrics/<stock_symbol>)
def test_financial_metrics(client):
    """Test the financial metrics route (GET)"""
    with patch('app.utils.metrics.get_financial_metrics') as mock_metrics:
        mock_metrics.return_value = {"PE Ratio": 30, "Market Cap": 2_000_000_000_000}
        response = client.get('/financial-metrics/AAPL')
        assert response.status_code == 200
        data = json.loads(response.data)
        assert data["stock_symbol"] == "AAPL"
        assert "metrics" in data
        assert data["metrics"]["PE Ratio"] == 30

# Test: Stock Data route (GET /stock-data)
def test_stock_data(client):
    """Test the stock data route (GET)"""
    with patch('app.utils.scraper.get_stock_data') as mock_scraper:
        mock_scraper.return_value = {"recent_prices": [{"date": "2024-01-01", "price": 150}]}
        response = client.get('/stock-data')
        assert response.status_code == 200
        data = json.loads(response.data)
        assert data["stock_symbol"] == "AAPL"
        assert len(data["2024_prices"]) > 0
        assert data["2024_prices"][0]["prix"] == 150

# Test: Alert route (POST /set-alert/)
def test_set_alert(client):
    """Test the alert creation (POST)"""
    response = client.post('/set-alert/', json={'email': 'testalert@example.com', 'price': 160})
    assert response.status_code == 200
    data = json.loads(response.data)
    assert data["message"] == "Alerte configurée avec succès !"

# Test: Forgot Password route (POST /forgot_password)
def test_forgot_password(client):
    """Test the forgot password form submission"""
    response = client.post('/forgot_password', data={'email': 'testuser@example.com'})
    assert response.status_code == 200
    assert b"E-mail de réinitialisation envoyé." in response.data  # Adjust based on your template content

# Test: Reset Password route (POST /reset-password)
def test_reset_password(client):
    """Test the reset password form submission"""
    response = client.post('/reset-password', data={'email': 'testuser@example.com'})
    assert response.status_code == 200
    assert b"Un e-mail de réinitialisation a été envoyé" in response.data  # Adjust based on your template content

# Test: Logout route (GET /logout)
def test_logout(client):
    """Test the logout route"""
    response = client.get('/logout')
    assert response.status_code == 302  # Should redirect
    assert b"Utilisateur déconnecté." in response.data  # Adjust based on logout message
