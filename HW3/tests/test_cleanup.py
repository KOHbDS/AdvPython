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

def test_cleanup_unused_links(client, db, auth_token):
    # Создаем несколько ссылок
    client.post(
        "/links/shorten",
        json={"original_url": "https://example.com/1", "custom_alias": "test1"},
        headers={"Authorization": f"Bearer {auth_token}"}
    )
    client.post(
        "/links/shorten",
        json={"original_url": "https://example.com/2", "custom_alias": "test2"},
        headers={"Authorization": f"Bearer {auth_token}"}
    )
    
    # Используем одну из ссылок, чтобы обновить last_used
    client.get("/test1")
    
    # Изменяем дату создания второй ссылки, чтобы она считалась старой
    link2 = db.query(models.Link).filter(models.Link.short_code == "test2").first()
    link2.created_at = datetime.now() - timedelta(days=2)
    db.commit()
    
    # Запускаем очистку неиспользуемых ссылок (с небольшим значением days)
    response = client.post(
        "/links/cleanup?days=1",
        headers={"Authorization": f"Bearer {auth_token}"}
    )
    assert response.status_code == 200
    
    # Проверяем, что неиспользуемая ссылка деактивирована
    link1 = db.query(models.Link).filter(models.Link.short_code == "test1").first()
    link2 = db.query(models.Link).filter(models.Link.short_code == "test2").first()
    
    assert link1.is_active  # Эта ссылка должна остаться активной, т.к. использовалась
    assert not link2.is_active  # Эта ссылка должна быть деактивирована

def test_cleanup_expired_links(client, db, auth_token):
    # Создаем ссылку с истекшим сроком действия
    expiry_date = (datetime.now() - timedelta(days=1)).isoformat()
    client.post(
        "/links/shorten",
        json={"original_url": "https://example.com", "custom_alias": "expired", "expires_at": expiry_date},
        headers={"Authorization": f"Bearer {auth_token}"}
    )
    
    # Создаем активную ссылку
    client.post(
        "/links/shorten",
        json={"original_url": "https://example.com/active", "custom_alias": "active"},
        headers={"Authorization": f"Bearer {auth_token}"}
    )
    
    # Явно вызываем функцию очистки
    from app.background_tasks import cleanup_expired_links
    cleanup_expired_links(db)
    
    # Проверяем, что истекшая ссылка деактивирована
    expired_link = db.query(models.Link).filter(models.Link.short_code == "expired").first()
    active_link = db.query(models.Link).filter(models.Link.short_code == "active").first()
    
    assert not expired_link.is_active  # Эта ссылка должна быть деактивирована
    assert active_link.is_active  # Эта ссылка должна остаться активной
    
    # Проверяем, что запись добавлена в таблицу истекших ссылок
    expired_record = db.query(models.ExpiredLink).filter(models.ExpiredLink.short_code == "expired").first()
    assert expired_record is not None
    assert expired_record.original_url == "https://example.com"
