import json
from typing import Any, Optional
from .base import BaseCache


class RedisCache(BaseCache):
    def __init__(self, url: str = "redis://localhost:6379"):
        try:
            import redis
            self._client = redis.from_url(url)
        except ImportError:
            raise ImportError("Install redis: pip install redis")

    def get(self, key: str) -> Optional[Any]:
        val = self._client.get(key)
        if val is None:
            return None
        return json.loads(val)

    def set(self, key: str, value: Any, ttl: int = 60):
        self._client.setex(key, ttl, json.dumps(value, default=str))

    def delete(self, key: str):
        self._client.delete(key)

    def invalidate_pattern(self, pattern: str):
        keys = self._client.keys(pattern)
        if keys:
            self._client.delete(*keys)

    def increment(self, key: str, ttl: int = 60) -> int:
        pipe = self._client.pipeline()
        pipe.incr(key)
        pipe.expire(key, ttl)
        result = pipe.execute()
        return result[0]
