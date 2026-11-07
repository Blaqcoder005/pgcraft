import os
import json
from .backend.pg8000 import Pg8000Backend
from .query_builder import QueryBuilder
from .exception import ConnectionError
from .cache.memory import MemoryCache
from .cache.redis import RedisCache
from .rate_limiter import RateLimiter


class Database:
    def __init__(self, backend, cache=None):
        self._backend = backend
        self._cache = cache
        self.rate_limiter = RateLimiter(cache) if cache else None

    def table(self, table_name):
        qb = QueryBuilder(self._backend, table_name)
        qb._cache_backend = self._cache
        return qb

    def rate_limit(self, key: str, limit: int = 100, window: int = 60):
        if not self.rate_limiter:
            return {"allowed": True, "count": 0, "limit": limit, "remaining": limit}
        return self.rate_limiter.check(key, limit, window)

    def cache_invalidate(self, table: str):
        if self._cache:
            self._cache.invalidate_pattern(f"pgcraft:{table}:*")

    def raw(self, query, args=None):
        columns, rows = self._backend.execute(query, args or [])
        if not columns:
            return []
        return [self._backend.row_to_dict(columns, row) for row in rows]

    def rpc(self, function_name, params=None):
        if params:
            arg_slots = ", ".join([f"{k} := %s" for k in params.keys()])
            query = f"SELECT * FROM {function_name}({arg_slots})"
            args = list(params.values())
        else:
            query = f"SELECT * FROM {function_name}()"
            args = []

        columns, rows = self._backend.execute(query, args)
        if not columns:
            return []
        return [self._backend.row_to_dict(columns, row) for row in rows]


def connect(
    host=None,
    database=None,
    user=None,
    password=None,
    port=None,
    engine=None,
    cache=None,
    cache_url=None,
):
    # Fall back to env vars if not passed directly
    host = host or os.getenv("DB_HOST", "localhost")
    database = database or os.getenv("DB_NAME", "postgres")
    user = user or os.getenv("DB_USER", "postgres")
    password = password or os.getenv("DB_PASS", "")
    port = int(port or os.getenv("DB_PORT", 5432))
    engine = engine or os.getenv("DB_ENGINE", "pg8000")
    cache = cache or os.getenv("CACHE") or None
    cache_url = cache_url or os.getenv("CACHE_URL") or None

    # Setup backend
    if engine == "pg8000":
        b = Pg8000Backend(
            host=host,
            database=database,
            user=user,
            password=password,
            port=port,
        )
    elif engine == "psycopg2":
        from .backends.psycopg2 import Psycopg2Backend
        b = Psycopg2Backend(
            host=host,
            database=database,
            user=user,
            password=password,
            port=port,
        )
    else:
        raise ValueError(f"Unknown engine: {engine}")

    # Setup cache
    cache_backend = None
    if cache == "memory":
        cache_backend = MemoryCache()
    elif cache == "redis":
        cache_backend = RedisCache(url=cache_url or "redis://localhost:6379")

    return Database(b, cache=cache_backend)
