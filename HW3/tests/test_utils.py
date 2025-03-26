import pytest
from datetime import datetime, timedelta
from app.main import generate_unique_short_code, parse_expiry_date, check_link_expiry
from app import models

def test_generate_unique_short_code(db):
    """Тест генерации уникального короткого кода"""

    short_code = generate_unique_short_code(db)

    assert short_code is not None
    assert len(short_code) > 0

    another_code = generate_unique_short_code(db)
    assert short_code != another_code

def test_parse_expiry_date():
    """Тест парсинга даты истечения срока"""

    assert parse_expiry_date(None) is None

    now = datetime.now()
    assert parse_expiry_date(now) == now

    date_str = "2023-12-31T23:59:59"
    parsed = parse_expiry_date(date_str)
    assert isinstance(parsed, datetime)
    assert parsed.year == 2023
    assert parsed.month == 12
    assert parsed.day == 31

    with pytest.raises(Exception):
        parse_expiry_date("invalid-date")

def test_check_link_expiry(db):
    """Тест проверки срока действия ссылки"""

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
    db.commit()
    
    assert check_link_expiry(expired_link, db) is True
    assert expired_link.is_active is False
    
    assert check_link_expiry(active_link, db) is False
    assert active_link.is_active is True
