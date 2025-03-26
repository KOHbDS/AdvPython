import pytest
from datetime import datetime, timedelta
from app import models, cache

def test_cache_set_get(db):
    """Тест базовых операций с кэшем"""
    if hasattr(cache, '_memory_cache'):
        cache._memory_cache.clear()
    
    cache.set_link_cache("test_key", "test_value")
    
    value = cache.get_link_cache("test_key")
    
    assert value == "test_value"

def test_cache_delete(db):
    """Тест удаления из кэша"""
    if hasattr(cache, '_memory_cache'):
        cache._memory_cache.clear()

    cache.set_link_cache("test_key", "test_value")
    
    assert cache.get_link_cache("test_key") == "test_value"

    cache.delete_link_cache("test_key")
    assert cache.get_link_cache("test_key") is None

def test_cache_stats(db):
    """Тест работы с кэшем статистики"""

    if hasattr(cache, '_memory_cache'):
        cache._memory_cache.clear()

    stats = {
        "original_url": "https://example.com",
        "short_code": "test_stats",
        "created_at": datetime.now().isoformat(),
        "clicks": 0,
        "last_used": None,
        "expires_at": None,
        "owner_id": 1
    }

    cache.set_stats_cache("test_stats", stats)
    
    cached_stats = cache.get_stats_cache("test_stats")
    
    assert cached_stats is not None
    assert cached_stats["short_code"] == "test_stats"
    assert cached_stats["original_url"] == "https://example.com"
    assert cached_stats["clicks"] == 0

def test_cache_increment_clicks(db):
    """Тест инкремента счетчика кликов в кэше"""
    if hasattr(cache, '_memory_cache'):
        cache._memory_cache.clear()
    
    stats = {
        "original_url": "https://example.com",
        "short_code": "test_clicks",
        "created_at": datetime.now().isoformat(),
        "clicks": 5,
        "last_used": datetime.now().isoformat(),
        "expires_at": None,
        "owner_id": 1
    }
    
    cache.set_stats_cache("test_clicks", stats)
    
    cache.increment_link_clicks("test_clicks")
    
    updated_stats = cache.get_stats_cache("test_clicks")
    

    assert updated_stats is not None
    assert updated_stats["clicks"] == 6
    assert updated_stats["last_used"] is not None

def test_link_creation_caching(client, db, auth_token):
    """Тест кэширования при создании ссылки"""
    if hasattr(cache, '_memory_cache'):
        cache._memory_cache.clear()
    response = client.post(
        "/links/shorten",
        json={"original_url": "https://example.com/cache", "custom_alias": "cache_test"},
        headers={"Authorization": f"Bearer {auth_token}"}
    )
    assert response.status_code == 200
    cached_url = cache.get_link_cache("cache_test")
    assert cached_url == "https://example.com/cache"

def test_link_update_caching(client, db, auth_token):
    """Тест обновления кэша при обновлении ссылки"""
    if hasattr(cache, '_memory_cache'):
        cache._memory_cache.clear()
    
    client.post(
        "/links/shorten",
        json={"original_url": "https://example.com/original", "custom_alias": "update_test"},
        headers={"Authorization": f"Bearer {auth_token}"}
    )
    
    assert cache.get_link_cache("update_test") == "https://example.com/original"
    
    response = client.put(
        "/links/update_test",
        json={"original_url": "https://example.com/updated"},
        headers={"Authorization": f"Bearer {auth_token}"}
    )
    assert response.status_code == 200
    
    updated_url = cache.get_link_cache("update_test")
    assert updated_url == "https://example.com/updated"

def test_link_delete_caching(client, db, auth_token):
    """Тест удаления из кэша при удалении ссылки"""
    if hasattr(cache, '_memory_cache'):
        cache._memory_cache.clear()
    
    client.post(
        "/links/shorten",
        json={"original_url": "https://example.com/delete", "custom_alias": "delete_test"},
        headers={"Authorization": f"Bearer {auth_token}"}
    )
    
    assert cache.get_link_cache("delete_test") == "https://example.com/delete"
    
    response = client.delete(
        "/links/delete_test",
        headers={"Authorization": f"Bearer {auth_token}"}
    )
    assert response.status_code == 204
    assert cache.get_link_cache("delete_test") is None

def test_redirect_uses_cache(client, db, auth_token):
    """Тест использования кэша при перенаправлении"""
    if hasattr(cache, '_memory_cache'):
        cache._memory_cache.clear()
    client.post(
        "/links/shorten",
        json={"original_url": "https://example.com/redirect", "custom_alias": "redirect_test"},
        headers={"Authorization": f"Bearer {auth_token}"}
    )
    
    assert cache.get_link_cache("redirect_test") == "https://example.com/redirect"
    
    response = client.get("/redirect_test", allow_redirects=False)
    assert response.status_code == 307
    assert response.headers["location"] == "https://example.com/redirect"
    
    link = db.query(models.Link).filter(models.Link.short_code == "redirect_test").first()
    assert link.clicks == 1
