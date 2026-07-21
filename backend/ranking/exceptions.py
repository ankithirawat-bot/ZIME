"""Ranking exception hierarchy."""

from __future__ import annotations


class RankingError(Exception):
    """Base exception for all ranking errors."""


class FactorNotFoundError(RankingError):
    """Raised when a requested factor is not registered."""

    def __init__(self, name: str) -> None:
        self.name = name
        super().__init__(f"Factor not found: {name}")


class InvalidWeightsError(RankingError):
    """Raised when weights configuration is invalid."""

    def __init__(self, message: str) -> None:
        super().__init__(f"Invalid weights: {message}")


class InvalidNormalizationError(RankingError):
    """Raised when normalization method is invalid."""

    def __init__(self, method: str) -> None:
        self.method = method
        super().__init__(f"Invalid normalization method: {method}")


class EmptyUniverseError(RankingError):
    """Raised when no symbols are provided for ranking."""

    def __init__(self) -> None:
        super().__init__("No symbols provided for ranking")


class InsufficientDataError(RankingError):
    """Raised when insufficient data is available for ranking."""

    def __init__(self, symbol: str, message: str) -> None:
        self.symbol = symbol
        super().__init__(f"Insufficient data for {symbol}: {message}")


class RankingConfigurationError(RankingError):
    """Raised when ranking configuration is invalid."""

    def __init__(self, message: str) -> None:
        super().__init__(f"Ranking configuration error: {message}")
