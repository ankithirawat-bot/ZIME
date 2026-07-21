"""Risk exception hierarchy."""

from __future__ import annotations


class RiskError(Exception):
    """Base exception for all risk errors."""


class InvalidRiskConfigError(RiskError):
    """Raised when risk configuration is invalid."""

    def __init__(self, message: str) -> None:
        super().__init__(f"Invalid risk config: {message}")


class InsufficientDataError(RiskError):
    """Raised when insufficient data is provided for risk calculations."""

    def __init__(self, message: str) -> None:
        super().__init__(f"Insufficient data: {message}")


class VaRCalculationError(RiskError):
    """Raised when VaR calculation fails."""

    def __init__(self, message: str) -> None:
        super().__init__(f"VaR calculation error: {message}")


class StressTestError(RiskError):
    """Raised when stress test fails."""

    def __init__(self, message: str) -> None:
        super().__init__(f"Stress test error: {message}")


class ScenarioError(RiskError):
    """Raised when scenario analysis fails."""

    def __init__(self, message: str) -> None:
        super().__init__(f"Scenario error: {message}")


class LimitViolationError(RiskError):
    """Raised when a risk limit is violated."""

    def __init__(self, limit: str, message: str) -> None:
        self.limit = limit
        super().__init__(f"Limit violation ({limit}): {message}")


class EmptyPortfolioError(RiskError):
    """Raised when the portfolio is empty."""

    def __init__(self) -> None:
        super().__init__("Portfolio is empty")


class ScenarioNotFoundError(RiskError):
    """Raised when a scenario is not found."""

    def __init__(self, name: str) -> None:
        self.name = name
        super().__init__(f"Scenario not found: {name}")


class CalculationError(RiskError):
    """Raised when a risk calculation fails."""

    def __init__(self, calculation: str, message: str) -> None:
        self.calculation = calculation
        super().__init__(f"Calculation error ({calculation}): {message}")
