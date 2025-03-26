import pytest
from datetime import datetime, timedelta
from app import models, cache, background_tasks

# Используем фикстуру auth_token из conftest.py

def test_cleanup_unused_links(client, db, auth_token):
    """Тест очистки неиспользуемых ссылок"""
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
    
    assert cache.get_link_cache("test1") == "https://example.com/1"
    assert cache.get_link_cache("test2") == "https://example.com/2"
    
    client.get("/test1")
    
    link2 = db.query(models.Link).filter(models.Link.short_code == "test2").first()
    link2.created_at = datetime.now() - timedelta(days=2)
    db.commit()
    
    response = client.post(
        "/links/cleanup?days=1",
        headers={"Authorization": f"Bearer {auth_token}"}
    )
    assert response.status_code == 200
    assert "message" in response.json()
    
    link1 = db.query(models.Link).filter(models.Link.short_code == "test1").first()
    link2 = db.query(models.Link).filter(models.Link.short_code == "test2").first()
    
    assert link1.is_active
    assert not link2.is_active
    
    assert cache.get_link_cache("test1") is not None
    assert cache.get_link_cache("test2") is None

def test_cleanup_expired_links(client, db, auth_token):
    """Тест очистки истекших ссылок"""
    expiry_date = (datetime.now() - timedelta(days=1)).isoformat()
    client.post(
        "/links/shorten",
        json={"original_url": "https://example.com", "custom_alias": "expired", "expires_at": expiry_date},
        headers={"Authorization": f"Bearer {auth_token}"}
    )
    
    client.post(
        "/links/shorten",
        json={"original_url": "https://example.com/active", "custom_alias": "active"},
        headers={"Authorization": f"Bearer {auth_token}"}
    )
    

    background_tasks.cleanup_expired_links(db)
    
    expired_link = db.query(models.Link).filter(models.Link.short_code == "expired").first()
    active_link = db.query(models.Link).filter(models.Link.short_code == "active").first()
    
    assert not expired_link.is_active
    assert active_link.is_active 
    
    expired_record = db.query(models.ExpiredLink).filter(models.ExpiredLink.short_code == "expired").first()
    assert expired_record is not None
    assert expired_record.original_url.rstrip('/') == "https://example.com"



def test_cleanup_unused_links_function(db, auth_token, client):
    """Тест функции очистки неиспользуемых ссылок напрямую"""
    client.post(
        "/links/shorten",
        json={"original_url": "https://example.com/unused", "custom_alias": "unused"},
        headers={"Authorization": f"Bearer {auth_token}"}
    )
    
    link = db.query(models.Link).filter(models.Link.short_code == "unused").first()
    link.created_at = datetime.now() - timedelta(days=100)
    db.commit()

    background_tasks.cleanup_unused_links(db, days=30)

    link = db.query(models.Link).filter(models.Link.short_code == "unused").first()
    assert not link.is_active
