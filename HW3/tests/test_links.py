import pytest
from datetime import datetime, timedelta
from app import models, cache

# Используем фикстуру auth_token из conftest.py

# Исправьте тест test_create_short_link
def test_create_short_link(client, db, auth_token):
    """Тест создания короткой ссылки с кастомным алиасом"""
    response = client.post(
        "/links/shorten",
        json={"original_url": "https://example.com", "custom_alias": "test123"},
        headers={"Authorization": f"Bearer {auth_token}"}
    )
    assert response.status_code == 200
    data = response.json()
    assert data["short_code"] == "test123"
    # Проверяем URL без учета завершающего слеша
    assert data["original_url"].rstrip('/') == "https://example.com"
    
    # Проверяем, что ссылка создана в базе
    db_link = db.query(models.Link).filter(models.Link.short_code == "test123").first()
    assert db_link is not None
    assert db_link.original_url.rstrip('/') == "https://example.com"


def test_create_short_link_without_alias(client, db, auth_token):
    """Тест создания короткой ссылки без кастомного алиаса"""
    response = client.post(
        "/links/shorten",
        json={"original_url": "https://example.com/no-alias"},
        headers={"Authorization": f"Bearer {auth_token}"}
    )
    assert response.status_code == 200
    data = response.json()
    assert "short_code" in data
    assert data["original_url"] == "https://example.com/no-alias"
    
    # Проверяем, что ссылка создана в базе
    short_code = data["short_code"]
    db_link = db.query(models.Link).filter(models.Link.short_code == short_code).first()
    assert db_link is not None

def test_create_short_link_with_expiry(client, db, auth_token):
    """Тест создания короткой ссылки с датой истечения срока"""
    expiry_date = (datetime.now() + timedelta(days=1)).isoformat()
    response = client.post(
        "/links/shorten",
        json={"original_url": "https://example.com/expiry", "custom_alias": "expiry", "expires_at": expiry_date},
        headers={"Authorization": f"Bearer {auth_token}"}
    )
    assert response.status_code == 200
    data = response.json()
    assert data["short_code"] == "expiry"
    
    # Проверяем, что срок действия установлен в базе
    db_link = db.query(models.Link).filter(models.Link.short_code == "expiry").first()
    assert db_link is not None
    assert db_link.expires_at is not None

def test_create_link_duplicate_alias(client, db, auth_token):
    """Тест создания ссылки с существующим алиасом"""
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

def test_get_link_info(client, db, auth_token):
    """Тест получения информации о ссылке"""
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
    # Используем rstrip для удаления слеша в конце URL
    assert data["original_url"].rstrip('/') == "https://example.com"

def test_get_link_stats(client, db, auth_token):
    """Тест получения статистики по ссылке"""
    # Создаем ссылку
    client.post(
        "/links/shorten",
        json={"original_url": "https://example.com", "custom_alias": "stats"},
        headers={"Authorization": f"Bearer {auth_token}"}
    )
    
    # Делаем переход по ссылке
    client.get("/stats")
    
    # Получаем статистику
    response = client.get(
        "/links/stats/stats",
        headers={"Authorization": f"Bearer {auth_token}"}
    )
    assert response.status_code == 200
    data = response.json()
    assert data["clicks"] == 1
    assert data["last_used"] is not None

def test_update_link(client, db, auth_token):
    """Тест обновления ссылки"""
    # Создаем ссылку
    client.post(
        "/links/shorten",
        json={"original_url": "https://example.com", "custom_alias": "update"},
        headers={"Authorization": f"Bearer {auth_token}"}
    )
    
    # Обновляем ссылку
    response = client.put(
        "/links/update",
        json={"original_url": "https://updated-example.com"},
        headers={"Authorization": f"Bearer {auth_token}"}
    )
    assert response.status_code == 200
    data = response.json()
    # Используем rstrip для удаления слеша в конце URL
    assert data["original_url"].rstrip('/') == "https://updated-example.com"
    
    # Проверяем, что ссылка обновлена в базе
    db_link = db.query(models.Link).filter(models.Link.short_code == "update").first()
    assert db_link.original_url.rstrip('/') == "https://updated-example.com"

def test_update_link_custom_alias(client, db, auth_token):
    """Тест обновления алиаса ссылки"""
    # Создаем ссылку
    client.post(
        "/links/shorten",
        json={"original_url": "https://example.com", "custom_alias": "old-alias"},
        headers={"Authorization": f"Bearer {auth_token}"}
    )
    
    # Обновляем алиас
    response = client.put(
        "/links/old-alias",
        json={"custom_alias": "new-alias"},
        headers={"Authorization": f"Bearer {auth_token}"}
    )
    assert response.status_code == 200
    data = response.json()
    assert data["short_code"] == "new-alias"
    
    # Проверяем, что старый алиас больше не работает
    old_link = db.query(models.Link).filter(models.Link.short_code == "old-alias").first()
    assert old_link is None
    
    # Проверяем, что новый алиас работает
    new_link = db.query(models.Link).filter(models.Link.short_code == "new-alias").first()
    assert new_link is not None

def test_delete_link(client, db, auth_token):
    """Тест удаления ссылки"""
    # Создаем ссылку
    client.post(
        "/links/shorten",
        json={"original_url": "https://example.com", "custom_alias": "delete-me"},
        headers={"Authorization": f"Bearer {auth_token}"}
    )
    
    # Удаляем ссылку
    response = client.delete(
        "/links/delete-me",
        headers={"Authorization": f"Bearer {auth_token}"}
    )
    assert response.status_code == 204
    
    # Проверяем, что ссылка деактивирована в базе
    db_link = db.query(models.Link).filter(models.Link.short_code == "delete-me").first()
    assert db_link is not None
    assert db_link.is_active == False
    
    # Проверяем, что ссылка удалена из кэша
    cached_url = cache.get_link_cache("delete-me")
    assert cached_url is None

def test_redirect(client, db, auth_token):
    """Тест перенаправления по короткой ссылке"""
    # Создаем ссылку
    client.post(
        "/links/shorten",
        json={"original_url": "https://example.com", "custom_alias": "redirect"},
        headers={"Authorization": f"Bearer {auth_token}"}
    )
    
    # Делаем запрос на перенаправление
    response = client.get("/redirect", allow_redirects=False)
    assert response.status_code == 307
    # Используем rstrip для удаления слеша в конце URL
    assert response.headers["location"].rstrip('/') == "https://example.com"
    
    # Проверяем, что счетчик кликов увеличился
    db_link = db.query(models.Link).filter(models.Link.short_code == "redirect").first()
    assert db_link.clicks == 1
    assert db_link.last_used is not None

def test_search_by_url(client, db, auth_token):
    """Тест поиска ссылки по оригинальному URL"""
    # Создаем ссылку
    client.post(
        "/links/shorten",
        json={"original_url": "https://searchme.com", "custom_alias": "search"},
        headers={"Authorization": f"Bearer {auth_token}"}
    )
    
    # Получаем URL с добавленным слешем
    db_link = db.query(models.Link).filter(models.Link.short_code == "search").first()
    actual_url = db_link.original_url
    
    # Ищем ссылку по URL с учетом возможного слеша
    response = client.get(
        f"/links/search?original_url={actual_url}",
        headers={"Authorization": f"Bearer {auth_token}"}
    )
    assert response.status_code == 200
    data = response.json()
    assert data["short_code"] == "search"


def test_expired_links(client, db, auth_token):
    """Тест получения списка истекших ссылок"""
    # Создаем ссылку с истекшим сроком действия
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
