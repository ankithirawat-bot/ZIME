"""Volatility forecast exception hierarchy."""

from __future__ import annotations


class VolatilityError(Exception):
    """Base exception for all volatility forecast errors."""


class InvalidVolatilityConfigError(VolatilityError):
    """Raised when volatility configuration is invalid."""

    def __init__(self, message: str) -> None:
        super().__init__(f"Invalid volatility config: {message}")


class InsufficientDataError(VolatilityError):
    """Raised when insufficient data is provided for volatility calculations."""

    def __init__(self, message: str) -> None:
        super().__init__(f"Insufficient data: {message}")


class EstimationError(VolatilityError):
    """Raised when model parameter estimation fails."""

    def __init__(self, model: str, message: str) -> None:
        self.model = model
        super().__init__(f"Estimation error ({model}): {message}")


class ConvergenceError(VolatilityError):
    """Raised when model estimation fails to converge."""

    def __init__(self, model: str, message: str = "") -> None:
        self.model = model
        msg = f"Convergence error ({model})"
        if message:
            msg += f": {message}"
        super().__init__(msg)


class ForecastError(VolatilityError):
    """Raised when volatility forecasting fails."""

    def __init__(self, message: str) -> None:
        super().__init__(f"Forecast error: {message}")


class ModelNotFoundError(VolatilityError):
    """Raised when a volatility model is not found."""

    def __init__(self, name: str) -> None:
        self.name = name
        super().__init__(f"Volatility model not found: {name}")
