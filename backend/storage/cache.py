"""
Cache abstraction.

Abstract base class for in-memory caching.
"""

from __future__ import annotations

from abc import ABC, abstractmethod


class CacheProvider(ABC):
    """Abstract interface for cache operations.

    Concrete implementations handle the actual cache mechanism
    (Redis, in-memory dict, etc.).
    """

    @abstractmethod
    def get(self, key: str) -> object | None:
        """Retrieve a value from the cache.

        Args:
            key: Cache key.

        Returns:
            Cached value or None if not found.
        """

    @abstractmethod
    def put(self, key: str, value: object, ttl_seconds: int | None = None) -> None:
        """Store a value in the cache.

        Args:
            key:         Cache key.
            value:       Value to store.
            ttl_seconds: Optional time-to-live in seconds.
        """

    @abstractmethod
    def invalidate(self, key: str) -> bool:
        """Remove a specific key from the cache.

        Args:
            key: Cache key to remove.

        Returns:
            True if the key existed and was removed.
        """

    @abstractmethod
    def clear(self) -> int:
        """Remove all entries from the cache.

        Returns:
            Number of entries removed.
        """
