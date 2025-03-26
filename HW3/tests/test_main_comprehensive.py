# tests/test_main_comprehensive.py
import pytest
from fastapi.testclient import TestClient
from datetime import datetime, timedelta
from unittest.mock import patch, MagicMock
from app.main import app, generate_unique_short_code, parse_expiry_date, check_link_expiry
from app import models, cache


def test_parse_expiry_date_comprehensive():
    """Детальный тест парсинга даты истечения срока"""
    assert parse_expiry_date(None) is None
    
    now = datetime.now()
    assert parse_expiry_date(now) == now
    
    date_str = "2023-12-31T23:59:59"
    parsed = parse_expiry_date(date_str)
    assert isinstance(parsed, datetime)
    assert parsed.year == 2023
    assert parsed.month == 12
    assert parsed.day == 31
    
    date_str = "2023-12-31T23:59:59Z"
    parsed = parse_expiry_date(date_str)
    assert isinstance(parsed, datetime)
    assert parsed.year == 2023
    
    with pytest.raises(Exception):
        parse_expiry_date("invalid-date-format")

def test_check_link_expiry_comprehensive(db):
    """Детальный тест проверки срока действия ссылки"""
    expired_link = models.Link(
        short_code="test_expired",
        original_url="https://example.com",
        expires_at=datetime.now() - timedelta(days=1),
        is_active=True
    )
    db.add(expired_link)
    
    active_link = models.Link(
        short_code="test_active",
        original_url="https://example.com",
        expires_at=datetime.now() + timedelta(days=1),
        is_active=True
    )
    db.add(active_link)
    
    no_expiry_link = models.Link(
        short_code="test_no_expiry",
        original_url="https://example.com",
        expires_at=None,
        is_active=True
    )
    db.add(no_expiry_link)
    
    inactive_link = models.Link(
        short_code="test_inactive",
        original_url="https://example.com",
        expires_at=datetime.now() - timedelta(days=1),
        is_active=False
    )
    db.add(inactive_link)
    
    db.commit()
    
    assert check_link_expiry(expired_link, db) is True
    assert expired_link.is_active is False
    
    assert check_link_expiry(active_link, db) is False
    assert active_link.is_active is True
    
    assert check_link_expiry(no_expiry_link, db) is False
    assert no_expiry_link.is_active is True
    
    assert check_link_expiry(inactive_link, db) is False
    assert inactive_link.is_active is False

def test_generate_unique_short_code_comprehensive(db):
    """Детальный тест генерации уникального короткого кода"""
    short_code = generate_unique_short_code(db)
    
    assert short_code is not None
    assert len(short_code) > 0

    link = models.Link(
        short_code=short_code,
        original_url="https://example.com"
    )
    db.add(link)
    db.commit()
    another_code = generate_unique_short_code(db)
    assert short_code != another_code

    assert db.query(models.Link).filter(models.Link.short_code == another_code).first() is None

def test_create_short_link_with_expiry(client, db, auth_token):
    """Тест создания короткой ссылки с датой истечения срока"""
    expiry_date = (datetime.now() + timedelta(days=1)).isoformat()
    response = client.post(
        "/links/shorten",
        json={"original_url": "https://example.com/expiry-test", "expires_at": expiry_date},
        headers={"Authorization": f"Bearer {auth_token}"}
    )
    
    assert response.status_code == 200
    data = response.json()
    assert "short_code" in data

    short_code = data["short_code"]
    db_link = db.query(models.Link).filter(models.Link.short_code == short_code).first()
    assert db_link is not None
    assert db_link.expires_at is not None

def test_redirect_expired_link(client, db, auth_token):
    """Тест перенаправления по истекшей ссылке"""
    expiry_date = (datetime.now() - timedelta(days=1)).isoformat()
    response = client.post(
        "/links/shorten",
        json={"original_url": "https://example.com/expired", "custom_alias": "expired-test", "expires_at": expiry_date},
        headers={"Authorization": f"Bearer {auth_token}"}
    )
    
    assert response.status_code == 200
    
    response = client.get("/expired-test", follow_redirects=False)
    assert response.status_code == 404

    db_link = db.query(models.Link).filter(models.Link.short_code == "expired-test").first()
    assert db_link is not None
    assert db_link.is_active is False

def test_health_check_detailed(client):
    """Детальный тест эндпоинта проверки здоровья"""
    response = client.get("/healthz")
    assert response.status_code == 200
    data = response.json()
    
    assert "status" in data
    assert "database" in data
    assert "redis" in data
    
    if data["database"] == "healthy" and data["redis"] == "healthy":
        assert data["status"] == "healthy"


def test_search_by_url_not_found(client, db, auth_token):
    """Тест поиска несуществующей ссылки по URL"""
    response = client.get(
        "/links/search?original_url=https://nonexistent.com",
        headers={"Authorization": f"Bearer {auth_token}"}
    )
    
    assert response.status_code == 404
    assert response.json()["detail"] == "Link not found"

def test_get_link_info_not_found(client, db):
    """Тест получения информации о несуществующей ссылке"""
    response = client.get("/links/nonexistent")
    
    assert response.status_code == 404
    assert response.json()["detail"] == "Link not found"

def test_update_link_not_found(client, db, auth_token):
    """Тест обновления несуществующей ссылки"""
    response = client.put(
        "/links/nonexistent",
        json={"original_url": "https://updated.com"},
        headers={"Authorization": f"Bearer {auth_token}"}
    )
    
    assert response.status_code == 404
    assert "detail" in response.json()
    assert response.json()["detail"] == "Link not found"
