# tests/test_main_additional.py
import pytest
from fastapi.testclient import TestClient
from datetime import datetime, timedelta
from unittest.mock import patch, MagicMock
from app.main import app, generate_unique_short_code, parse_expiry_date, check_link_expiry
from app import models, cache, background_tasks

def test_create_short_link_no_auth(client):
    """Тест создания короткой ссылки без аутентификации"""
    response = client.post(
        "/links/shorten",
        json={"original_url": "https://example.com/no-auth"}
    )
    
    assert response.status_code == 200
    data = response.json()
    assert "short_code" in data
    assert data["original_url"] == "https://example.com/no-auth"

def test_create_short_link_invalid_url(client):
    """Тест создания короткой ссылки с невалидным URL"""
    response = client.post(
        "/links/shorten",
        json={"original_url": "invalid-url"}
    )
    
    assert response.status_code == 422 

def test_create_short_link_invalid_expiry(client):
    """Тест создания короткой ссылки с невалидной датой истечения"""
    response = client.post(
        "/links/shorten",
        json={"original_url": "https://example.com", "expires_at": "invalid-date"}
    )
    
    assert response.status_code == 400
    assert "Invalid date format" in response.json()["detail"]

def test_create_short_link_server_error(client, db):
    """Тест обработки ошибок сервера при создании ссылки"""
    with patch.object(db, 'commit', side_effect=Exception("Test error")):
        response = client.post(
            "/links/shorten",
            json={"original_url": "https://example.com/error"}
        )
        
        assert response.status_code == 500
        assert "Error creating link" in response.json()["detail"]

def test_get_expired_links_empty(client, auth_token):
    """Тест получения пустого списка истекших ссылок"""
    response = client.get(
        "/expired-links",
        headers={"Authorization": f"Bearer {auth_token}"}
    )
    
    assert response.status_code == 200
    assert response.json() == []

def test_redirect_nonexistent(client):
    """Тест перенаправления по несуществующей ссылке"""
    response = client.get("/nonexistent-code", follow_redirects=False)
    
    assert response.status_code == 404
    assert response.json()["detail"] == "Link not found"

def test_redirect_with_cache(client, db, auth_token):
    """Тест перенаправления с использованием кэша"""
    response = client.post(
        "/links/shorten",
        json={"original_url": "https://example.com/cached", "custom_alias": "cache-test"},
        headers={"Authorization": f"Bearer {auth_token}"}
    )
    
    cache.set_link_cache("cache-test", "https://example.com/cached")
    
    response = client.get("/cache-test", follow_redirects=False)
    
    assert response.status_code == 307
    assert response.headers["location"] == "https://example.com/cached"

def test_custom_docs(client):
    """Тест кастомной документации"""
    response = client.get("/docs-v2")
    
    assert response.status_code == 200
    assert "text/html" in response.headers["content-type"]
    assert "swagger-ui" in response.text
