import json
import logging
import time
from typing import Any, Optional
import redis
from app.core.config import settings

logger = logging.getLogger("eve_healthcare.cache")


class CacheService:
    """Cache service with Redis backend and in-memory fallback."""

    def __init__(self):
        self._redis_client: Optional[redis.Redis] = None
        self._memory_cache: dict[str, tuple[Any, float]] = {}
        self._is_redis_available = False

        if settings.CACHE_ENABLED:
            try:
                self._redis_client = redis.from_url(
                    settings.REDIS_URL,
                    decode_responses=True,
                    socket_connect_timeout=2
                )
                self._redis_client.ping()
                self._is_redis_available = True
                logger.info("Connected to Redis cache.")
            except Exception as e:
                logger.warning(f"Redis unavailable ({e}). Falling back to in-memory cache.")
                self._is_redis_available = False

    def get(self, key: str) -> Optional[Any]:
        """Retrieve item from cache."""
        if not settings.CACHE_ENABLED:
            return None
            
        if self._is_redis_available and self._redis_client:
            try:
                val = self._redis_client.get(key)
                if val:
                    return json.loads(val)
                return None
            except Exception as e:
                logger.warning(f"Redis get error for {key}: {e}")

        # In-memory fallback
        if key in self._memory_cache:
            data, expiry = self._memory_cache[key]
            if expiry > time.time():
                return data
            else:
                del self._memory_cache[key]
        return None

    def set(self, key: str, value: Any, ttl: Optional[int] = None) -> None:
        """Store item in cache with TTL (in seconds)."""
        if not settings.CACHE_ENABLED:
            return
            
        ttl = ttl or settings.CACHE_DEFAULT_TTL
        
        if self._is_redis_available and self._redis_client:
            try:
                self._redis_client.setex(key, ttl, json.dumps(value, default=str))
                return
            except Exception as e:
                logger.warning(f"Redis set error for {key}: {e}")

        # In-memory fallback
        self._memory_cache[key] = (value, time.time() + ttl)

    def delete(self, key: str) -> None:
        """Delete specific key."""
        if self._is_redis_available and self._redis_client:
            try:
                self._redis_client.delete(key)
            except Exception:
                pass
        self._memory_cache.pop(key, None)

    def invalidate_prefix(self, prefix: str) -> None:
        """Invalidate all keys matching prefix."""
        if self._is_redis_available and self._redis_client:
            try:
                keys = self._redis_client.keys(f"{prefix}*")
                if keys:
                    self._redis_client.delete(*keys)
            except Exception as e:
                logger.warning(f"Redis invalidate error: {e}")

        keys_to_del = [k for k in self._memory_cache if k.startswith(prefix)]
        for k in keys_to_del:
            del self._memory_cache[k]


cache = CacheService()
