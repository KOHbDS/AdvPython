import pytest
from datetime import datetime, timedelta
from unittest.mock import patch, MagicMock, call
import os
from app import background_tasks, models, cache

def test_cleanup_expired_links(db):
    """Тест очистки истекших ссылок"""
    expired_link = models.Link(
        short_code="expired_bg",
        original_url="https://example.com/expired",
        expires_at=datetime.now() - timedelta(days=1),
        is_active=True,
        owner_id=1
    )
    db.add(expired_link)
    
    active_link = models.Link(
        short_code="active_bg",
        original_url="https://example.com/active",
        expires_at=datetime.now() + timedelta(days=1),
        is_active=True,
        owner_id=1
    )
    db.add(active_link)
    
    no_expiry_link = models.Link(
        short_code="no_expiry_bg",
        original_url="https://example.com/no_expiry",
        expires_at=None,
        is_active=True,
        owner_id=1
    )
    db.add(no_expiry_link)
    
    db.commit()
    
    background_tasks.cleanup_expired_links(db)
    
    expired_link = db.query(models.Link).filter(models.Link.short_code == "expired_bg").first()
    active_link = db.query(models.Link).filter(models.Link.short_code == "active_bg").first()
    no_expiry_link = db.query(models.Link).filter(models.Link.short_code == "no_expiry_bg").first()
    
    assert expired_link.is_active is False
    assert active_link.is_active is True
    assert no_expiry_link.is_active is True
    
    expired_record = db.query(models.ExpiredLink).filter(models.ExpiredLink.short_code == "expired_bg").first()
    assert expired_record is not None
    assert expired_record.original_url == "https://example.com/expired"
    assert expired_record.owner_id == 1

def test_cleanup_expired_links_error_handling():
    """Тест обработки ошибок при очистке истекших ссылок"""
    mock_db = MagicMock()
    
    mock_expired_link = MagicMock()
    mock_expired_link.short_code = "test_error"
    mock_expired_link.original_url = "https://example.com/error"
    mock_expired_link.created_at = datetime.now() - timedelta(days=10)
    mock_expired_link.expires_at = datetime.now() - timedelta(days=1)
    mock_expired_link.is_active = True
    mock_expired_link.clicks = 5
    mock_expired_link.owner_id = 1
    
    mock_query = MagicMock()
    mock_query.filter.return_value.all.return_value = [mock_expired_link]
    mock_db.query.return_value = mock_query
    mock_db.commit.side_effect = Exception("Test error")
    
    mock_expired_record = MagicMock()
    mock_db.add.return_value = None

    background_tasks.cleanup_expired_links(mock_db)
    
    mock_db.add.assert_called_once()

    mock_db.commit.assert_called_once()

    mock_db.rollback.assert_called_once()

def test_cleanup_unused_links(db):
    """Тест очистки неиспользуемых ссылок"""
    old_link = models.Link(
        short_code="old_unused",
        original_url="https://example.com/old",
        created_at=datetime.now() - timedelta(days=100),
        last_used=None,
        is_active=True,
        owner_id=1
    )
    db.add(old_link)
    
    used_link = models.Link(
        short_code="old_used",
        original_url="https://example.com/used",
        created_at=datetime.now() - timedelta(days=100),
        last_used=datetime.now() - timedelta(days=1),
        is_active=True,
        owner_id=1
    )
    db.add(used_link)
    
    new_link = models.Link(
        short_code="new_unused",
        original_url="https://example.com/new",
        created_at=datetime.now() - timedelta(days=1),
        last_used=None,
        is_active=True,
        owner_id=1
    )
    db.add(new_link)
    
    db.commit()
    
    background_tasks.cleanup_unused_links(db, days=30)
    
    old_link = db.query(models.Link).filter(models.Link.short_code == "old_unused").first()
    used_link = db.query(models.Link).filter(models.Link.short_code == "old_used").first()
    new_link = db.query(models.Link).filter(models.Link.short_code == "new_unused").first()
    
    assert old_link.is_active is False
    assert used_link.is_active is True
    assert new_link.is_active is True

def test_cleanup_unused_links_error_handling():
    """Тест обработки ошибок при очистке неиспользуемых ссылок"""
    mock_db = MagicMock()
    
    mock_old_link = MagicMock()
    mock_old_link.short_code = "old_error"
    mock_old_link.is_active = True
    
    mock_query = MagicMock()
    mock_query.filter.return_value.all.return_value = [mock_old_link]
    mock_db.query.return_value = mock_query
    mock_db.commit.side_effect = Exception("Test error")
    
    background_tasks.cleanup_unused_links(mock_db, days=30)
    
    mock_db.commit.assert_called_once()
    
    mock_db.rollback.assert_called_once()

def test_default_unused_days():
    """Тест значения по умолчанию для неиспользуемых дней"""
    assert background_tasks.DEFAULT_UNUSED_DAYS > 0
    
    original_value = background_tasks.DEFAULT_UNUSED_DAYS
    
    try:
        with patch.dict(os.environ, {"DEFAULT_UNUSED_DAYS": "45"}):
            import importlib
            importlib.reload(background_tasks)
            assert background_tasks.DEFAULT_UNUSED_DAYS == 45
    finally:
        background_tasks.DEFAULT_UNUSED_DAYS = original_value
