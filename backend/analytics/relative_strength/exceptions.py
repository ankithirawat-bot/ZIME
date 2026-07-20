"""Relative Strength engine exceptions."""

from __future__ import annotations


class RelativeStrengthError(Exception):
    """Base exception for relative strength engine errors."""


class InsufficientDataError(RelativeStrengthError):
    """Raised when context lacks the data required for analysis."""


class SignalError(RelativeStrengthError):
    """Raised when a signal fails or is misconfigured."""
