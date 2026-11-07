from abc import ABC, abstractmethod
from typing import Any, Optional


class BaseCache(ABC):
    @abstractmethod
    def get(self, key: str) -> Optional[Any]:
        pass

    @abstractmethod
    def set(self, key: str, value: Any, ttl: int = 60):
        pass

    @abstractmethod
    def delete(self, key: str):
        pass

    @abstractmethod
    def invalidate_pattern(self, pattern: str):
        pass

    @abstractmethod
    def increment(self, key: str, ttl: int = 60) -> int:
        pass
