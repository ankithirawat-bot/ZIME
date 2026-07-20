"""
Momentum Engine.

Orchestrates signal providers, an evaluator and a scorer to produce an
immutable :class:`AnalyticsFact`. The public API exposes only the fact;
indicator values are computed internally and never returned.
"""

from __future__ import annotations

from backend.analytics.models import AnalyticsContext, AnalyticsFact
from backend.analytics.momentum.evaluators import WeightedEvaluator
from backend.analytics.momentum.models import SignalOutput
from backend.analytics.momentum.scoring import MomentumScorer
from backend.analytics.momentum.signals import SignalRegistry, build_default_signal_registry


class MomentumEngine:
    """Determines price momentum from multiple independent signals."""

    def __init__(
        self,
        registry: SignalRegistry | None = None,
        evaluator: WeightedEvaluator | None = None,
        scorer: MomentumScorer | None = None,
    ) -> None:
        self._registry = registry or build_default_signal_registry()
        self._evaluator = evaluator or WeightedEvaluator()
        self._scorer = scorer or MomentumScorer()

    def analyze(self, context: AnalyticsContext) -> AnalyticsFact:
        """Analyze momentum and return an explainable analytics fact.

        Args:
            context: Normalized market data, corporate actions and config.

        Returns:
            AnalyticsFact named "Momentum" with state, confidence and evidence.
        """
        outputs: list[SignalOutput] = [
            signal(context) for signal in self._registry.all().values()
        ]
        result = self._evaluator.evaluate(outputs, context.config)
        completeness = (
            result.available_count / result.total_count if result.total_count else 0.0
        )
        scoring = self._scorer.score(result, completeness)
        warnings = self._warnings(context, outputs, result)

        metadata = {
            "combined_score": round(result.combined_score, 4),
            "agreement": round(result.agreement, 4),
            "completeness": round(completeness, 4),
            "conflict": result.conflict,
            "signal_scores": {o.name: round(o.score, 4) for o in outputs},
            "available_signals": result.available_count,
            "bars_analyzed": len(context.prices),
            "warnings": warnings,
        }

        return AnalyticsFact(
            name="Momentum",
            state=scoring.state.value,
            confidence=scoring.confidence,
            evidence=tuple(e.text for e in scoring.evidence),
            metadata=metadata,
        )

    def _warnings(
        self,
        context: AnalyticsContext,
        outputs: list[SignalOutput],
        result,
    ) -> list[str]:
        warnings: list[str] = []
        if not context.prices:
            warnings.append("No price data available")
        for output in outputs:
            if not output.available:
                warnings.append(f"Signal '{output.name}' lacked sufficient data")
        if result.conflict:
            warnings.append("Conflicting signals observed")
        if 0 < result.available_count < result.total_count:
            warnings.append("Some signals lacked sufficient data")
        return warnings
