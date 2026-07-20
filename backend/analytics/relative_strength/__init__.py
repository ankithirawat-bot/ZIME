"""Relative Strength Engine package (analytics)."""

from backend.analytics.relative_strength.evaluators import WeightedEvaluator
from backend.analytics.relative_strength.evidence import Evidence, evidence_texts
from backend.analytics.relative_strength.exceptions import (
    InsufficientDataError,
    RelativeStrengthError,
    SignalError,
)
from backend.analytics.relative_strength.models import (
    EvaluatorResult,
    RelativeStrengthConfig,
    RelativeStrengthState,
    ScoringResult,
    SignalOutput,
)
from backend.analytics.relative_strength.relative_strength_engine import (
    RelativeStrengthEngine,
)
from backend.analytics.relative_strength.scoring import RelativeStrengthScorer
from backend.analytics.relative_strength.signals import (
    Signal,
    SignalRegistry,
    benchmark_outperformance,
    build_default_signal_registry,
    industry_leadership,
    relative_momentum_persistence,
    sector_leadership,
)

__all__ = [
    "Evidence",
    "EvaluatorResult",
    "InsufficientDataError",
    "RelativeStrengthConfig",
    "RelativeStrengthEngine",
    "RelativeStrengthError",
    "RelativeStrengthScorer",
    "RelativeStrengthState",
    "ScoringResult",
    "Signal",
    "SignalError",
    "SignalOutput",
    "SignalRegistry",
    "WeightedEvaluator",
    "benchmark_outperformance",
    "build_default_signal_registry",
    "evidence_texts",
    "industry_leadership",
    "relative_momentum_persistence",
    "sector_leadership",
]
