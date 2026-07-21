"""
Data quality exceptions.

Domain errors for the data quality platform. Every error derives from
:class:`DataQualityError` so callers can catch the family.
"""

from __future__ import annotations


class DataQualityError(Exception):
    """Base exception for all data quality errors."""


class ValidationError(DataQualityError):
    """Raised when a validation request is malformed."""


class RuleNotFoundError(DataQualityError):
    """Raised when a requested validation rule is not registered."""

    def __init__(self, name: str) -> None:
        self.name = name
        super().__init__(f"Validation rule not registered: {name}")


class DetectorNotFoundError(DataQualityError):
    """Raised when a requested anomaly detector is not registered."""

    def __init__(self, name: str) -> None:
        self.name = name
        super().__init__(f"Anomaly detector not registered: {name}")
