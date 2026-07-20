"""
Shared core package for the ZIME backend.

Provides constants, type aliases, validation helpers, and enumerations
that are used across multiple engines.
"""

from backend.core.constants import (
    DEFAULT_CONFIDENCE,
    DEFAULT_MAX_RISK,
    MAX_ITEMS,
    MIN_RR_ACCEPTABLE,
)
from backend.core.enums import FactorCategory, Signal
from backend.core.types import Confidence, Money, Percentage, Score
from backend.core.validation import (
    validate_confidence,
    validate_non_negative,
    validate_percentage,
    validate_position_size,
    validate_positive_number,
    validate_price_relationship,
)

__all__ = [
    "DEFAULT_CONFIDENCE",
    "DEFAULT_MAX_RISK",
    "FactorCategory",
    "MAX_ITEMS",
    "MIN_RR_ACCEPTABLE",
    "Money",
    "Percentage",
    "Confidence",
    "Score",
    "Signal",
    "validate_confidence",
    "validate_non_negative",
    "validate_percentage",
    "validate_positive_number",
    "validate_price_relationship",
    "validate_position_size",
]
