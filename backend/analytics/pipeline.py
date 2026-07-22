"""
Analytics Pipeline.

Orchestrates multiple analytics engines in a configured order, collecting
results and handling recoverable failures. Engines remain independent;
the pipeline is the single orchestration point.
"""

from __future__ import annotations

import time
from dataclasses import dataclass, field

from backend.analytics.base_engine import AnalyticsEngineBase
from backend.analytics.models import AnalyticsContext, AnalyticsFact
from backend.analytics.momentum.momentum_engine import MomentumEngine
from backend.analytics.relative_strength.relative_strength_engine import (
    RelativeStrengthEngine,
)
from backend.analytics.trend.trend_engine import TrendEngine
from backend.analytics.volatility.volatility_engine import VolatilityEngine
from backend.analytics.volume.volume_engine import VolumeEngine


@dataclass(frozen=True)
class PipelineResult:
    """Immutable result from a full pipeline run.

    Attributes:
        facts:           Engine name → AnalyticsFact (only successful runs).
        execution_order: Ordered sequence of engine names.
        execution_times: Engine name → wall-clock seconds.
        errors:          Engine name → error message for failed engines.
        total_duration:  Total wall-clock seconds for the pipeline run.
        success_count:   Number of engines that completed successfully.
        failure_count:   Number of engines that raised recoverable errors.
    """

    facts: dict[str, AnalyticsFact] = field(default_factory=dict)
    execution_order: tuple[str, ...] = ()
    execution_times: dict[str, float] = field(default_factory=dict)
    errors: dict[str, str] = field(default_factory=dict)
    total_duration: float = 0.0
    success_count: int = 0
    failure_count: int = 0


class AnalyticsPipeline:
    """Single orchestration point for all analytics engines.

    Engines are registered via dependency injection and executed in a
    defined order.  Recoverable failures are captured per-engine so that
    a single engine failure does not prevent the remaining engines from
    running.

    Example::

        pipeline = AnalyticsPipeline()
        result  = pipeline.run(context)
        trend   = result.facts.get("Trend")
    """

    DEFAULT_ENGINES: tuple[AnalyticsEngineBase, ...] = (
        TrendEngine(),
        MomentumEngine(),
        VolumeEngine(),
        RelativeStrengthEngine(),
        VolatilityEngine(),
    )

    def __init__(
        self,
        engines: tuple[AnalyticsEngineBase, ...] | None = None,
    ) -> None:
        """Initialize the pipeline.

        Args:
            engines: Ordered sequence of engine instances.  If ``None`` the
                     default set is used (Trend, Momentum, Volume, RS,
                     Volatility).
        """
        self._engines = engines if engines is not None else self.DEFAULT_ENGINES

    def run(self, context: AnalyticsContext) -> PipelineResult:
        """Execute all registered engines against *context*.

        Each engine receives the same *context*.  Recoverable errors
        (e.g. insufficient data) are caught per-engine and recorded in
        ``result.errors``; other engines continue execution.

        Args:
            context: Normalized market data, corporate actions and config.

        Returns:
            PipelineResult with facts, timing and error information.
        """
        facts: dict[str, AnalyticsFact] = {}
        errors: dict[str, str] = {}
        times: dict[str, float] = {}
        start = time.perf_counter()

        for engine in self._engines:
            engine_start = time.perf_counter()
            try:
                fact = engine.analyze(context)
                facts[fact.name] = fact
            except Exception as exc:
                errors[engine._engine_name()] = str(exc)
            times[engine._engine_name()] = time.perf_counter() - engine_start

        total = time.perf_counter() - start

        order = tuple(e._engine_name() for e in self._engines)

        return PipelineResult(
            facts=facts,
            execution_order=order,
            execution_times=times,
            errors=errors,
            total_duration=total,
            success_count=len(facts),
            failure_count=len(errors),
        )
