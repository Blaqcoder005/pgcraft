from .cache.base import BaseCache


class RateLimiter:
    def __init__(self, cache: BaseCache):
        self._cache = cache

    def check(
        self,
        key: str,
        limit: int = 100,
        window: int = 60,
    ) -> dict:
        cache_key = f"rl:{key}"
        count = self._cache.increment(cache_key, ttl=window)

        return {
            "allowed": count <= limit,
            "count": count,
            "limit": limit,
            "remaining": max(0, limit - count),
        }

    def reset(self, key: str):
        self._cache.delete(f"rl:{key}")
