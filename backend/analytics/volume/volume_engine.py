"""
Volume Engine.

Orchestrates signal providers, an evaluator and a scorer to produce an
immutable :class:`AnalyticsFact`. The public API exposes only the fact;
indicator values are computed internally and never returned.
"""

from __future__ import annotations

from backend.analytics.base_engine import AnalyticsEngineBase
from backend.analytics.volume.evaluators import WeightedEvaluator
from backend.analytics.volume.scoring import VolumeScorer
from backend.analytics.volume.signals import SignalRegistry, build_default_signal_registry


class VolumeEngine(AnalyticsEngineBase):
    """Determines volume participation from multiple independent signals."""

    def __init__(
        self,
        registry: SignalRegistry | None = None,
        evaluator: WeightedEvaluator | None = None,
        scorer: VolumeScorer | None = None,
    ) -> None:
        super().__init__(
            registry=registry or build_default_signal_registry(),
            evaluator=evaluator or WeightedEvaluator(),
            scorer=scorer or VolumeScorer(),
        )

    def _engine_name(self) -> str:
        return "Volume"
