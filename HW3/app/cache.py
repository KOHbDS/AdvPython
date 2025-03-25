import redis
import json
from typing import Any, Optional
from datetime import datetime
from .config import REDIS_HOST, REDIS_PORT, REDIS_DB, TESTING

# Префиксы ключей для различных типов данных
LINK_PREFIX = "link:"
STATS_PREFIX = "stats:"

# Время жизни кэша (в секундах)
CACHE_TTL = 3600  # 1 час

# Создаем клиент Redis только если не в режиме тестирования
if not TESTING:
    try:
        redis_client = redis.Redis(host=REDIS_HOST, port=REDIS_PORT, db=REDIS_DB, decode_responses=True)
    except Exception as e:
        print(f"Redis connection error: {e}")
        redis_client = None
else:
    # В тестовом режиме используем заглушку вместо Redis
    redis_client = None

# Заглушка для кэша в тестовом режиме
_memory_cache = {}

def set_link_cache(short_code: str, url: str) -> None:
    """Кэширование ссылки"""
    if TESTING:
        _memory_cache[f"{LINK_PREFIX}{short_code}"] = url
        return
        
    if redis_client:
        key = f"{LINK_PREFIX}{short_code}"
        redis_client.set(key, url, ex=CACHE_TTL)

def get_link_cache(short_code: str) -> Optional[str]:
    """Получение ссылки из кэша"""
    if TESTING:
        return _memory_cache.get(f"{LINK_PREFIX}{short_code}")
        
    if redis_client:
        key = f"{LINK_PREFIX}{short_code}"
        return redis_client.get(key)
    return None

def set_stats_cache(short_code: str, stats: dict) -> None:
    """Кэширование статистики ссылки"""
    if TESTING:
        _memory_cache[f"{STATS_PREFIX}{short_code}"] = json.dumps(stats)
        return
        
    if redis_client:
        key = f"{STATS_PREFIX}{short_code}"
        redis_client.set(key, json.dumps(stats), ex=CACHE_TTL)

def get_stats_cache(short_code: str) -> Optional[dict]:
    """Получение статистики ссылки из кэша"""
    if TESTING:
        data = _memory_cache.get(f"{STATS_PREFIX}{short_code}")
        return json.loads(data) if data else None
        
    if redis_client:
        key = f"{STATS_PREFIX}{short_code}"
        data = redis_client.get(key)
        if data:
            return json.loads(data)
    return None

def delete_link_cache(short_code: str) -> None:
    """Удаление ссылки из кэша"""
    if TESTING:
        _memory_cache.pop(f"{LINK_PREFIX}{short_code}", None)
        _memory_cache.pop(f"{STATS_PREFIX}{short_code}", None)
        return
        
    if redis_client:
        link_key = f"{LINK_PREFIX}{short_code}"
        stats_key = f"{STATS_PREFIX}{short_code}"
        redis_client.delete(link_key, stats_key)

def increment_link_clicks(short_code: str) -> None:
    """Инкремент счетчика кликов в кэше"""
    if TESTING:
        stats_key = f"{STATS_PREFIX}{short_code}"
        stats_str = _memory_cache.get(stats_key)
        if stats_str:
            stats = json.loads(stats_str)
            stats['clicks'] += 1
            stats['last_used'] = datetime.now().isoformat()
            _memory_cache[stats_key] = json.dumps(stats)
        return
        
    if redis_client:
        stats_key = f"{STATS_PREFIX}{short_code}"
        stats = get_stats_cache(short_code)
        if stats:
            stats['clicks'] += 1
            stats['last_used'] = datetime.now().isoformat()
            set_stats_cache(short_code, stats)
