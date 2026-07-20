"""Momentum engine immutable models.

Defines the momentum-state enumeration, the momentum configuration and the
intermediate result models passed between signals, evaluators and the scorer.
None of these expose raw indicator values; they carry only scores, states and
evidence.
"""

from __future__ import annotations

from dataclasses import dataclass
from enum import StrEnum

from backend.analytics.models import TrendConfig
from backend.analytics.momentum.evidence import Evidence


class MomentumState(StrEnum):
    """Momentum classification produced by the engine."""

    VERY_STRONG = "Very Strong"
    STRONG = "Strong"
    NEUTRAL = "Neutral"
    WEAK = "Weak"
    VERY_WEAK = "Very Weak"


@dataclass(frozen=True)
class MomentumConfig(TrendConfig):
    """Immutable configuration for momentum analysis.

    Inherits the base analytics configuration so it remains compatible with the
    shared :class:`AnalyticsContext` contract, while adding momentum-specific
    periods, thresholds and signal weights.

    Attributes:
        roc_short_period:        Bars for the short rate-of-change window.
        roc_long_period:         Bars for the long rate-of-change window.
        acceleration_window:     Bars per slope segment for acceleration.
        momentum_persistence_threshold: Run length for full persistence credit.
        breakout_window:         Bars for the prior high/low breakout window.
        weight_roc:              Weight of the rate-of-change signal.
        weight_acceleration:     Weight of the acceleration signal.
        weight_momentum_persistence: Weight of the persistence signal.
        weight_breakout:         Weight of the breakout-continuation signal.
        conflict_threshold:      Agreement below this flags conflicting signals.
    """

    roc_short_period: int = 10
    roc_long_period: int = 30
    acceleration_window: int = 10
    momentum_persistence_threshold: int = 20
    breakout_window: int = 20
    weight_roc: float = 0.30
    weight_acceleration: float = 0.25
    weight_momentum_persistence: float = 0.20
    weight_breakout: float = 0.25


@dataclass(frozen=True)
class SignalOutput:
    """Immutable output of a single momentum signal.

    Attributes:
        name:      Signal identifier.
        score:     Directional score in [-1, 1] (+ strong momentum, - weak).
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
        state:       Resulting momentum state.
        confidence:  Confidence score in [0, 100].
        evidence:    Evidence items carried into the analytics fact.
    """

    state: MomentumState
    confidence: float
    evidence: tuple[Evidence, ...]
