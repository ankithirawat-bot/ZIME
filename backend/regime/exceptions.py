"""Market regime detection exception hierarchy."""

from __future__ import annotations


class RegimeError(Exception):
    """Base exception for all regime detection errors."""


class InvalidRegimeConfigError(RegimeError):
    """Raised when regime configuration is invalid."""

    def __init__(self, message: str) -> None:
        super().__init__(f"Invalid regime config: {message}")


class InsufficientDataError(RegimeError):
    """Raised when insufficient data is provided."""

    def __init__(self, message: str) -> None:
        super().__init__(f"Insufficient data: {message}")


class DetectionError(RegimeError):
    """Raised when regime detection fails."""

    def __init__(self, message: str) -> None:
        super().__init__(f"Detection error: {message}")


class DetectorNotFoundError(RegimeError):
    """Raised when a detector is not found."""

    def __init__(self, name: str) -> None:
        self.name = name
        super().__init__(f"Detector not found: {name}")


class FeatureError(RegimeError):
    """Raised when feature extraction fails."""

    def __init__(self, feature: str, message: str) -> None:
        self.feature = feature
        super().__init__(f"Feature error ({feature}): {message}")


class TransitionError(RegimeError):
    """Raised when regime transition calculation fails."""

    def __init__(self, message: str) -> None:
        super().__init__(f"Transition error: {message}")
