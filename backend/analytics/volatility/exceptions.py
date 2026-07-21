"""Volatility engine exceptions."""

from __future__ import annotations


class VolatilityError(Exception):
    """Base exception for volatility engine errors."""


class InsufficientDataError(VolatilityError):
    """Raised when context lacks the data required for analysis."""


class SignalError(VolatilityError):
    """Raised when a signal fails or is misconfigured."""
