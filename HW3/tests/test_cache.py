import pytest
from datetime import datetime, timedelta
from app import models

@pytest.fixture
def auth_token(client, db):
    # Создаем пользователя и получаем токен
    client.post(
        "/users/",
        json={"username": "testuser", "email": "test@example.com", "password": "password123"}
    )
    response = client.post(
        "/token",
        data={"username": "testuser", "password": "password123"}
    )
    return response.json()["access_token"]

def test_cache_invalidation(client, db, auth_token):
    # Создаем ссылку
    client.post(
        "/links/shorten",
        json={"original_url": "https://example.com", "custom_alias": "toinvalidate"},
        headers={"Authorization": f"Bearer {auth_token}"}
    )
    
    # Первый запрос должен сохранить ссылку в кэше
    client.get("/toinvalidate", allow_redirects=False)
    
    # Проверяем, что ссылка в кэше
    from app.cache import get_link_cache
    cached_url = get_link_cache("toinvalidate")
    assert cached_url == "https://example.com"
    
    # Обновляем ссылку
    client.put(
        "/links/toinvalidate",
        json={"original_url": "https://updated-example.com"},
        headers={"Authorization": f"Bearer {auth_token}"}
    )
    
    # Проверяем, что кэш обновился
    updated_cached_url = get_link_cache("toinvalidate")
    assert updated_cached_url == "https://updated-example.com"
    
    # Удаляем ссылку
    client.delete(
        "/links/toinvalidate",
        headers={"Authorization": f"Bearer {auth_token}"}
    )
    
    # Проверяем, что кэш очищен
    deleted_cached_url = get_link_cache("toinvalidate")
    assert deleted_cached_url is None
