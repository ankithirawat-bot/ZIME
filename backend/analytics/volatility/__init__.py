"""Volatility Engine package (analytics)."""

from backend.analytics.volatility.evaluators import WeightedEvaluator
from backend.analytics.volatility.evidence import Evidence, evidence_texts
from backend.analytics.volatility.exceptions import (
    InsufficientDataError,
    SignalError,
    VolatilityError,
)
from backend.analytics.volatility.models import (
    EvaluatorResult,
    ScoringResult,
    SignalOutput,
    VolatilityConfig,
    VolatilityState,
)
from backend.analytics.volatility.scoring import VolatilityScorer
from backend.analytics.volatility.signals import (
    Signal,
    SignalRegistry,
    build_default_signal_registry,
    historical_volatility,
    range_expansion,
    volatility_persistence,
    volatility_trend,
)
from backend.analytics.volatility.volatility_engine import VolatilityEngine

__all__ = [
    "Evidence",
    "EvaluatorResult",
    "InsufficientDataError",
    "Signal",
    "SignalError",
    "ScoringResult",
    "SignalOutput",
    "SignalRegistry",
    "VolatilityConfig",
    "VolatilityEngine",
    "VolatilityError",
    "VolatilityScorer",
    "VolatilityState",
    "WeightedEvaluator",
    "build_default_signal_registry",
    "evidence_texts",
    "historical_volatility",
    "range_expansion",
    "volatility_persistence",
    "volatility_trend",
]
