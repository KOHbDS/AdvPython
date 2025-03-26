import pytest
from datetime import datetime, timedelta
from app import models, cache

# Используем фикстуру auth_token из conftest.py

def test_cache_set_get(db):
    """Тест базовых операций с кэшем"""
    # Очищаем кэш перед тестом
    if hasattr(cache, '_memory_cache'):
        cache._memory_cache.clear()
    
    # Устанавливаем значение в кэш
    cache.set_link_cache("test_key", "test_value")
    
    # Получаем значение из кэша
    value = cache.get_link_cache("test_key")
    
    # Проверяем, что значение получено корректно
    assert value == "test_value"

def test_cache_delete(db):
    """Тест удаления из кэша"""
    # Очищаем кэш перед тестом
    if hasattr(cache, '_memory_cache'):
        cache._memory_cache.clear()
    
    # Устанавливаем значение в кэш
    cache.set_link_cache("test_key", "test_value")
    
    # Проверяем, что значение установлено
    assert cache.get_link_cache("test_key") == "test_value"
    
    # Удаляем значение из кэша
    cache.delete_link_cache("test_key")
    
    # Проверяем, что значение удалено
    assert cache.get_link_cache("test_key") is None

def test_cache_stats(db):
    """Тест работы с кэшем статистики"""
    # Очищаем кэш перед тестом
    if hasattr(cache, '_memory_cache'):
        cache._memory_cache.clear()
    
    # Создаем статистику
    stats = {
        "original_url": "https://example.com",
        "short_code": "test_stats",
        "created_at": datetime.now().isoformat(),
        "clicks": 0,
        "last_used": None,
        "expires_at": None,
        "owner_id": 1
    }
    
    # Устанавливаем статистику в кэш
    cache.set_stats_cache("test_stats", stats)
    
    # Получаем статистику из кэша
    cached_stats = cache.get_stats_cache("test_stats")
    
    # Проверяем, что статистика получена корректно
    assert cached_stats is not None
    assert cached_stats["short_code"] == "test_stats"
    assert cached_stats["original_url"] == "https://example.com"
    assert cached_stats["clicks"] == 0

def test_cache_increment_clicks(db):
    """Тест инкремента счетчика кликов в кэше"""
    # Очищаем кэш перед тестом
    if hasattr(cache, '_memory_cache'):
        cache._memory_cache.clear()
    
    # Создаем статистику
    stats = {
        "original_url": "https://example.com",
        "short_code": "test_clicks",
        "created_at": datetime.now().isoformat(),
        "clicks": 5,
        "last_used": datetime.now().isoformat(),
        "expires_at": None,
        "owner_id": 1
    }
    
    # Устанавливаем статистику в кэш
    cache.set_stats_cache("test_clicks", stats)
    
    # Инкрементируем счетчик кликов
    cache.increment_link_clicks("test_clicks")
    
    # Получаем обновленную статистику
    updated_stats = cache.get_stats_cache("test_clicks")
    
    # Проверяем, что счетчик увеличился
    assert updated_stats is not None
    assert updated_stats["clicks"] == 6
    assert updated_stats["last_used"] is not None

def test_link_creation_caching(client, db, auth_token):
    """Тест кэширования при создании ссылки"""
    # Очищаем кэш перед тестом
    if hasattr(cache, '_memory_cache'):
        cache._memory_cache.clear()
    
    # Создаем ссылку
    response = client.post(
        "/links/shorten",
        json={"original_url": "https://example.com/cache", "custom_alias": "cache_test"},
        headers={"Authorization": f"Bearer {auth_token}"}
    )
    assert response.status_code == 200
    
    # Проверяем, что ссылка добавлена в кэш
    cached_url = cache.get_link_cache("cache_test")
    assert cached_url == "https://example.com/cache"

def test_link_update_caching(client, db, auth_token):
    """Тест обновления кэша при обновлении ссылки"""
    # Очищаем кэш перед тестом
    if hasattr(cache, '_memory_cache'):
        cache._memory_cache.clear()
    
    # Создаем ссылку
    client.post(
        "/links/shorten",
        json={"original_url": "https://example.com/original", "custom_alias": "update_test"},
        headers={"Authorization": f"Bearer {auth_token}"}
    )
    
    # Проверяем начальное значение в кэше
    assert cache.get_link_cache("update_test") == "https://example.com/original"
    
    # Обновляем ссылку
    response = client.put(
        "/links/update_test",
        json={"original_url": "https://example.com/updated"},
        headers={"Authorization": f"Bearer {auth_token}"}
    )
    assert response.status_code == 200
    
    # Проверяем, что кэш обновлен
    updated_url = cache.get_link_cache("update_test")
    assert updated_url == "https://example.com/updated"

def test_link_delete_caching(client, db, auth_token):
    """Тест удаления из кэша при удалении ссылки"""
    # Очищаем кэш перед тестом
    if hasattr(cache, '_memory_cache'):
        cache._memory_cache.clear()
    
    # Создаем ссылку
    client.post(
        "/links/shorten",
        json={"original_url": "https://example.com/delete", "custom_alias": "delete_test"},
        headers={"Authorization": f"Bearer {auth_token}"}
    )
    
    # Проверяем, что ссылка добавлена в кэш
    assert cache.get_link_cache("delete_test") == "https://example.com/delete"
    
    # Удаляем ссылку
    response = client.delete(
        "/links/delete_test",
        headers={"Authorization": f"Bearer {auth_token}"}
    )
    assert response.status_code == 204
    
    # Проверяем, что ссылка удалена из кэша
    assert cache.get_link_cache("delete_test") is None

def test_redirect_uses_cache(client, db, auth_token):
    """Тест использования кэша при перенаправлении"""
    # Очищаем кэш перед тестом
    if hasattr(cache, '_memory_cache'):
        cache._memory_cache.clear()
    
    # Создаем ссылку
    client.post(
        "/links/shorten",
        json={"original_url": "https://example.com/redirect", "custom_alias": "redirect_test"},
        headers={"Authorization": f"Bearer {auth_token}"}
    )
    
    # Проверяем, что ссылка добавлена в кэш
    assert cache.get_link_cache("redirect_test") == "https://example.com/redirect"
    
    # Выполняем перенаправление
    response = client.get("/redirect_test", allow_redirects=False)
    assert response.status_code == 307
    assert response.headers["location"] == "https://example.com/redirect"
    
    # Проверяем, что счетчик кликов увеличился в базе данных
    link = db.query(models.Link).filter(models.Link.short_code == "redirect_test").first()
    assert link.clicks == 1
