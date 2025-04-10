import redis
from app.core.config import settings
import json
from typing import Any, Optional
import logging
from datetime import datetime
import fnmatch

logger = logging.getLogger(__name__)

class DateTimeEncoder(json.JSONEncoder):
    """Кастомный JSON энкодер для datetime"""
    def default(self, obj):
        if isinstance(obj, datetime):
            return obj.isoformat()
        return super().default(obj)

# Фиктивный Redis клиент для тестов
class MockRedis:
    """Мок-класс для Redis в тестовом окружении"""
    
    def __init__(self):
        self._data = {}
        self._expires = {}
    
    def get(self, key: str) -> str:
        """Получает значение по ключу"""
        if key in self._expires and self._expires[key] < datetime.now().timestamp():
            del self._data[key]
            del self._expires[key]
            return None
        return self._data.get(key)
    
    def set(self, key: str, value: str, ex: int = None) -> bool:
        """Устанавливает значение по ключу с опциональным временем жизни"""
        self._data[key] = value
        if ex:
            self.expire(key, ex)
        return True
    
    def setex(self, key: str, time: int, value: str) -> bool:
        """Устанавливает значение по ключу с временем жизни"""
        self._data[key] = value
        self.expire(key, time)
        return True
    
    def delete(self, key: str) -> bool:
        """Удаляет значение по ключу"""
        if key in self._data:
            del self._data[key]
            if key in self._expires:
                del self._expires[key]
            return True
        return False
    
    def incr(self, key: str) -> int:
        """Увеличивает значение по ключу на 1"""
        current = int(self._data.get(key, 0))
        self._data[key] = str(current + 1)
        return current + 1
    
    def expire(self, key: str, time: int) -> bool:
        """Устанавливает время жизни ключа в секундах"""
        if key in self._data:
            self._expires[key] = datetime.now().timestamp() + time
            return True
        return False
    
    def ttl(self, key: str) -> int:
        """Возвращает оставшееся время жизни ключа в секундах"""
        if key not in self._data:
            return -2
        if key not in self._expires:
            return -1
        ttl = self._expires[key] - datetime.now().timestamp()
        return max(1, int(ttl))  # Возвращаем минимум 1 секунду для существующих ключей
    
    def keys(self, pattern: str = "*") -> list:
        """Возвращает список ключей, соответствующих шаблону"""
        self._clean_expired()
        return [k for k in self._data.keys() if fnmatch.fnmatch(k, pattern)]
    
    def flushall(self) -> bool:
        """Очищает все данные"""
        self._data.clear()
        self._expires.clear()
        return True
    
    def _clean_expired(self):
        """Очищает истекшие ключи"""
        now = datetime.now().timestamp()
        expired = [k for k, t in self._expires.items() if t < now]
        for key in expired:
            del self._data[key]
            del self._expires[key]

# Создание экземпляра MockRedis для тестов
mock_redis = MockRedis()

def get_redis_client():
    """Возвращает клиент Redis или мок для тестов"""
    if settings.TESTING:
        return mock_redis
    return redis.from_url(settings.REDIS_URL)

def cache_data(key: str, data: Any, ttl: Optional[int] = None) -> None:
    """
    Кэширование данных в Redis
    """
    try:
        if ttl is None:
            ttl = settings.CACHE_TTL
        redis_client = get_redis_client()
        redis_client.setex(
            key,
            ttl,
            json.dumps(data, cls=DateTimeEncoder)
        )
    except Exception as e:
        logger.error(f"Error caching data: {e}")

def get_cached_data(key: str) -> Optional[Any]:
    """
    Получение данных из кэша
    """
    try:
        redis_client = get_redis_client()
        data = redis_client.get(key)
        if data:
            return json.loads(data)
        return None
    except Exception as e:
        logger.error(f"Error getting cached data: {e}")
        return None

def clear_cache(key_pattern: str = None):
    """Очищает кэш по шаблону ключа или весь кэш"""
    redis_client = get_redis_client()
    if key_pattern:
        # В реальном Redis можно использовать SCAN, но для простоты используем keys
        keys = redis_client.keys(key_pattern)
        for key in keys:
            redis_client.delete(key)
    else:
        redis_client.flushall()

def clear_cache_pattern(pattern: str) -> None:
    """
    Очистка кэша по шаблону
    """
    try:
        redis_client = get_redis_client()
        keys = redis_client.keys(pattern)
        if keys:
            redis_client.delete(*keys)
    except Exception as e:
        logger.error(f"Error clearing cache pattern: {e}") 