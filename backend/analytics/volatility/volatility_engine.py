"""
Volatility Engine.

Orchestrates signal providers, an evaluator and a scorer to produce an
immutable :class:`AnalyticsFact`. The public API exposes only the fact;
indicator values are computed internally and never returned.
"""

from __future__ import annotations

from backend.analytics.base_engine import AnalyticsEngineBase
from backend.analytics.models import AnalyticsContext
from backend.analytics.volatility.evaluators import WeightedEvaluator
from backend.analytics.volatility.exceptions import VolatilityError
from backend.analytics.volatility.scoring import VolatilityScorer
from backend.analytics.volatility.signals import SignalRegistry, build_default_signal_registry


class VolatilityEngine(AnalyticsEngineBase):
    """Determines volatility regime from multiple independent signals."""

    def __init__(
        self,
        registry: SignalRegistry | None = None,
        evaluator: WeightedEvaluator | None = None,
        scorer: VolatilityScorer | None = None,
    ) -> None:
        super().__init__(
            registry=registry or build_default_signal_registry(),
            evaluator=evaluator or WeightedEvaluator(),
            scorer=scorer or VolatilityScorer(),
        )

    def _engine_name(self) -> str:
        return "Volatility"

    def _check_preconditions(self, context: AnalyticsContext) -> None:
        if not context.prices:
            raise VolatilityError("No price data provided for volatility analysis")
