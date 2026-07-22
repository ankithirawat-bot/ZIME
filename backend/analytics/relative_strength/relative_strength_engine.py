"""
Relative Strength Engine.

Orchestrates signal providers, an evaluator and a scorer to produce an
immutable :class:`AnalyticsFact`. The public API exposes only the fact;
indicator values are computed internally and never returned.
"""

from __future__ import annotations

from backend.analytics.base_engine import AnalyticsEngineBase
from backend.analytics.relative_strength.evaluators import WeightedEvaluator
from backend.analytics.relative_strength.scoring import RelativeStrengthScorer
from backend.analytics.relative_strength.signals import (
    SignalRegistry,
    build_default_signal_registry,
)


class RelativeStrengthEngine(AnalyticsEngineBase):
    """Determines relative strength from multiple independent signals."""

    def __init__(
        self,
        registry: SignalRegistry | None = None,
        evaluator: WeightedEvaluator | None = None,
        scorer: RelativeStrengthScorer | None = None,
    ) -> None:
        super().__init__(
            registry=registry or build_default_signal_registry(),
            evaluator=evaluator or WeightedEvaluator(),
            scorer=scorer or RelativeStrengthScorer(),
        )

    def _engine_name(self) -> str:
        return "Relative Strength"
