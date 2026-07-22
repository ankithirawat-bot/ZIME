"""
Momentum Engine.

Orchestrates signal providers, an evaluator and a scorer to produce an
immutable :class:`AnalyticsFact`. The public API exposes only the fact;
indicator values are computed internally and never returned.
"""

from __future__ import annotations

from backend.analytics.base_engine import AnalyticsEngineBase
from backend.analytics.momentum.evaluators import WeightedEvaluator
from backend.analytics.momentum.scoring import MomentumScorer
from backend.analytics.momentum.signals import SignalRegistry, build_default_signal_registry


class MomentumEngine(AnalyticsEngineBase):
    """Determines price momentum from multiple independent signals."""

    def __init__(
        self,
        registry: SignalRegistry | None = None,
        evaluator: WeightedEvaluator | None = None,
        scorer: MomentumScorer | None = None,
    ) -> None:
        super().__init__(
            registry=registry or build_default_signal_registry(),
            evaluator=evaluator or WeightedEvaluator(),
            scorer=scorer or MomentumScorer(),
        )

    def _engine_name(self) -> str:
        return "Momentum"
