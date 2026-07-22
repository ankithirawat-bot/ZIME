"""
Analytics Pipeline.

Orchestrates multiple analytics engines via the :class:`AnalyticsRegistry`,
collecting results and handling recoverable failures.  Engines remain
independent; the pipeline is the single orchestration point.

The pipeline does **not** import any specific engine — it works with any
engine registered in the provided registry.
"""

from __future__ import annotations

import time
from dataclasses import dataclass, field
from typing import Literal

from backend.analytics.execution import (
    ExecutionStrategy,
    ParallelExecutionStrategy,
    SequentialExecutionStrategy,
)
from backend.analytics.execution_report import (
    EngineExecutionResult,
    PipelineExecutionReport,
)
from backend.analytics.models import AnalyticsContext, AnalyticsFact
from backend.analytics.registry import (
    AnalyticsRegistry,
    create_default_registry,
)

_STRATEGY_MAP: dict[str, type[ExecutionStrategy]] = {
    "sequential": SequentialExecutionStrategy,
    "parallel": ParallelExecutionStrategy,
}


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
        report:          Structured execution telemetry report.
    """

    facts: dict[str, AnalyticsFact] = field(default_factory=dict)
    execution_order: tuple[str, ...] = ()
    execution_times: dict[str, float] = field(default_factory=dict)
    errors: dict[str, str] = field(default_factory=dict)
    total_duration: float = 0.0
    success_count: int = 0
    failure_count: int = 0
    report: PipelineExecutionReport = field(
        default_factory=PipelineExecutionReport
    )


class AnalyticsPipeline:
    """Single orchestration point for all analytics engines.

    Engines are provided by an :class:`AnalyticsRegistry` and executed in
    registration order.  Recoverable failures are captured per-engine so
    that a single engine failure does not prevent the remaining engines
    from running.

    The pipeline is fully decoupled from specific engine implementations —
    any engine registered in the registry will be executed.

    Example::

        pipeline = AnalyticsPipeline()
        result  = pipeline.run(context)
        trend   = result.facts.get("Trend")
    """

    def __init__(
        self,
        registry: AnalyticsRegistry | None = None,
        execution_strategy: ExecutionStrategy
        | Literal["sequential", "parallel"]
        | None = None,
    ) -> None:
        """Initialize the pipeline.

        Args:
            registry:           An :class:`AnalyticsRegistry` with engines to
                                execute.  If ``None`` a default registry with
                                all standard engines is created automatically.
            execution_strategy: Execution strategy instance or name.  Pass
                                ``"parallel"`` to enable concurrent execution.
                                Defaults to ``"sequential"``.
        """
        self._registry = (
            registry if registry is not None else create_default_registry()
        )
        self._strategy = _resolve_strategy(execution_strategy)

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
        engines = self._registry.ordered()

        start = time.perf_counter()
        tasks = self._strategy.execute(engines, context)
        total = time.perf_counter() - start

        facts: dict[str, AnalyticsFact] = {}
        errors: dict[str, str] = {}
        times: dict[str, float] = {}
        engine_reports: list[EngineExecutionResult] = []

        for task in tasks:
            if task.fact is not None:
                facts[task.engine_name] = task.fact
            if task.error is not None:
                errors[task.engine_name] = task.error
            times[task.engine_name] = task.duration_s

            engine_reports.append(
                EngineExecutionResult(
                    engine_name=task.engine_name,
                    started_at=task.started_at,
                    finished_at=task.finished_at,
                    duration_ms=round(task.duration_s * 1000, 2),
                    status="SUCCESS" if task.fact is not None else "FAILED",
                    warnings=task.warnings,
                    exception_type=task.exception_type,
                )
            )

        report = PipelineExecutionReport(
            engines=tuple(engine_reports),
            total_duration_ms=round(total * 1000, 2),
            success_count=len(facts),
            failure_count=len(errors),
        )

        return PipelineResult(
            facts=facts,
            execution_order=self._registry.list(),
            execution_times=times,
            errors=errors,
            total_duration=total,
            success_count=len(facts),
            failure_count=len(errors),
            report=report,
        )


def _resolve_strategy(
    strategy: ExecutionStrategy | str | None,
) -> ExecutionStrategy:
    """Resolve a strategy name or instance to an ExecutionStrategy.

    Args:
        strategy: Strategy instance, ``"sequential"``, ``"parallel"``, or
                  ``None``.

    Returns:
        ExecutionStrategy instance.
    """
    if strategy is None or strategy == "sequential":
        return SequentialExecutionStrategy()
    if isinstance(strategy, str):
        cls = _STRATEGY_MAP.get(strategy)
        if cls is None:
            raise ValueError(
                f"Unknown execution strategy: {strategy!r}. "
                f"Available: {list(_STRATEGY_MAP)}"
            )
        return cls()
    return strategy
