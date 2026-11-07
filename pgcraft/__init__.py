from .connection import connect, Database
from .result import Result
from .exception import (
    PgCraftError,
    ConnectionError,
    QueryError,
    NotFoundError,
    MultipleRowsError,
)

__version__ = "0.1.0"
__all__ = [
    "connect",
    "Database",
    "Result",
    "PgCraftError",
    "ConnectionError",
    "QueryError",
    "NotFoundError",
    "MultipleRowsError",
]
