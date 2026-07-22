"""
Deterministic cache key generation.

Produces stable string keys from :class:`AnalyticsContext` for
use with :class:`CacheProvider`.
"""

from __future__ import annotations

import hashlib
from typing import Any

from backend.analytics.models import AnalyticsContext


def _hash(obj: Any) -> str:
    """Return a short hex digest of the string representation of *obj*."""
    return hashlib.md5(str(obj).encode("utf-8"), usedforsecurity=False).hexdigest()[:12]


def make_cache_key(context: AnalyticsContext) -> str:
    """Build a deterministic cache key from an *AnalyticsContext*.

    The key incorporates:
    * Universe identifier (``symbol:exchange``)
    * Latest price bar date
    * Configuration field values
    * Corporate action signatures

    Args:
        context: The analytics input to derive a key from.

    Returns:
        A stable hex string suitable as a cache key.
    """
    symbol = context.symbol
    exchange = context.exchange

    # Latest data timestamp
    if context.prices:
        latest_date = max(b.trade_date for b in context.prices).isoformat()
    else:
        latest_date = "no_data"

    # Configuration digest
    config_hash = _hash(context.config)

    # Corporate actions digest
    ca_hash = _hash(context.corporate_actions)

    raw = f"{symbol}:{exchange}|{latest_date}|{config_hash}|{ca_hash}"
    return hashlib.md5(raw.encode("utf-8"), usedforsecurity=False).hexdigest()
