"""Trend engine immutable models.

Defines the trend-state enumeration and the intermediate result models passed
between signals, evaluators and the scorer. None of these expose raw indicator
values; they carry only scores, states and evidence.
"""

from __future__ import annotations

from dataclasses import dataclass
from enum import StrEnum

from backend.analytics.trend.evidence import Evidence


class TrendState(StrEnum):
    """Trend classification produced by the engine."""

    STRONG_BULLISH = "Strong Bullish"
    BULLISH = "Bullish"
    NEUTRAL = "Neutral"
    BEARISH = "Bearish"
    STRONG_BEARISH = "Strong Bearish"


@dataclass(frozen=True)
class SignalOutput:
    """Immutable output of a single trend signal.

    Attributes:
        name:      Signal identifier.
        score:     Directional score in [-1, 1] (+ bullish, - bearish).
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
        state:       Resulting trend state.
        confidence:  Confidence score in [0, 100].
        evidence:    Evidence items carried into the analytics fact.
    """

    state: TrendState
    confidence: float
    evidence: tuple[Evidence, ...]
