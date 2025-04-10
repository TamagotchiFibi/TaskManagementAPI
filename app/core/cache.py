import redis
import json
from typing import Any, Optional
from app.core.config import settings, logger

redis_client = redis.Redis(
    host=settings.REDIS_HOST,
    port=settings.REDIS_PORT,
    decode_responses=True
)

def cache_data(key: str, data: Any, ttl: Optional[int] = None) -> bool:
    """Сохранение данных в кэш"""
    try:
        serialized_data = json.dumps(data)
        if ttl is None:
            ttl = settings.CACHE_TTL
        redis_client.setex(key, ttl, serialized_data)
        logger.debug(f"Data cached successfully: {key}")
        return True
    except Exception as e:
        logger.error(f"Failed to cache data: {str(e)}")
        return False

def get_cached_data(key: str) -> Optional[Any]:
    """Получение данных из кэша"""
    try:
        data = redis_client.get(key)
        if data:
            return json.loads(data)
        return None
    except Exception as e:
        logger.error(f"Failed to get cached data: {str(e)}")
        return None

def clear_cache(key: str) -> bool:
    """Очистка кэша по ключу"""
    try:
        redis_client.delete(key)
        logger.debug(f"Cache cleared successfully: {key}")
        return True
    except Exception as e:
        logger.error(f"Failed to clear cache: {str(e)}")
        return False 