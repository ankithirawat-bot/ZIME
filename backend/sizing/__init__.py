"""Position sizing engine.

Provides a production-grade position sizing engine responsible for calculating
optimal position sizes based on account size, portfolio constraints, volatility,
and risk management rules.
"""

from __future__ import annotations

from backend.sizing.engine import SizingEngine
from backend.sizing.exceptions import (
    CalculationError,
    ConstraintViolationError,
    EmptyPortfolioError,
    InsufficientDataError,
    InvalidSizingConfigError,
    MethodNotFoundError,
    SizingError,
)
from backend.sizing.factory import SizingFactory
from backend.sizing.models import (
    AllocationResult,
    PositionRequest,
    PositionSizing,
    RiskBudget,
    SizingConfig,
    SizingDefinition,
    SizingMetadata,
    SizingMetrics,
    SizingStatistics,
)

__all__ = [
    "AllocationResult",
    "CalculationError",
    "ConstraintViolationError",
    "EmptyPortfolioError",
    "InsufficientDataError",
    "InvalidSizingConfigError",
    "MethodNotFoundError",
    "PositionRequest",
    "PositionSizing",
    "RiskBudget",
    "SizingConfig",
    "SizingDefinition",
    "SizingEngine",
    "SizingError",
    "SizingFactory",
    "SizingMetadata",
    "SizingMetrics",
    "SizingStatistics",
]
