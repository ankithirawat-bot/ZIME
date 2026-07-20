"""Momentum Engine package (analytics)."""

from backend.analytics.momentum.evaluators import WeightedEvaluator
from backend.analytics.momentum.evidence import Evidence, evidence_texts
from backend.analytics.momentum.exceptions import (
    InsufficientDataError,
    MomentumError,
    SignalError,
)
from backend.analytics.momentum.models import (
    EvaluatorResult,
    MomentumConfig,
    MomentumState,
    ScoringResult,
    SignalOutput,
)
from backend.analytics.momentum.momentum_engine import MomentumEngine
from backend.analytics.momentum.scoring import MomentumScorer
from backend.analytics.momentum.signals import (
    Signal,
    SignalRegistry,
    breakout_continuation,
    build_default_signal_registry,
    momentum_persistence,
    price_acceleration,
    rate_of_change,
)

__all__ = [
    "Evidence",
    "EvaluatorResult",
    "InsufficientDataError",
    "MomentumConfig",
    "MomentumEngine",
    "MomentumError",
    "MomentumState",
    "ScoringResult",
    "Signal",
    "SignalError",
    "SignalOutput",
    "SignalRegistry",
    "WeightedEvaluator",
    "breakout_continuation",
    "build_default_signal_registry",
    "evidence_texts",
    "momentum_persistence",
    "price_acceleration",
    "rate_of_change",
    "MomentumScorer",
]
