"""Volume engine exceptions."""

from __future__ import annotations


class VolumeError(Exception):
    """Base exception for volume engine errors."""


class InsufficientDataError(VolumeError):
    """Raised when context lacks the data required for analysis."""


class SignalError(VolumeError):
    """Raised when a signal fails or is misconfigured."""
