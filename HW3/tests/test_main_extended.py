# tests/test_main_extended.py
import pytest
from fastapi.testclient import TestClient
from datetime import datetime, timedelta
from unittest.mock import patch, MagicMock
from app.main import app, generate_unique_short_code, parse_expiry_date, check_link_expiry
from app import models

def test_root_endpoint(client):
    """Тест корневого эндпоинта"""
    response = client.get("/")
    assert response.status_code == 200
    assert "message" in response.json()
    assert "Welcome" in response.json()["message"]

def test_health_check_endpoint(client, db):
    """Тест эндпоинта проверки здоровья"""
    response = client.get("/healthz")
    assert response.status_code == 200
    data = response.json()
    assert "status" in data
    assert "database" in data
    assert "redis" in data

def test_health_check_with_db_error(client):
    """Тест эндпоинта здоровья с ошибкой БД"""
    with patch('app.database.get_db', side_effect=Exception("DB Error")):
        response = client.get("/healthz")
        assert response.status_code in [200, 503]
        data = response.json()
        assert "database" in data

def test_custom_swagger_ui(client):
    """Тест кастомной Swagger UI"""
    response = client.get("/docs-v2")
    assert response.status_code == 200
    assert "text/html" in response.headers["content-type"]
    assert "swagger-ui" in response.text


def test_parse_expiry_date_with_exceptions():
    """Тест обработки исключений при парсинге даты"""
    with pytest.raises(Exception):
        parse_expiry_date("invalid-date-format")
    
    assert parse_expiry_date(None) is None
    
    now = datetime.now()
    assert parse_expiry_date(now) == now
