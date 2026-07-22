"""
Analytics execution strategies.

Defines pluggable execution strategies for the :class:`AnalyticsPipeline`.
Engines are fully independent (none depends on another's output), so
they can safely be executed in parallel.
"""

from __future__ import annotations

import time
from abc import ABC, abstractmethod
from concurrent.futures import ThreadPoolExecutor, as_completed
from dataclasses import dataclass
from datetime import UTC, datetime

from backend.analytics.base_engine import AnalyticsEngineBase
from backend.analytics.models import AnalyticsContext, AnalyticsFact


@dataclass(frozen=True)
class EngineTask:
    """Immutable result of executing a single analytics engine.

    Attributes:
        engine_name:    Registered engine name.
        fact:           Resulting AnalyticsFact, or ``None`` on failure.
        error:          Human-readable error message, or ``None``.
        exception_type: Fully-qualified exception class, or ``None``.
        warnings:       Warning strings extracted from the fact metadata.
        started_at:     UTC timestamp when execution began.
        finished_at:    UTC timestamp when execution finished.
        duration_s:     Wall-clock duration in seconds.
    """

    engine_name: str
    fact: AnalyticsFact | None
    error: str | None
    exception_type: str | None
    warnings: tuple[str, ...]
    started_at: datetime
    finished_at: datetime
    duration_s: float


class ExecutionStrategy(ABC):
    """Pluggable engine execution strategy.

    Subclasses implement :meth:`execute` which runs all registered
    engines and returns results in **registry order**.
    """

    @abstractmethod
    def execute(
        self,
        engines: tuple[AnalyticsEngineBase, ...],
        context: AnalyticsContext,
    ) -> tuple[EngineTask, ...]:
        """Execute all *engines* against *context*.

        Args:
            engines: Ordered sequence of engine instances.
            context: Normalized market data and configuration.

        Returns:
            Tuple of EngineTask results in the same order as *engines*.
        """
        ...


def _run_single(
    engine: AnalyticsEngineBase,
    context: AnalyticsContext,
) -> EngineTask:
    """Execute a single engine and capture telemetry."""
    started_at = datetime.now(UTC)
    engine_start = time.perf_counter()
    fact: AnalyticsFact | None = None
    error: str | None = None
    exception_type: str | None = None
    warnings: tuple[str, ...] = ()

    try:
        fact = engine.analyze(context)
        warnings = tuple(fact.metadata.get("warnings", []))
    except Exception as exc:
        error = str(exc)
        exception_type = f"{type(exc).__module__}.{type(exc).__qualname__}"

    finished_at = datetime.now(UTC)
    duration_s = time.perf_counter() - engine_start

    return EngineTask(
        engine_name=engine._engine_name(),
        fact=fact,
        error=error,
        exception_type=exception_type,
        warnings=warnings,
        started_at=started_at,
        finished_at=finished_at,
        duration_s=duration_s,
    )


class SequentialExecutionStrategy(ExecutionStrategy):
    """Executes engines one at a time in registry order.

    This is the default strategy and matches the original pipeline
    behaviour exactly.
    """

    def execute(
        self,
        engines: tuple[AnalyticsEngineBase, ...],
        context: AnalyticsContext,
    ) -> tuple[EngineTask, ...]:
        return tuple(_run_single(e, context) for e in engines)


class ParallelExecutionStrategy(ExecutionStrategy):
    """Executes independent engines concurrently.

    Uses a :class:`ThreadPoolExecutor` to run engines in parallel.
    Results are collated in registry order so that downstream consumers
    see deterministic ordering.

    One engine failure does **not** cancel remaining engines.

    Args:
        max_workers: Maximum thread count (defaults to number of engines).
    """

    def __init__(self, max_workers: int | None = None) -> None:
        self._max_workers = max_workers

    def execute(
        self,
        engines: tuple[AnalyticsEngineBase, ...],
        context: AnalyticsContext,
    ) -> tuple[EngineTask, ...]:
        results: dict[str, EngineTask] = {}
        order = [e._engine_name() for e in engines]

        with ThreadPoolExecutor(max_workers=self._max_workers) as pool:
            fut_map = {
                pool.submit(_run_single, e, context): e._engine_name()
                for e in engines
            }
            for future in as_completed(fut_map):
                name = fut_map[future]
                try:
                    results[name] = future.result()
                except Exception as exc:
                    # Should not happen — _run_single catches everything
                    results[name] = EngineTask(
                        engine_name=name,
                        fact=None,
                        error=f"Unexpected executor error: {exc}",
                        exception_type=f"{type(exc).__module__}.{type(exc).__qualname__}",
                        warnings=(),
                        started_at=datetime.now(UTC),
                        finished_at=datetime.now(UTC),
                        duration_s=0.0,
                    )

        # Collate in registry order
        return tuple(results[n] for n in order)
