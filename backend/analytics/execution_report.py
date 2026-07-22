"""
Analytics execution report.

Immutable models for per-engine and aggregate pipeline execution
telemetry.  The report captures timing, status, warnings and exception
details for every registered engine.
"""

from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime


@dataclass(frozen=True)
class EngineExecutionResult:
    """Telemetry for a single analytics engine execution.

    Attributes:
        engine_name:    Registered engine name.
        started_at:     UTC timestamp when execution began.
        finished_at:    UTC timestamp when execution completed.
        duration_ms:    Wall-clock duration in milliseconds.
        status:         Outcome — ``"SUCCESS"``, ``"FAILED"`` or ``"SKIPPED"``.
        warnings:       Human-readable warning strings.
        exception_type: Fully-qualified exception class name if failed.
    """

    engine_name: str
    started_at: datetime
    finished_at: datetime
    duration_ms: float
    status: str = "SUCCESS"
    warnings: tuple[str, ...] = ()
    exception_type: str | None = None


@dataclass(frozen=True)
class PipelineExecutionReport:
    """Aggregate execution report for a full pipeline run.

    Attributes:
        engines:         Per-engine telemetry in execution order.
        total_duration_ms: Total wall-clock duration in milliseconds.
        success_count:   Number of engines that completed successfully.
        failure_count:   Number of engines that raised recoverable errors.
        skipped_count:   Number of engines that were skipped.
    """

    engines: tuple[EngineExecutionResult, ...] = ()
    total_duration_ms: float = 0.0
    success_count: int = 0
    failure_count: int = 0
    skipped_count: int = 0
