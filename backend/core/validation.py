"""
Reusable validation helpers.

All functions are pure: they return True when the input is valid and
False otherwise.  Exceptions are reserved for programming or
configuration errors, not for expected validation failures.
"""

from __future__ import annotations


def validate_percentage(value: float, name: str = "value") -> bool:
    """Validate that *value* is in the range [0, 100].

    Args:
        value: The number to check.
        name:  Label (unused, kept for API consistency).

    Returns:
        True when *value* is in [0, 100].
    """
    return 0.0 <= value <= 100.0


def validate_confidence(value: float, name: str = "confidence") -> bool:
    """Validate that *value* is in the range [0, 100].

    Args:
        value: The number to check.
        name:  Label (unused, kept for API consistency).

    Returns:
        True when *value* is in [0, 100].
    """
    return validate_percentage(value, name)


def validate_positive_number(value: float, name: str = "value") -> bool:
    """Validate that *value* is strictly positive (> 0).

    Args:
        value: The number to check.
        name:  Label (unused, kept for API consistency).

    Returns:
        True when *value* > 0.
    """
    return value > 0.0


def validate_non_negative(value: float, name: str = "value") -> bool:
    """Validate that *value* is non-negative (>= 0).

    Args:
        value: The number to check.
        name:  Label (unused, kept for API consistency).

    Returns:
        True when *value* >= 0.
    """
    return value >= 0.0


def validate_price_relationship(
    entry: float,
    stop: float,
    *,
    allow_equal: bool = False,
) -> bool:
    """Validate that *stop* is below *entry*.

    Args:
        entry:      Entry price.
        stop:       Stop-loss price.
        allow_equal: If True, stop == entry is accepted.

    Returns:
        True when the price relationship is valid.
    """
    if allow_equal:
        return stop <= entry
    return stop < entry


def validate_position_size(
    value: float,
    max_size: float | None = None,
    name: str = "position_size",
) -> bool:
    """Validate position size is positive and within bounds.

    Args:
        value:    The position size to check (fractional, e.g. 0.15).
        max_size: Optional upper bound (inclusive).
        name:     Label (unused, kept for API consistency).

    Returns:
        True when *value* is positive and within *max_size*.
    """
    if value <= 0.0:
        return False
    if max_size is not None and value > max_size:
        return False
    return True
