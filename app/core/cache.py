import json
import time
from typing import Any

try:
    import redis
except ImportError:
    redis = None

from app.core.config import get_settings


class CacheManager:
    """Manages caching with Redis when available, falling back gracefully to in-memory TTL caching."""

    def __init__(self):
        self._memory_cache: dict[str, tuple[float, str]] = {}
        self._redis_client = None

    def _get_redis(self):
        settings = get_settings()
        if redis and getattr(settings, "redis_url", None) and self._redis_client is None:
            try:
                client = redis.from_url(settings.redis_url, decode_responses=True)
                client.ping()
                self._redis_client = client
            except Exception:
                self._redis_client = False
        return self._redis_client if self._redis_client is not False else None

    def get(self, key: str) -> Any | None:
        client = self._get_redis()
        if client:
            try:
                val = client.get(key)
                return json.loads(val) if val else None
            except Exception:
                pass

        if key in self._memory_cache:
            expires_at, val = self._memory_cache[key]
            if time.time() < expires_at:
                try:
                    return json.loads(val)
                except Exception:
                    return val
            else:
                del self._memory_cache[key]
        return None

    def set(self, key: str, value: Any, ttl_seconds: int = 60) -> None:
        payload = json.dumps(value, default=str)
        client = self._get_redis()
        if client:
            try:
                client.setex(key, ttl_seconds, payload)
                return
            except Exception:
                pass

        self._memory_cache[key] = (time.time() + ttl_seconds, payload)

    def delete(self, key: str) -> None:
        client = self._get_redis()
        if client:
            try:
                client.delete(key)
            except Exception:
                pass
        self._memory_cache.pop(key, None)

    def invalidate_all(self) -> None:
        client = self._get_redis()
        if client:
            try:
                client.flushdb()
            except Exception:
                pass
        self._memory_cache.clear()


cache_manager = CacheManager()
