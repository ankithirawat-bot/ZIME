"""Strategy exception hierarchy."""

from __future__ import annotations


class StrategyError(Exception):
    """Base exception for all strategy errors."""


class RuleNotFoundError(StrategyError):
    """Raised when a requested rule is not registered."""

    def __init__(self, name: str) -> None:
        self.name = name
        super().__init__(f"Rule not found: {name}")


class InvalidRuleError(StrategyError):
    """Raised when a rule definition is invalid."""

    def __init__(self, message: str) -> None:
        super().__init__(f"Invalid rule: {message}")


class InvalidConditionError(StrategyError):
    """Raised when a condition is invalid."""

    def __init__(self, message: str) -> None:
        super().__init__(f"Invalid condition: {message}")


class InvalidStrategyError(StrategyError):
    """Raised when a strategy definition is invalid."""

    def __init__(self, message: str) -> None:
        super().__init__(f"Invalid strategy: {message}")


class EvaluationError(StrategyError):
    """Raised when strategy evaluation fails."""

    def __init__(self, symbol: str, message: str) -> None:
        self.symbol = symbol
        super().__init__(f"Evaluation failed for {symbol}: {message}")


class EmptyUniverseError(StrategyError):
    """Raised when no symbols are provided for evaluation."""

    def __init__(self) -> None:
        super().__init__("No symbols provided for evaluation")


class ConfigurationError(StrategyError):
    """Raised when strategy configuration is invalid."""

    def __init__(self, message: str) -> None:
        super().__init__(f"Configuration error: {message}")
