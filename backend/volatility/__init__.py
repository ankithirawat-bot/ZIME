"""Volatility forecast engine.

Provides a production-grade volatility forecasting engine capable of estimating
future volatility using multiple statistical models (Historical, EWMA, GARCH,
EGARCH, GJR-GARCH).
"""

from __future__ import annotations

from backend.volatility.comparison import ModelComparer
from backend.volatility.engine import VolatilityEngine
from backend.volatility.estimators import (
    EGARCHEstimator,
    EWMAAEstimator,
    GARCHEstimator,
    GJRGARCHEstimator,
    HistoricalVolatilityEstimator,
)
from backend.volatility.exceptions import (
    ConvergenceError,
    EstimationError,
    ForecastError,
    InsufficientDataError,
    InvalidVolatilityConfigError,
    ModelNotFoundError,
    VolatilityError,
)
from backend.volatility.factory import VolatilityFactory
from backend.volatility.forecast import ForecastEngine
from backend.volatility.models import (
    ConfidenceInterval,
    ForecastDefinition,
    ForecastMetrics,
    ForecastResult,
    ForecastStatistics,
    ModelComparison,
    VolatilityConfig,
    VolatilityForecast,
    VolatilityMetadata,
)

__all__ = [
    "ConfidenceInterval",
    "ConvergenceError",
    "EWMAAEstimator",
    "EGARCHEstimator",
    "EstimationError",
    "ForecastDefinition",
    "ForecastEngine",
    "ForecastError",
    "ForecastMetrics",
    "ForecastResult",
    "ForecastStatistics",
    "GARCHEstimator",
    "GJRGARCHEstimator",
    "HistoricalVolatilityEstimator",
    "InsufficientDataError",
    "InvalidVolatilityConfigError",
    "ModelComparer",
    "ModelComparison",
    "ModelNotFoundError",
    "VolatilityConfig",
    "VolatilityEngine",
    "VolatilityError",
    "VolatilityFactory",
    "VolatilityForecast",
    "VolatilityMetadata",
]
