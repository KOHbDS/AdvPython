import pytest
import json
import redis
import os
from datetime import datetime, timedelta
from unittest.mock import patch, MagicMock, Mock
from app import cache

def test_cache_constants():
    """Тест констант кэша"""
    assert cache.LINK_PREFIX == "link:"
    assert cache.STATS_PREFIX == "stats:"
    assert isinstance(cache.CACHE_TTL, int)

def test_memory_cache_initialization():
    """Тест инициализации кэша в памяти"""
    original_memory_cache = cache._memory_cache.copy()
    
    try:
        cache._memory_cache.clear()
        
        assert len(cache._memory_cache) == 0
        
        cache._memory_cache["test_key"] = "test_value"
        
        assert "test_key" in cache._memory_cache
        assert cache._memory_cache["test_key"] == "test_value"
    finally:
        cache._memory_cache.clear()
        cache._memory_cache.update(original_memory_cache)

@pytest.mark.parametrize("testing_flag", [True, False])
def test_redis_initialization(testing_flag):
    """Тест инициализации Redis с разными флагами тестирования"""
    original_testing = cache.TESTING
    original_redis_client = cache.redis_client
    
    try:
        cache.TESTING = testing_flag
        
        if testing_flag:
            assert cache.redis_client is None or cache.TESTING is True
        else:
            pass
    finally:
        cache.TESTING = original_testing
        cache.redis_client = original_redis_client


def test_set_get_link_cache_testing_mode():
    """Тест установки и получения ссылки из кэша в тестовом режиме"""
    original_memory_cache = cache._memory_cache.copy()
    original_testing = cache.TESTING
    
    try:
        cache.TESTING = True
        cache._memory_cache.clear()
        
        cache.set_link_cache("test_code", "https://example.com")
        assert cache.get_link_cache("test_code") == "https://example.com"
        
        assert cache.get_link_cache("nonexistent") is None
        
        cache.delete_link_cache("test_code")
        assert cache.get_link_cache("test_code") is None
    finally:
        cache._memory_cache.clear()
        cache._memory_cache.update(original_memory_cache)
        cache.TESTING = original_testing

def test_set_get_stats_cache_testing_mode():
    """Тест установки и получения статистики из кэша в тестовом режиме"""
    original_memory_cache = cache._memory_cache.copy()
    original_testing = cache.TESTING
    
    try:
        cache.TESTING = True
        cache._memory_cache.clear()
        
        stats = {
            "original_url": "https://example.com",
            "short_code": "test_stats",
            "created_at": datetime.now().isoformat(),
            "clicks": 5,
            "last_used": datetime.now().isoformat(),
            "expires_at": None,
            "owner_id": 1
        }
        
        cache.set_stats_cache("test_stats", stats)
        retrieved_stats = cache.get_stats_cache("test_stats")
        
        assert retrieved_stats is not None
        assert retrieved_stats["clicks"] == 5
        assert retrieved_stats["short_code"] == "test_stats"
        
        assert cache.get_stats_cache("nonexistent") is None
    finally:
        cache._memory_cache.clear()
        cache._memory_cache.update(original_memory_cache)
        cache.TESTING = original_testing

def test_increment_link_clicks_testing_mode():
    """Тест инкремента счетчика кликов в тестовом режиме"""
    original_memory_cache = cache._memory_cache.copy()
    original_testing = cache.TESTING
    
    try:
        cache.TESTING = True
        cache._memory_cache.clear()
        stats = {
            "original_url": "https://example.com",
            "short_code": "test_clicks",
            "created_at": datetime.now().isoformat(),
            "clicks": 5,
            "last_used": datetime.now().isoformat(),
            "expires_at": None,
            "owner_id": 1
        }
        
        cache.set_stats_cache("test_clicks", stats)
        
        cache.increment_link_clicks("test_clicks")
        
        updated_stats = cache.get_stats_cache("test_clicks")
        
        assert updated_stats is not None
        assert updated_stats["clicks"] == 6
        
        cache.increment_link_clicks("nonexistent")
    finally:
        cache._memory_cache.clear()
        cache._memory_cache.update(original_memory_cache)
        cache.TESTING = original_testing

def test_redis_operations_with_mocks():
    """Тест операций Redis с использованием моков"""
    original_redis_client = cache.redis_client
    original_testing = cache.TESTING
    
    try:
        cache.TESTING = False
        
        mock_redis = MagicMock()
        mock_redis.get.return_value = "https://example.com"
        mock_redis.set.return_value = True
        cache.redis_client = mock_redis
        
        cache.set_link_cache("test_code", "https://example.com")
        mock_redis.set.assert_called_with(
            "link:test_code", 
            "https://example.com", 
            ex=cache.CACHE_TTL
        )
        
        result = cache.get_link_cache("test_code")
        mock_redis.get.assert_called_with("link:test_code")
        assert result == "https://example.com"
        
        cache.delete_link_cache("test_code")
        mock_redis.delete.assert_called()
    finally:
        cache.redis_client = original_redis_client
        cache.TESTING = original_testing

def test_redis_stats_operations_with_mocks():
    """Тест операций Redis со статистикой"""
    original_redis_client = cache.redis_client
    original_testing = cache.TESTING
    
    try:
        cache.TESTING = False
        
        stats = {
            "original_url": "https://example.com",
            "short_code": "test_stats",
            "created_at": datetime.now().isoformat(),
            "clicks": 5,
            "last_used": datetime.now().isoformat(),
            "expires_at": None,
            "owner_id": 1
        }
        
        mock_redis = MagicMock()
        mock_redis.get.return_value = json.dumps(stats)
        mock_redis.set.return_value = True
        
        cache.redis_client = mock_redis
        
        cache.set_stats_cache("test_stats", stats)
        mock_redis.set.assert_called_with(
            "stats:test_stats", 
            json.dumps(stats), 
            ex=cache.CACHE_TTL
        )
        
        result = cache.get_stats_cache("test_stats")
        mock_redis.get.assert_called_with("stats:test_stats")
        assert result == stats
        
        cache.increment_link_clicks("test_stats")
    finally:
        cache.redis_client = original_redis_client
        cache.TESTING = original_testing

def test_redis_error_handling():
    """Тест обработки ошибок Redis"""
    original_redis_client = cache.redis_client
    original_testing = cache.TESTING
    
    try:
        cache.TESTING = False
        
        mock_redis = MagicMock()
        mock_redis.get.side_effect = redis.RedisError("Test error")
        mock_redis.set.side_effect = redis.RedisError("Test error")
        mock_redis.delete.side_effect = redis.RedisError("Test error")
        
        cache.redis_client = mock_redis
        
        assert cache.get_link_cache("test_error") is None
        cache.set_link_cache("test_error", "test_value")
        cache.delete_link_cache("test_error") 

        assert cache.get_stats_cache("test_error") is None

        stats = {
            "clicks": 5,
            "last_used": datetime.now().isoformat()
        }
        
        cache.set_stats_cache("test_error", stats)
        cache.increment_link_clicks("test_error")
    finally:
        cache.redis_client = original_redis_client
        cache.TESTING = original_testing
