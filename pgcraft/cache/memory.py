import time
import fnmatch
from typing import Any, Optional
from .base import BaseCache


class MemoryCache(BaseCache):
    def __init__(self):
        self._store: dict = {}  # key → (value, expires_at)

    def get(self, key: str) -> Optional[Any]:
        if key not in self._store:
            return None
        value, expires_at = self._store[key]
        if expires_at and time.time() > expires_at:
            del self._store[key]
            return None
        return value

    def set(self, key: str, value: Any, ttl: int = 60):
        expires_at = time.time() + ttl if ttl else None
        self._store[key] = (value, expires_at)

    def delete(self, key: str):
        self._store.pop(key, None)

    def invalidate_pattern(self, pattern: str):
        keys = [k for k in self._store if fnmatch.fnmatch(k, pattern)]
        for k in keys:
            del self._store[k]

    def increment(self, key: str, ttl: int = 60) -> int:
        current = self.get(key)
        if current is None:
            self.set(key, 1, ttl)
            return 1
        new_val = current + 1
        # Keep existing TTL
        _, expires_at = self._store.get(key, (None, None))
        remaining_ttl = max(0, int(expires_at - time.time())) if expires_at else ttl
        self.set(key, new_val, remaining_ttl)
        return new_val
