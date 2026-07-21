"""
Confidence scoring.

Converts an :class:`EvaluatorResult` into a :class:`VolatilityState` and a
confidence score in [0, 100]. Conflicting signals are downgraded one level
toward neutral and have their confidence capped, so no single signal nor a
split verdict can produce an over-confident call.
"""

from __future__ import annotations

from backend.analytics.volatility.models import (
    EvaluatorResult,
    ScoringResult,
    VolatilityState,
)

_ORDER = [
    VolatilityState.VERY_LOW,
    VolatilityState.LOW,
    VolatilityState.NORMAL,
    VolatilityState.HIGH,
    VolatilityState.VERY_HIGH,
]


def _state_from_score(score: float) -> VolatilityState:
    if score >= 0.6:
        return VolatilityState.VERY_HIGH
    if score >= 0.2:
        return VolatilityState.HIGH
    if score > -0.2:
        return VolatilityState.NORMAL
    if score > -0.6:
        return VolatilityState.LOW
    return VolatilityState.VERY_LOW


def _downgrade(state: VolatilityState) -> VolatilityState:
    index = _ORDER.index(state)
    neutral = _ORDER.index(VolatilityState.NORMAL)
    if index < neutral:
        return _ORDER[index + 1]
    if index > neutral:
        return _ORDER[index - 1]
    return VolatilityState.NORMAL


class VolatilityScorer:
    """Maps an evaluator result to a volatility state and confidence."""

    @staticmethod
    def score(result: EvaluatorResult, completeness: float) -> ScoringResult:
        """Score the combined result.

        Args:
            result:       Combined signal outcome.
            completeness: Fraction of signals with sufficient data (0-1).

        Returns:
            ScoringResult with state, confidence and evidence.
        """
        state = _state_from_score(result.combined_score)
        magnitude = abs(result.combined_score)
        confidence = (50.0 + 50.0 * magnitude) * result.agreement * completeness

        if result.conflict:
            state = _downgrade(state)
            confidence = min(confidence, 50.0 * completeness)

        confidence = max(0.0, min(100.0, confidence))
        return ScoringResult(
            state=state,
            confidence=round(confidence, 2),
            evidence=result.evidence,
        )
