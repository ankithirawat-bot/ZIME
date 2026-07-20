"""
Confidence scoring.

Converts an :class:`EvaluatorResult` into a :class:`MomentumState` and a
confidence score in [0, 100]. Conflicting signals are downgraded one level
toward neutral and have their confidence capped, so no single signal nor a
split verdict can produce an over-confident call.
"""

from __future__ import annotations

from backend.analytics.momentum.models import EvaluatorResult, MomentumState, ScoringResult

_ORDER = [
    MomentumState.VERY_WEAK,
    MomentumState.WEAK,
    MomentumState.NEUTRAL,
    MomentumState.STRONG,
    MomentumState.VERY_STRONG,
]


def _state_from_score(score: float) -> MomentumState:
    if score >= 0.6:
        return MomentumState.VERY_STRONG
    if score >= 0.2:
        return MomentumState.STRONG
    if score > -0.2:
        return MomentumState.NEUTRAL
    if score > -0.6:
        return MomentumState.WEAK
    return MomentumState.VERY_WEAK


def _downgrade(state: MomentumState) -> MomentumState:
    index = _ORDER.index(state)
    neutral = _ORDER.index(MomentumState.NEUTRAL)
    if index < neutral:
        return _ORDER[index + 1]
    if index > neutral:
        return _ORDER[index - 1]
    return MomentumState.NEUTRAL


class MomentumScorer:
    """Maps an evaluator result to a momentum state and confidence."""

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
