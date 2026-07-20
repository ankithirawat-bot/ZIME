"""Relative Strength engine immutable models.

Defines the relative-strength state enumeration, the configuration and the
intermediate result models passed between signals, evaluators and the scorer.
None of these expose raw indicator values; they carry only scores, states and
evidence.
"""

from __future__ import annotations

from dataclasses import dataclass
from enum import StrEnum

from backend.analytics.models import TrendConfig
from backend.analytics.relative_strength.evidence import Evidence


class RelativeStrengthState(StrEnum):
    """Relative strength classification produced by the engine."""

    VERY_STRONG = "Very Strong"
    STRONG = "Strong"
    NEUTRAL = "Neutral"
    WEAK = "Weak"
    VERY_WEAK = "Very Weak"


@dataclass(frozen=True)
class RelativeStrengthConfig(TrendConfig):
    """Immutable configuration for relative-strength analysis.

    Inherits the base analytics configuration so it remains compatible with the
    shared :class:`AnalyticsContext` contract, while adding relative-strength
    windows, thresholds and signal weights.

    Attributes:
        rs_window:               Lookback for point-in-time outperformance.
        rs_persistence_window:   Sub-window length for persistence of RS.
        weight_benchmark:        Weight of the benchmark-outperformance signal.
        weight_sector:           Weight of the sector-leadership signal.
        weight_industry:         Weight of the industry-leadership signal.
        weight_persistence:      Weight of the RS-persistence signal.
        conflict_threshold:      Agreement below this flags conflicting signals.
    """

    rs_window: int = 60
    rs_persistence_window: int = 20
    weight_benchmark: float = 0.30
    weight_sector: float = 0.25
    weight_industry: float = 0.25
    weight_persistence: float = 0.20


@dataclass(frozen=True)
class SignalOutput:
    """Immutable output of a single relative-strength signal.

    Attributes:
        name:      Signal identifier.
        score:     Directional score in [-1, 1] (+ outperforming, - lagging).
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
        state:       Resulting relative-strength state.
        confidence:  Confidence score in [0, 100].
        evidence:    Evidence items carried into the analytics fact.
    """

    state: RelativeStrengthState
    confidence: float
    evidence: tuple[Evidence, ...]
