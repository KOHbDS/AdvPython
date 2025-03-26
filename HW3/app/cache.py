import redis
import json
from typing import Any, Optional, Dict
from datetime import datetime
from .config import REDIS_HOST, REDIS_PORT, REDIS_DB, TESTING
import os
import logging

logger = logging.getLogger(__name__)

LINK_PREFIX = "link:"
STATS_PREFIX = "stats:"

CACHE_TTL = int(os.getenv("CACHE_TTL", "3600"))

_memory_cache: Dict[str, Any] = {}

redis_client = None
if not TESTING:
    try:
        redis_url = os.getenv("REDIS_URL")
        if redis_url:
            redis_client = redis.from_url(redis_url, decode_responses=True)
            logger.info("Connected to Redis using REDIS_URL")
        else:
            redis_client = redis.Redis(
                host=REDIS_HOST, 
                port=REDIS_PORT, 
                db=REDIS_DB, 
                decode_responses=True
            )
            logger.info(f"Connected to Redis at {REDIS_HOST}:{REDIS_PORT}")
    except Exception as e:
        logger.error(f"Redis connection error: {e}")
        redis_client = None

def set_link_cache(short_code: str, url: str) -> None:
    """Кэширование ссылки"""
    if TESTING:
        _memory_cache[f"{LINK_PREFIX}{short_code}"] = url
        return
        
    if redis_client:
        try:
            key = f"{LINK_PREFIX}{short_code}"
            redis_client.set(key, url, ex=CACHE_TTL)
        except Exception as e:
            logger.error(f"Error setting link cache: {e}")

def get_link_cache(short_code: str) -> Optional[str]:
    """Получение ссылки из кэша"""
    if TESTING:
        return _memory_cache.get(f"{LINK_PREFIX}{short_code}")
        
    if redis_client:
        try:
            key = f"{LINK_PREFIX}{short_code}"
            return redis_client.get(key)
        except Exception as e:
            logger.error(f"Error getting link from cache: {e}")
    return None

def set_stats_cache(short_code: str, stats: Dict[str, Any]) -> None:
    """Кэширование статистики ссылки"""
    if TESTING:
        _memory_cache[f"{STATS_PREFIX}{short_code}"] = json.dumps(stats)
        return
        
    if redis_client:
        try:
            key = f"{STATS_PREFIX}{short_code}"
            redis_client.set(key, json.dumps(stats), ex=CACHE_TTL)
        except Exception as e:
            logger.error(f"Error setting stats cache: {e}")

def get_stats_cache(short_code: str) -> Optional[Dict[str, Any]]:
    """Получение статистики ссылки из кэша"""
    if TESTING:
        data = _memory_cache.get(f"{STATS_PREFIX}{short_code}")
        return json.loads(data) if data else None
        
    if redis_client:
        try:
            key = f"{STATS_PREFIX}{short_code}"
            data = redis_client.get(key)
            if data:
                return json.loads(data)
        except Exception as e:
            logger.error(f"Error getting stats from cache: {e}")
    return None

def delete_link_cache(short_code: str) -> None:
    """Удаление ссылки из кэша"""
    if TESTING:
        _memory_cache.pop(f"{LINK_PREFIX}{short_code}", None)
        _memory_cache.pop(f"{STATS_PREFIX}{short_code}", None)
        return
        
    if redis_client:
        try:
            link_key = f"{LINK_PREFIX}{short_code}"
            stats_key = f"{STATS_PREFIX}{short_code}"
            redis_client.delete(link_key, stats_key)
        except Exception as e:
            logger.error(f"Error deleting from cache: {e}")

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
        try:
            stats_key = f"{STATS_PREFIX}{short_code}"
            stats = get_stats_cache(short_code)
            if stats:
                stats['clicks'] += 1
                stats['last_used'] = datetime.now().isoformat()
                set_stats_cache(short_code, stats)
        except Exception as e:
            logger.error(f"Error incrementing clicks in cache: {e}")
