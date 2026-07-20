"""Trend engine exceptions."""

from __future__ import annotations


class TrendError(Exception):
    """Base exception for trend engine errors."""


class InsufficientDataError(TrendError):
    """Raised when context lacks the data required for analysis."""


class SignalError(TrendError):
    """Raised when a signal fails or is misconfigured."""
