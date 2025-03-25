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

def test_create_short_link(client, db, auth_token):
    # Создаем короткую ссылку
    response = client.post(
        "/links/shorten",
        json={"original_url": "https://example.com", "custom_alias": "test123"},
        headers={"Authorization": f"Bearer {auth_token}"}
    )
    assert response.status_code == 200
    data = response.json()
    assert data["short_code"] == "test123"
    assert data["original_url"] == "https://example.com"
    assert "created_at" in data

def test_create_link_duplicate_alias(client, db, auth_token):
    # Создаем первую ссылку
    client.post(
        "/links/shorten",
        json={"original_url": "https://example.com", "custom_alias": "test123"},
        headers={"Authorization": f"Bearer {auth_token}"}
    )
    
    # Пытаемся создать ссылку с тем же alias
    response = client.post(
        "/links/shorten",
        json={"original_url": "https://example.org", "custom_alias": "test123"},
        headers={"Authorization": f"Bearer {auth_token}"}
    )
    assert response.status_code == 400
    assert response.json()["detail"] == "Custom alias already in use"

def test_redirect(client, db, auth_token):
    # Создаем ссылку
    client.post(
        "/links/shorten",
        json={"original_url": "https://example.com", "custom_alias": "test123"},
        headers={"Authorization": f"Bearer {auth_token}"}
    )
    
    # Проверяем перенаправление
    response = client.get("/test123", allow_redirects=False)
    assert response.status_code == 307
    assert response.headers["location"] == "https://example.com"

def test_get_link_info(client, db, auth_token):
    # Создаем ссылку
    client.post(
        "/links/shorten",
        json={"original_url": "https://example.com", "custom_alias": "test123"},
        headers={"Authorization": f"Bearer {auth_token}"}
    )
    
    # Получаем информацию о ссылке
    response = client.get(
        "/links/test123",
        headers={"Authorization": f"Bearer {auth_token}"}
    )
    assert response.status_code == 200
    data = response.json()
    assert data["short_code"] == "test123"
    assert data["original_url"] == "https://example.com"
    assert data["clicks"] == 0

def test_update_link(client, db, auth_token):
    # Создаем ссылку
    client.post(
        "/links/shorten",
        json={"original_url": "https://example.com", "custom_alias": "test123"},
        headers={"Authorization": f"Bearer {auth_token}"}
    )
    
    # Обновляем ссылку
    response = client.put(
        "/links/test123",
        json={"original_url": "https://updated-example.com"},
        headers={"Authorization": f"Bearer {auth_token}"}
    )
    assert response.status_code == 200
    data = response.json()
    assert data["original_url"] == "https://updated-example.com"

def test_delete_link(client, db, auth_token):
    # Создаем ссылку
    client.post(
        "/links/shorten",
        json={"original_url": "https://example.com", "custom_alias": "test123"},
        headers={"Authorization": f"Bearer {auth_token}"}
    )
    
    # Удаляем ссылку
    response = client.delete(
        "/links/test123",
        headers={"Authorization": f"Bearer {auth_token}"}
    )
    assert response.status_code == 204
    
    # Проверяем, что ссылка больше не доступна
    response = client.get(
        "/links/test123",
        headers={"Authorization": f"Bearer {auth_token}"}
    )
    assert response.status_code == 404

def test_search_url(client, db, auth_token):
    # Создаем ссылку
    client.post(
        "/links/shorten",
        json={"original_url": "https://example.com", "custom_alias": "test123"},
        headers={"Authorization": f"Bearer {auth_token}"}
    )
    
    # Ищем ссылку по URL
    response = client.get(
        "/search-url?url=https://example.com",
        headers={"Authorization": f"Bearer {auth_token}"}
    )
    assert response.status_code == 200
    data = response.json()
    assert data["short_code"] == "test123"
    assert data["original_url"] == "https://example.com"

def test_expired_links(client, db, auth_token):
    # Создаем ссылку с истекающим сроком действия
    expiry_date = (datetime.now() - timedelta(days=1)).isoformat()
    client.post(
        "/links/shorten",
        json={"original_url": "https://example.com", "custom_alias": "expired", "expires_at": expiry_date},
        headers={"Authorization": f"Bearer {auth_token}"}
    )
    
    # Получаем список истекших ссылок
    response = client.get(
        "/expired-links",
        headers={"Authorization": f"Bearer {auth_token}"}
    )
    assert response.status_code == 200
    data = response.json()
    assert len(data) > 0
    assert any(link["short_code"] == "expired" for link in data)

def test_link_caching(client, db, auth_token):
    # Создаем ссылку
    client.post(
        "/links/shorten",
        json={"original_url": "https://example.com", "custom_alias": "cached"},
        headers={"Authorization": f"Bearer {auth_token}"}
    )
    
    # Первый запрос должен сохранить ссылку в кэше
    response1 = client.get("/cached", allow_redirects=False)
    assert response1.status_code == 307
    
    # Проверяем, что кэш работает (используем прямой доступ к кэшу для теста)
    from app.cache import get_link_cache
    cached_url = get_link_cache("cached")
    assert cached_url == "https://example.com"
    
    # Проверяем, что счетчик кликов увеличился
    link = db.query(models.Link).filter(models.Link.short_code == "cached").first()
    assert link.clicks == 1
    
    # Второй запрос должен использовать кэш
    response2 = client.get("/cached", allow_redirects=False)
    assert response2.status_code == 307
    
    # Проверяем, что счетчик кликов снова увеличился
    db.refresh(link)
    assert link.clicks == 2
