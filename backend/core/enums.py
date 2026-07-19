"""
Core enumerations for the ZIME factor framework.
"""

from enum import Enum


class Signal(str, Enum):
    """Directional signal emitted by a factor computation.

    Used to indicate the directional interpretation of a factor's
    numeric value relative to the instrument's outlook.
    """

    BULLISH = "bullish"
    BEARISH = "bearish"
    NEUTRAL = "neutral"


class FactorCategory(str, Enum):
    """Categorizes factors by their analytical domain.

    Used for grouping, filtering, and routing factor results
    to the appropriate scoring and engine layers.
    """

    TECHNICAL = "technical"
    FUNDAMENTAL = "fundamental"
    RISK = "risk"
    LIQUIDITY = "liquidity"
    MOMENTUM = "momentum"
    VOLUME = "volume"
