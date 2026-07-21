"""
Corporate Actions types.

Enumerations used across the corporate actions platform.
"""

from __future__ import annotations

from enum import StrEnum


class ActionType(StrEnum):
    """Supported corporate action types.

    The platform adjusts historical prices for SPLIT, BONUS and
    RIGHTS. DIVIDEND adjusts the adjusted close only. BUYBACK is
    stored as metadata and never adjusts prices.

    New action types can be added here without changing any public
    API — adjustment behaviour is resolved via the AdjustmentEngine
    dispatch table.
    """

    SPLIT = "split"
    BONUS = "bonus"
    DIVIDEND = "dividend"
    RIGHTS = "rights"
    BUYBACK = "buyback"


class AdjustmentType(StrEnum):
    """How a corporate action affects historical prices."""

    OHLC_VOLUME = "ohlc_volume"
    ADJUSTED_CLOSE = "adjusted_close"
    METADATA_ONLY = "metadata_only"
