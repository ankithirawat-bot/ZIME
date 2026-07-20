"""Volume Engine package (analytics)."""

from backend.analytics.volume.evaluators import WeightedEvaluator
from backend.analytics.volume.evidence import Evidence, evidence_texts
from backend.analytics.volume.exceptions import (
    InsufficientDataError,
    SignalError,
    VolumeError,
)
from backend.analytics.volume.models import (
    EvaluatorResult,
    ScoringResult,
    SignalOutput,
    VolumeConfig,
    VolumeState,
)
from backend.analytics.volume.scoring import VolumeScorer
from backend.analytics.volume.signals import (
    Signal,
    SignalRegistry,
    accumulation_distribution,
    build_default_signal_registry,
    relative_volume,
    volume_consistency,
    volume_trend,
)
from backend.analytics.volume.volume_engine import VolumeEngine

__all__ = [
    "Evidence",
    "EvaluatorResult",
    "InsufficientDataError",
    "Signal",
    "SignalError",
    "SignalOutput",
    "SignalRegistry",
    "ScoringResult",
    "VolumeConfig",
    "VolumeEngine",
    "VolumeError",
    "VolumeScorer",
    "VolumeState",
    "WeightedEvaluator",
    "accumulation_distribution",
    "build_default_signal_registry",
    "evidence_texts",
    "relative_volume",
    "volume_consistency",
    "volume_trend",
]
