"""
Cache models.

Immutable data classes for cache keys and telemetry.
"""

from __future__ import annotations

from dataclasses import dataclass


@dataclass(frozen=True)
class CacheKey:
    """Deterministic cache key components.

    Attributes:
        universe_id:    ``symbol:exchange`` identifier.
        data_timestamp: ISO date of the latest price bar.
        config_hash:    Hex digest of the engine configuration.
        params_hash:    Hex digest of additional parameters.
    """

    universe_id: str = ""
    data_timestamp: str = ""
    config_hash: str = ""
    params_hash: str = ""


@dataclass(frozen=True)
class CacheStats:
    """Cache performance telemetry.

    Attributes:
        hits:      Number of cache hits since last reset.
        misses:    Number of cache misses since last reset.
        hit_ratio: Ratio ``hits / (hits + misses)``.
    """

    hits: int = 0
    misses: int = 0
    hit_ratio: float = 0.0
