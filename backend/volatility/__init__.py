"""Volatility forecast engine.

Provides a production-grade volatility forecasting engine using multiple
statistical models: Historical, EWMA, GARCH, EGARCH, GJR-GARCH.
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
    DiagnosticsError,
    EstimationError,
    ForecastError,
    InsufficientDataError,
    InvalidVolatilityConfigError,
    ModelNotFoundError,
    UpdateError,
    VolatilityError,
)
from backend.volatility.factory import VolatilityFactory
from backend.volatility.forecast import ForecastEngine
from backend.volatility.models import (
    ConfidenceInterval,
    ForecastDefinition,
    ForecastMetrics,
    ForecastRequest,
    ForecastResult,
    ForecastStatistics,
    ModelComparison,
    ModelDiagnostics,
    VolatilityConfig,
    VolatilityForecast,
    VolatilityMetadata,
)

__all__ = [
    "ConfidenceInterval",
    "ConvergenceError",
    "DiagnosticsError",
    "EWMAAEstimator",
    "EGARCHEstimator",
    "EstimationError",
    "ForecastDefinition",
    "ForecastEngine",
    "ForecastError",
    "ForecastMetrics",
    "ForecastRequest",
    "ForecastResult",
    "ForecastStatistics",
    "GARCHEstimator",
    "GJRGARCHEstimator",
    "HistoricalVolatilityEstimator",
    "InsufficientDataError",
    "InvalidVolatilityConfigError",
    "ModelComparer",
    "ModelComparison",
    "ModelDiagnostics",
    "ModelNotFoundError",
    "UpdateError",
    "VolatilityConfig",
    "VolatilityEngine",
    "VolatilityError",
    "VolatilityFactory",
    "VolatilityForecast",
    "VolatilityMetadata",
]
