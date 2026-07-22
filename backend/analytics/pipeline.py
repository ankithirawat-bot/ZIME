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
from datetime import UTC, datetime

from backend.analytics.execution_report import (
    EngineExecutionResult,
    PipelineExecutionReport,
)
from backend.analytics.models import AnalyticsContext, AnalyticsFact
from backend.analytics.registry import (
    AnalyticsRegistry,
    create_default_registry,
)


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
    ) -> None:
        """Initialize the pipeline.

        Args:
            registry: An :class:`AnalyticsRegistry` with engines to execute.
                      If ``None`` a default registry with all standard
                      engines (Trend, Momentum, Volume, RS, Volatility) is
                      created automatically.
        """
        self._registry = (
            registry if registry is not None else create_default_registry()
        )

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
        engine_reports: list[EngineExecutionResult] = []
        start = time.perf_counter()

        for engine in self._registry.ordered():
            engine_start = time.perf_counter()
            engine_started = datetime.now(UTC)
            warnings: tuple[str, ...] = ()
            exception_type: str | None = None
            status: str = "SUCCESS"

            try:
                fact = engine.analyze(context)
                facts[fact.name] = fact
                warnings = tuple(fact.metadata.get("warnings", []))
            except Exception as exc:
                status = "FAILED"
                errors[engine._engine_name()] = str(exc)
                exception_type = f"{type(exc).__module__}.{type(exc).__qualname__}"

            engine_finished = datetime.now(UTC)
            duration_s = time.perf_counter() - engine_start
            times[engine._engine_name()] = duration_s

            engine_reports.append(
                EngineExecutionResult(
                    engine_name=engine._engine_name(),
                    started_at=engine_started,
                    finished_at=engine_finished,
                    duration_ms=round(duration_s * 1000, 2),
                    status=status,
                    warnings=warnings,
                    exception_type=exception_type,
                )
            )

        total = time.perf_counter() - start

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
