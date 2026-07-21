"""Volatility engine immutable models.

Defines the volatility-state enumeration, the configuration and the
intermediate result models passed between signals, evaluators and the scorer.
None of these expose raw indicator values; they carry only scores, states and
evidence.
"""

from __future__ import annotations

from dataclasses import dataclass
from enum import StrEnum

from backend.analytics.models import TrendConfig
from backend.analytics.volatility.evidence import Evidence


class VolatilityState(StrEnum):
    """Volatility classification produced by the engine."""

    VERY_HIGH = "Very High"
    HIGH = "High"
    NORMAL = "Normal"
    LOW = "Low"
    VERY_LOW = "Very Low"


@dataclass(frozen=True)
class VolatilityConfig(TrendConfig):
    """Immutable configuration for volatility analysis.

    Inherits the base analytics configuration so it remains compatible with the
    shared :class:`AnalyticsContext` contract, while adding volatility-specific
    windows, thresholds and signal weights.

    Attributes:
        hv_window:               Returns window for historical volatility.
        vol_trend_window:        Returns per segment for the volatility trend.
        range_window:            Bars for the price-range expansion baseline.
        weight_hv:               Weight of the historical-volatility signal.
        weight_vol_trend:        Weight of the volatility-trend signal.
        weight_range_expansion:  Weight of the range-expansion signal.
        weight_persistence:      Weight of the volatility-persistence signal.
        conflict_threshold:      Agreement below this flags conflicting signals.
    """

    hv_window: int = 30
    vol_trend_window: int = 10
    range_window: int = 20
    weight_hv: float = 0.30
    weight_vol_trend: float = 0.25
    weight_range_expansion: float = 0.25
    weight_persistence: float = 0.20


@dataclass(frozen=True)
class SignalOutput:
    """Immutable output of a single volatility signal.

    Attributes:
        name:      Signal identifier.
        score:     Directional score in [-1, 1] (+ high volatility, - low).
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
        state:       Resulting volatility state.
        confidence:  Confidence score in [0, 100].
        evidence:    Evidence items carried into the analytics fact.
    """

    state: VolatilityState
    confidence: float
    evidence: tuple[Evidence, ...]
