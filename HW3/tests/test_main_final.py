# tests/test_main_final.py
import pytest
from fastapi.testclient import TestClient
from datetime import datetime, timedelta
from unittest.mock import patch, MagicMock
from app.main import app, generate_unique_short_code, parse_expiry_date, check_link_expiry
from app import models, cache, auth
import json

def test_create_short_link_validation_error(client):
    """Тест валидации данных при создании ссылки"""
    response = client.post(
        "/links/shorten",
        json={"original_url": ""}
    )
    assert response.status_code == 422

    response = client.post(
        "/links/shorten",
        json={"original_url": "not-a-url"}
    )
    assert response.status_code == 422

    response = client.post(
        "/links/shorten",
        json={"original_url": "https://example.com", "custom_alias": "a"}
    )
    assert response.status_code == 422
    
    response = client.post(
        "/links/shorten",
        json={"original_url": "https://example.com", "custom_alias": "a" * 60}
    )
    assert response.status_code == 422

def test_get_current_user_auth_error(client):
    """Тест ошибки аутентификации"""

    response = client.get("/links/search?original_url=https://example.com")
    assert response.status_code == 401

    response = client.get(
        "/links/search?original_url=https://example.com",
        headers={"Authorization": "Bearer invalid.token"}
    )
    assert response.status_code == 401

def test_get_expired_links_empty(client, auth_token):
    """Тест получения пустого списка истекших ссылок"""
    response = client.get(
        "/expired-links",
        headers={"Authorization": f"Bearer {auth_token}"}
    )
    assert response.status_code == 200
    assert response.json() == []

def test_get_expired_links_with_data(client, db, auth_token):
    """Тест получения списка истекших ссылок с данными"""
    inactive_link = models.Link(
        short_code="expired_list",
        original_url="https://example.com/expired",
        expires_at=datetime.now() - timedelta(days=1),
        is_active=False,
        owner_id=1
    )
    db.add(inactive_link)
    db.commit()
    
    response = client.get(
        "/expired-links",
        headers={"Authorization": f"Bearer {auth_token}"}
    )
    assert response.status_code == 200
    data = response.json()
    assert len(data) > 0
    assert any(link["short_code"] == "expired_list" for link in data)

def test_update_link_with_expiry(client, db, auth_token):
    """Тест обновления ссылки с датой истечения"""
    response = client.post(
        "/links/shorten",
        json={"original_url": "https://example.com/update-expiry", "custom_alias": "update-expiry"},
        headers={"Authorization": f"Bearer {auth_token}"}
    )
    expiry_date = (datetime.now() + timedelta(days=1)).isoformat()
    response = client.put(
        "/links/update-expiry",
        json={"expires_at": expiry_date},
        headers={"Authorization": f"Bearer {auth_token}"}
    )
    
    assert response.status_code == 200
    data = response.json()
    assert data["short_code"] == "update-expiry"

    db_link = db.query(models.Link).filter(models.Link.short_code == "update-expiry").first()
    assert db_link.expires_at is not None

def test_create_short_link_with_background_task(client, db):
    """Тест фоновой задачи при создании ссылки"""
    with patch('app.background_tasks.cleanup_expired_links') as mock_cleanup:
        response = client.post(
            "/links/shorten",
            json={"original_url": "https://example.com/background"}
        )
        
        assert response.status_code == 200
        mock_cleanup.assert_called_once()

def test_redirect_with_db_error(client, db):
    """Тест перенаправления с ошибкой БД"""
    link = models.Link(
        short_code="redirect-db-error",
        original_url="https://example.com/redirect-error",
        is_active=True
    )
    db.add(link)
    db.commit()

    cache.set_link_cache("redirect-db-error", "https://example.com/redirect-error")

    with patch.object(db, 'commit', side_effect=Exception("Test DB error")):
        response = client.get("/redirect-db-error", follow_redirects=False)
        
        assert response.status_code == 307
        assert response.headers["location"] == "https://example.com/redirect-error"

def test_startup_event_with_mocks():
    """Тест события запуска с моками"""
    with patch('sqlalchemy.orm.Session.execute') as mock_execute:
        with patch('app.cache.redis_client') as mock_redis:
            mock_execute.return_value.fetchone.return_value = (1,)
            mock_redis.ping.return_value = True
            
            startup_handlers = [handler for handler in app.router.on_startup]
            
            assert len(startup_handlers) > 0
