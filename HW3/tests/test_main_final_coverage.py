import pytest
from fastapi.testclient import TestClient
from datetime import datetime, timedelta
from unittest.mock import patch, MagicMock
from app.main import app
from app import models, cache, auth, background_tasks
import json
import os

def test_create_short_link_with_custom_expiry(client, db):
    """Тест создания ссылки с пользовательским сроком истечения"""
    expiry_date = (datetime.now() + timedelta(days=30)).isoformat()
    
    response = client.post(
        "/links/shorten",
        json={
            "original_url": "https://example.com/custom-expiry",
            "custom_alias": "custom-expiry",
            "expires_at": expiry_date
        }
    )
    
    assert response.status_code == 200
    data = response.json()
    assert data["short_code"] == "custom-expiry"
    
    db_link = db.query(models.Link).filter(models.Link.short_code == "custom-expiry").first()
    assert db_link.expires_at is not None

def test_link_search_with_auth(client, db, auth_token):
    """Тест поиска ссылки с аутентификацией"""
    response = client.post(
        "/links/shorten",
        json={
            "original_url": "https://example.com/search-test",
            "custom_alias": "search-test"
        },
        headers={"Authorization": f"Bearer {auth_token}"}
    )
    
    response = client.get(
        "/links/search?original_url=https://example.com/search-test",
        headers={"Authorization": f"Bearer {auth_token}"}
    )
    
    assert response.status_code == 200
    data = response.json()
    assert data["short_code"] == "search-test"

def test_get_expired_links_with_active_expired(client, db, auth_token):
    """Тест получения истекших ссылок, включая активные с истекшим сроком"""
    link = models.Link(
        short_code="active-expired",
        original_url="https://example.com/active-expired",
        expires_at=datetime.now() - timedelta(days=1),
        is_active=True,
        owner_id=1
    )
    db.add(link)
    db.commit()

    response = client.get(
        "/expired-links",
        headers={"Authorization": f"Bearer {auth_token}"}
    )
    
    assert response.status_code == 200
    data = response.json()
    assert len(data) > 0
    assert any(link["short_code"] == "active-expired" for link in data)
    
    db_link = db.query(models.Link).filter(models.Link.short_code == "active-expired").first()
    assert db_link.is_active is False

def test_redirect_cache_update(client, db):
    """Тест обновления кэша при перенаправлении"""
    link = models.Link(
        short_code="cache-update",
        original_url="https://example.com/cache-update",
        is_active=True
    )
    db.add(link)
    db.commit()
    
    cache.set_link_cache("cache-update", "https://example.com/cache-update")
    
    original_get_stats = cache.get_stats_cache
    
    try:
        def mock_get_stats(short_code):
            return None

        cache.get_stats_cache = mock_get_stats
        
        response = client.get("/cache-update", follow_redirects=False)
        
        assert response.status_code == 307
        assert response.headers["location"] == "https://example.com/cache-update"
        db_link = db.query(models.Link).filter(models.Link.short_code == "cache-update").first()
        assert db_link.clicks == 1
        assert db_link.last_used is not None
    finally:
        cache.get_stats_cache = original_get_stats

def test_redirect_with_cache_stats(client, db):
    """Тест перенаправления с использованием кэша статистики"""
    link = models.Link(
        short_code="cache-stats",
        original_url="https://example.com/cache-stats",
        is_active=True
    )
    db.add(link)
    db.commit()
    
    stats = {
        "original_url": "https://example.com/cache-stats",
        "short_code": "cache-stats",
        "created_at": datetime.now().isoformat(),
        "clicks": 5,
        "last_used": datetime.now().isoformat(),
        "expires_at": None,
        "owner_id": None
    }
    cache.set_stats_cache("cache-stats", stats)
    
    response = client.get("/cache-stats", follow_redirects=False)
    
    assert response.status_code == 307
    assert response.headers["location"] == "https://example.com/cache-stats"
    
    updated_stats = cache.get_stats_cache("cache-stats")
    assert updated_stats["clicks"] == 6
