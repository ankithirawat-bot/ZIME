"""Sizing exception hierarchy."""

from __future__ import annotations


class SizingError(Exception):
    """Base exception for all sizing errors."""


class InvalidSizingConfigError(SizingError):
    """Raised when sizing configuration is invalid."""

    def __init__(self, message: str) -> None:
        super().__init__(f"Invalid sizing config: {message}")


class InsufficientDataError(SizingError):
    """Raised when insufficient data is provided for sizing calculations."""

    def __init__(self, message: str) -> None:
        super().__init__(f"Insufficient data: {message}")


class CalculationError(SizingError):
    """Raised when a sizing calculation fails."""

    def __init__(self, calculation: str, message: str) -> None:
        self.calculation = calculation
        super().__init__(f"Calculation error ({calculation}): {message}")


class ConstraintViolationError(SizingError):
    """Raised when a sizing constraint is violated."""

    def __init__(self, constraint: str, message: str) -> None:
        self.constraint = constraint
        super().__init__(f"Constraint violation ({constraint}): {message}")


class EmptyPortfolioError(SizingError):
    """Raised when the portfolio is empty."""

    def __init__(self) -> None:
        super().__init__("Portfolio is empty")


class MethodNotFoundError(SizingError):
    """Raised when a sizing method is not found."""

    def __init__(self, name: str) -> None:
        self.name = name
        super().__init__(f"Sizing method not found: {name}")
