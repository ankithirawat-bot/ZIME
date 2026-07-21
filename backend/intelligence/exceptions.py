"""Adaptive intelligence exception hierarchy."""

from __future__ import annotations


class IntelligenceError(Exception):
    """Base exception for all intelligence errors."""


class ModelNotFoundError(IntelligenceError):
    """Raised when a model is not found."""

    def __init__(self, name: str) -> None:
        self.name = name
        super().__init__(f"Model not found: {name}")


class InsufficientDataError(IntelligenceError):
    """Raised when insufficient data is available."""

    def __init__(self, message: str) -> None:
        super().__init__(f"Insufficient data: {message}")


class SelectionError(IntelligenceError):
    """Raised when model selection fails."""

    def __init__(self, message: str) -> None:
        super().__init__(f"Selection error: {message}")


class EnsembleError(IntelligenceError):
    """Raised when ensemble computation fails."""

    def __init__(self, message: str) -> None:
        super().__init__(f"Ensemble error: {message}")


class EvaluationError(IntelligenceError):
    """Raised when model evaluation fails."""

    def __init__(self, message: str) -> None:
        super().__init__(f"Evaluation error: {message}")


class LearningError(IntelligenceError):
    """Raised when learning update fails."""

    def __init__(self, message: str) -> None:
        super().__init__(f"Learning error: {message}")


class ConfidenceError(IntelligenceError):
    """Raised when confidence computation fails."""

    def __init__(self, message: str) -> None:
        super().__init__(f"Confidence error: {message}")
