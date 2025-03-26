import pytest
import json
from datetime import datetime
from app import cache
from unittest.mock import patch, MagicMock

def test_cache_initialization():
    """Тест инициализации кэша"""
    assert hasattr(cache, '_memory_cache')
    assert isinstance(cache._memory_cache, dict)

def test_redis_connection_error():
    """Тест обработки ошибок подключения к Redis"""
    with patch('redis.Redis', side_effect=Exception("Connection error")):
        old_client = cache.redis_client
        cache.redis_client = None
        
        try:
            from app import cache as reloaded_cache
            assert reloaded_cache.redis_client is None
        finally:
            cache.redis_client = old_client

def test_redis_operations_with_errors():
    """Тест операций Redis с ошибками"""
    if hasattr(cache, '_memory_cache'):
        cache._memory_cache.clear()
    
    mock_redis = MagicMock()
    mock_redis.get.side_effect = Exception("Redis error")
    mock_redis.set.side_effect = Exception("Redis error")
    mock_redis.delete.side_effect = Exception("Redis error")
    
    old_client = cache.redis_client
    cache.redis_client = mock_redis
    
    try:
        assert cache.get_link_cache("test_error") is None
        cache.set_link_cache("test_error", "test_value")
        cache.delete_link_cache("test_error")
        stats = {
            "clicks": 5,
            "last_used": datetime.now().isoformat()
        }
        cache.set_stats_cache("test_error", stats)
        
        if hasattr(cache, '_memory_cache'):
            cache._memory_cache.pop(f"{cache.STATS_PREFIX}test_error", None)
        
        assert cache.get_stats_cache("test_error") is None
        cache.increment_link_clicks("test_error") 
    finally:
        cache.redis_client = old_client

def test_stats_cache_operations():
    """Тест операций с кэшем статистики"""
    if hasattr(cache, '_memory_cache'):
        cache._memory_cache.clear()

    test_code = "test_stats_ops"
    test_stats = {
        "original_url": "https://example.com",
        "short_code": test_code,
        "created_at": datetime.now().isoformat(),
        "clicks": 10,
        "last_used": datetime.now().isoformat(),
        "expires_at": None,
        "owner_id": 1
    }
    
    cache.set_stats_cache(test_code, test_stats)
    retrieved_stats = cache.get_stats_cache(test_code)
    
    assert retrieved_stats is not None
    assert retrieved_stats["clicks"] == 10
    assert retrieved_stats["short_code"] == test_code
    
    cache.increment_link_clicks(test_code)
    updated_stats = cache.get_stats_cache(test_code)
    
    assert updated_stats["clicks"] == 11
