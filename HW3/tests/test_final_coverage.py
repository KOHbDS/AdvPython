import pytest
from fastapi.testclient import TestClient
from datetime import datetime, timedelta
from unittest.mock import patch, MagicMock
from app.main import app
from app import models, cache, auth
import json

def test_create_short_link_with_complex_data(client, db):
    """Тест создания ссылки со сложными данными"""
    expiry_date = (datetime.now() + timedelta(days=365)).isoformat()
    
    response = client.post(
        "/links/shorten",
        json={
            "original_url": "https://example.com/complex-data",
            "custom_alias": "complex-data",
            "expires_at": expiry_date
        }
    )
    
    assert response.status_code == 200
    data = response.json()
    assert data["short_code"] == "complex-data"
    
    db_link = db.query(models.Link).filter(models.Link.short_code == "complex-data").first()
    assert db_link is not None
    assert db_link.original_url == "https://example.com/complex-data"
    assert db_link.expires_at is not None

def test_get_link_stats_with_cache(client, db):
    """Тест получения статистики ссылки с использованием кэша"""
    link = models.Link(
        short_code="stats-with-cache",
        original_url="https://example.com/stats-with-cache",
        clicks=10,
        is_active=True
    )
    db.add(link)
    db.commit()
    
    stats = {
        "original_url": "https://example.com/stats-with-cache",
        "short_code": "stats-with-cache",
        "created_at": datetime.now().isoformat(),
        "clicks": 15,
        "last_used": datetime.now().isoformat(),
        "expires_at": None,
        "owner_id": None
    }
    cache.set_stats_cache("stats-with-cache", stats)

    response = client.get("/links/stats-with-cache/stats")

    assert response.status_code == 200
    data = response.json()
    assert data["clicks"] == 15
    assert data["short_code"] == "stats-with-cache"

def test_redirect_nonexistent_link_with_cache(client):
    """Тест перенаправления по несуществующей ссылке с кэшем"""
    cache.set_link_cache("nonexistent-link", "https://example.com/nonexistent")
    
    response = client.get("/nonexistent-link", follow_redirects=False)
    
    assert response.status_code == 404
    assert "Link not found" in response.json()["detail"]

def test_update_link_server_error(client, db, auth_token):
    """Тест обработки ошибки сервера при обновлении ссылки"""
    link = models.Link(
        short_code="update-error",
        original_url="https://example.com/update-error",
        is_active=True,
        owner_id=1
    )
    db.add(link)
    db.commit()
    
    with patch.object(db, 'commit', side_effect=Exception("Test error")):
        response = client.put(
            "/links/update-error",
            json={"original_url": "https://example.com/updated"},
            headers={"Authorization": f"Bearer {auth_token}"}
        )
        
        assert response.status_code == 500
        assert "Error updating link" in response.json()["detail"]

def test_delete_link_server_error(client, db, auth_token):
    """Тест обработки ошибки сервера при удалении ссылки"""
    link = models.Link(
        short_code="delete-error",
        original_url="https://example.com/delete-error",
        is_active=True,
        owner_id=1
    )
    db.add(link)
    db.commit()
    
    with patch.object(db, 'commit', side_effect=Exception("Test error")):
        response = client.delete(
            "/links/delete-error",
            headers={"Authorization": f"Bearer {auth_token}"}
        )
        
        assert response.status_code == 500
        assert "Error deleting link" in response.json()["detail"]
