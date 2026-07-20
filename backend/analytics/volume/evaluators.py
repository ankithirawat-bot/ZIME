"""
Signal evaluators.

Combine independent :class:`SignalOutput` values into a single
:class:`EvaluatorResult`. No single signal determines the final volume state:
the weighted evaluator blends every available signal and quantifies how much
the signals agree, flagging conflict when they diverge.
"""

from __future__ import annotations

from backend.analytics.models import TrendConfig
from backend.analytics.volume.models import EvaluatorResult, SignalOutput

_WEIGHT_KEYS = {
    "relative_volume": "weight_relative_volume",
    "volume_trend": "weight_volume_trend",
    "accumulation": "weight_accumulation",
    "consistency": "weight_consistency",
}


class WeightedEvaluator:
    """Blends signal scores using configured weights.

    Computes a weighted combined score, a direction-agreement measure among
    signals that express a view, and a conflict flag when agreement drops
    below the configured threshold.
    """

    def __init__(self, conflict_threshold: float = 0.5) -> None:
        self._conflict_threshold = conflict_threshold

    def evaluate(
        self, outputs: list[SignalOutput], config: TrendConfig
    ) -> EvaluatorResult:
        """Combine signal outputs.

        Args:
            outputs: Signal outputs from the registry.
            config:  Volume configuration (provides weights).

        Returns:
            EvaluatorResult with combined score, agreement and evidence.
        """
        available = [o for o in outputs if o.available]
        total = len(outputs)
        if not available:
            return EvaluatorResult(0.0, 0.0, 0, total, (), True)

        weights = [
            getattr(config, _WEIGHT_KEYS.get(o.name, "weight_relative_volume"))
            for o in available
        ]
        weight_sum = sum(weights)
        if weight_sum == 0:
            combined = 0.0
        else:
            combined = sum(o.score * w for o, w in zip(available, weights)) / weight_sum
        combined = max(-1.0, min(1.0, combined))

        directional = [o.score for o in available if abs(o.score) >= 0.05]
        if len(directional) < 2:
            agreement = 1.0
        else:
            pairs = [
                (a, b)
                for i, a in enumerate(directional)
                for b in directional[i + 1:]
            ]
            same = sum(1 for a, b in pairs if (a > 0) == (b > 0))
            agreement = same / len(pairs)

        conflict = agreement < self._conflict_threshold
        evidence = tuple(e for o in available for e in o.evidence)
        return EvaluatorResult(
            combined_score=combined,
            agreement=agreement,
            available_count=len(available),
            total_count=total,
            evidence=evidence,
            conflict=conflict,
        )
