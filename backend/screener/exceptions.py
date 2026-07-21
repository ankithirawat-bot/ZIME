"""Screener exception hierarchy."""

from __future__ import annotations


class ScreenerError(Exception):
    """Base exception for all screener errors."""


class FilterNotFoundError(ScreenerError):
    """Raised when a requested filter is not registered."""

    def __init__(self, name: str) -> None:
        self.name = name
        super().__init__(f"Filter not found: {name}")


class OperatorNotFoundError(ScreenerError):
    """Raised when a requested operator is not registered."""

    def __init__(self, name: str) -> None:
        self.name = name
        super().__init__(f"Operator not found: {name}")


class InvalidFilterError(ScreenerError):
    """Raised when a filter definition is invalid."""

    def __init__(self, message: str) -> None:
        super().__init__(f"Invalid filter: {message}")


class InvalidOperatorError(ScreenerError):
    """Raised when an operator application is invalid."""

    def __init__(self, message: str) -> None:
        super().__init__(f"Invalid operator: {message}")


class InvalidScreenDefinitionError(ScreenerError):
    """Raised when a screen definition is invalid."""

    def __init__(self, message: str) -> None:
        super().__init__(f"Invalid screen definition: {message}")


class ParserError(ScreenerError):
    """Raised when parsing a screen definition fails."""

    def __init__(self, message: str) -> None:
        super().__init__(f"Parser error: {message}")


class EvaluationError(ScreenerError):
    """Raised when screen evaluation fails."""

    def __init__(self, symbol: str, message: str) -> None:
        self.symbol = symbol
        super().__init__(f"Evaluation failed for {symbol}: {message}")
