"""Trend Engine package (analytics)."""

from backend.analytics.trend.evaluators import WeightedEvaluator
from backend.analytics.trend.evidence import Evidence, evidence_texts
from backend.analytics.trend.exceptions import (
    InsufficientDataError,
    SignalError,
    TrendError,
)
from backend.analytics.trend.models import (
    EvaluatorResult,
    ScoringResult,
    SignalOutput,
    TrendState,
)
from backend.analytics.trend.scoring import TrendScorer
from backend.analytics.trend.signals import (
    Signal,
    SignalRegistry,
    build_default_signal_registry,
    higher_highs_lows,
    moving_average_alignment,
    slope_direction,
    trend_persistence,
)
from backend.analytics.trend.trend_engine import TrendEngine

__all__ = [
    "Evidence",
    "EvaluatorResult",
    "InsufficientDataError",
    "ScoringResult",
    "Signal",
    "SignalError",
    "SignalOutput",
    "SignalRegistry",
    "TrendEngine",
    "TrendError",
    "TrendScorer",
    "TrendState",
    "WeightedEvaluator",
    "build_default_signal_registry",
    "evidence_texts",
    "higher_highs_lows",
    "moving_average_alignment",
    "slope_direction",
    "trend_persistence",
]
