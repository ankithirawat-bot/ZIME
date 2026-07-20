"""Volume engine immutable models.

Defines the volume-state enumeration, the volume configuration and the
intermediate result models passed between signals, evaluators and the scorer.
None of these expose raw indicator values; they carry only scores, states and
evidence.
"""

from __future__ import annotations

from dataclasses import dataclass
from enum import StrEnum

from backend.analytics.models import TrendConfig
from backend.analytics.volume.evidence import Evidence


class VolumeState(StrEnum):
    """Volume participation classification produced by the engine."""

    VERY_STRONG = "Very Strong"
    STRONG = "Strong"
    NEUTRAL = "Neutral"
    WEAK = "Weak"
    VERY_WEAK = "Very Weak"


@dataclass(frozen=True)
class VolumeConfig(TrendConfig):
    """Immutable configuration for volume analysis.

    Inherits the base analytics configuration so it remains compatible with the
    shared :class:`AnalyticsContext` contract, while adding volume-specific
    windows, thresholds and signal weights.

    Attributes:
        relative_volume_window: Bars for the average-volume baseline.
        volume_trend_window:    Bars per segment for the volume trend.
        accumulation_window:    Bars for up/down volume split.
        consistency_window:     Bars for the volume-consistency measure.
        weight_relative_volume: Weight of the relative-volume signal.
        weight_volume_trend:    Weight of the volume-trend signal.
        weight_accumulation:    Weight of the accumulation/distribution signal.
        weight_consistency:     Weight of the consistency signal.
        conflict_threshold:     Agreement below this flags conflicting signals.
    """

    relative_volume_window: int = 20
    volume_trend_window: int = 10
    accumulation_window: int = 20
    consistency_window: int = 20
    weight_relative_volume: float = 0.30
    weight_volume_trend: float = 0.25
    weight_accumulation: float = 0.25
    weight_consistency: float = 0.20


@dataclass(frozen=True)
class SignalOutput:
    """Immutable output of a single volume signal.

    Attributes:
        name:      Signal identifier.
        score:     Directional score in [-1, 1] (+ strong participation, - weak).
        evidence:  Evidence items supporting the score.
        available: False when the signal lacked sufficient data.
    """

    name: str
    score: float
    evidence: tuple[Evidence, ...]
    available: bool = True


@dataclass(frozen=True)
class EvaluatorResult:
    """Immutable combined result of all signals.

    Attributes:
        combined_score:  Weighted combination of signal scores in [-1, 1].
        agreement:       Direction agreement in [0, 1] (1 = unanimous).
        available_count: Number of signals with sufficient data.
        total_count:     Total number of signals evaluated.
        evidence:        All evidence items from available signals.
        conflict:        True when signals disagree below the threshold.
    """

    combined_score: float
    agreement: float
    available_count: int
    total_count: int
    evidence: tuple[Evidence, ...]
    conflict: bool


@dataclass(frozen=True)
class ScoringResult:
    """Immutable final scoring outcome.

    Attributes:
        state:       Resulting volume state.
        confidence:  Confidence score in [0, 100].
        evidence:    Evidence items carried into the analytics fact.
    """

    state: VolumeState
    confidence: float
    evidence: tuple[Evidence, ...]
