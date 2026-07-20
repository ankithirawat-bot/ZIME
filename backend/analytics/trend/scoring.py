"""
Confidence scoring.

Converts an :class:`EvaluatorResult` into a :class:`TrendState` and a
confidence score in [0, 100]. Conflicting signals are downgraded one level
toward neutral and have their confidence capped, so no single signal nor a
split verdict can produce an over-confident call.
"""

from __future__ import annotations

from backend.analytics.trend.models import EvaluatorResult, ScoringResult, TrendState

_ORDER = [
    TrendState.STRONG_BEARISH,
    TrendState.BEARISH,
    TrendState.NEUTRAL,
    TrendState.BULLISH,
    TrendState.STRONG_BULLISH,
]


def _state_from_score(score: float) -> TrendState:
    if score >= 0.6:
        return TrendState.STRONG_BULLISH
    if score >= 0.2:
        return TrendState.BULLISH
    if score > -0.2:
        return TrendState.NEUTRAL
    if score > -0.6:
        return TrendState.BEARISH
    return TrendState.STRONG_BEARISH


def _downgrade(state: TrendState) -> TrendState:
    index = _ORDER.index(state)
    neutral = _ORDER.index(TrendState.NEUTRAL)
    if index < neutral:
        return _ORDER[index + 1]
    if index > neutral:
        return _ORDER[index - 1]
    return TrendState.NEUTRAL


class TrendScorer:
    """Maps an evaluator result to a trend state and confidence."""

    def score(self, result: EvaluatorResult, completeness: float) -> ScoringResult:
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
