"""
Cache provider abstraction.

Defines the :class:`CacheProvider` protocol and ships a thread-safe
:class:`MemoryCache` as the default implementation.
"""

from __future__ import annotations

import time
from abc import ABC, abstractmethod
from dataclasses import dataclass
from threading import Lock
from typing import Any

from backend.cache.models import CacheStats

_DEFAULT_TTL: float = 300.0  # 5 minutes


@dataclass
class _CacheEntry[T]:
    """Internal entry with expiration tracking."""

    value: T
    expires_at: float


class CacheProvider(ABC):
    """Abstract cache provider.

    Subclasses implement :meth:`get`, :meth:`set`, :meth:`invalidate`,
    :meth:`clear` and :meth:`stats`.
    """

    @abstractmethod
    def get(self, key: str) -> Any | None:
        """Retrieve a cached value.

        Args:
            key: Cache key.

        Returns:
            Cached value or ``None`` if missing or expired.
        """
        ...

    @abstractmethod
    def set(self, key: str, value: Any, ttl: float = _DEFAULT_TTL) -> None:
        """Store a value with a time-to-live.

        Args:
            key:   Cache key.
            value: Value to cache.
            ttl:   Time-to-live in seconds (default 300).
        """
        ...

    @abstractmethod
    def invalidate(self, key: str) -> None:
        """Remove a single key from the cache.

        Args:
            key: Cache key to remove.
        """
        ...

    @abstractmethod
    def clear(self) -> None:
        """Remove all entries from the cache."""
        ...

    @abstractmethod
    def stats(self) -> CacheStats:
        """Return cumulative cache telemetry."""
        ...


class MemoryCache(CacheProvider):
    """Thread-safe in-memory cache with TTL support.

    Example::

        cache = MemoryCache()
        cache.set("my-key", {"result": 42}, ttl=60.0)
        value = cache.get("my-key")
    """

    def __init__(self) -> None:
        self._store: dict[str, _CacheEntry[Any]] = {}
        self._lock = Lock()
        self._hits: int = 0
        self._misses: int = 0

    def get(self, key: str) -> Any | None:
        with self._lock:
            entry = self._store.get(key)
            if entry is None:
                self._misses += 1
                return None
            if time.monotonic() > entry.expires_at:
                del self._store[key]
                self._misses += 1
                return None
            self._hits += 1
            return entry.value

    def set(self, key: str, value: Any, ttl: float = _DEFAULT_TTL) -> None:
        with self._lock:
            self._store[key] = _CacheEntry(
                value=value,
                expires_at=time.monotonic() + ttl,
            )

    def invalidate(self, key: str) -> None:
        with self._lock:
            self._store.pop(key, None)

    def clear(self) -> None:
        with self._lock:
            self._store.clear()
            self._hits = 0
            self._misses = 0

    def stats(self) -> CacheStats:
        with self._lock:
            total = self._hits + self._misses
            ratio = self._hits / total if total > 0 else 0.0
            return CacheStats(
                hits=self._hits,
                misses=self._misses,
                hit_ratio=round(ratio, 4),
            )
