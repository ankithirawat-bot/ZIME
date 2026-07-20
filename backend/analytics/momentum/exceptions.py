"""Momentum engine exceptions."""

from __future__ import annotations


class MomentumError(Exception):
    """Base exception for momentum engine errors."""


class InsufficientDataError(MomentumError):
    """Raised when context lacks the data required for analysis."""


class SignalError(MomentumError):
    """Raised when a signal fails or is misconfigured."""
