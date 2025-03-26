import pytest
from fastapi.testclient import TestClient
from datetime import datetime, timedelta
from unittest.mock import patch, MagicMock
from app.main import app
from app import models, cache, auth
import json
import os

def test_create_short_link_complex_flow(client, db):
    """Тест сложного сценария создания ссылки"""
    expiry_date = (datetime.now() + timedelta(days=30)).isoformat()
    response = client.post(
        "/links/shorten",
        json={
            "original_url": "https://example.com/complex-flow",
            "custom_alias": "complex-flow",
            "expires_at": expiry_date
        }
    )
    
    assert response.status_code == 200
    data = response.json()
    assert data["short_code"] == "complex-flow"
    
    cached_url = cache.get_link_cache("complex-flow")
    assert cached_url == "https://example.com/complex-flow"
    
    redirect_response = client.get("/complex-flow", follow_redirects=False)
    assert redirect_response.status_code == 307
    assert redirect_response.headers["location"] == "https://example.com/complex-flow"
    
    db_link = db.query(models.Link).filter(models.Link.short_code == "complex-flow").first()
    assert db_link.clicks == 1
    assert db_link.last_used is not None

def test_config_environment_variables():
    """Тест переменных окружения в конфигурации"""
    from app import config
    original_testing = config.TESTING
    original_database_url = config.DATABASE_URL
    
    try:
        with patch.dict(os.environ, {"TESTING": "True"}):
            import importlib
            importlib.reload(config)
            assert config.TESTING is True
            assert config.DATABASE_URL == "sqlite:///:memory:"
        
        with patch.dict(os.environ, {
            "TESTING": "False",
            "DATABASE_URL": "postgresql://test:test@testhost/testdb"
        }):
            importlib.reload(config)
            assert config.TESTING is False
            assert config.DATABASE_URL == "postgresql://test:test@testhost/testdb"
    finally:
        config.TESTING = original_testing
        config.DATABASE_URL = original_database_url

def test_startup_event_mock():
    """Тест события запуска с использованием моков"""
    from app.main import app
    
    startup_handlers = [handler for handler in app.router.on_startup]
    
    assert len(startup_handlers) > 0

def test_simple_docs_function():
    """Тест функции simple_docs"""
    from app.simple_docs import add_custom_docs
    
    mock_app = MagicMock()
    
    add_custom_docs(mock_app)
    
    assert mock_app.docs_url is None
    
    mock_app.get.assert_called_once()
    args, kwargs = mock_app.get.call_args
    assert args[0] == "/docs"
    assert "response_class" in kwargs

def test_generate_unique_short_code_with_collision(db):
    """Тест генерации уникального кода с коллизией"""
    from app.main import generate_unique_short_code
    
    link = models.Link(
        short_code="abcdef",
        original_url="https://example.com/collision",
        is_active=True
    )
    db.add(link)
    db.commit()
    
    with patch('shortuuid.uuid', side_effect=["abcdef", "ghijkl"]):
        short_code = generate_unique_short_code(db)
        
        assert short_code == "ghijkl"
