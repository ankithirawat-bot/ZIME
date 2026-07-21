"""
Job executor.

Runs a single :class:`Job` through its registered handler with retry support,
capturing status, timing and errors, and persisting each attempt to history.
"""

from __future__ import annotations

from collections.abc import Callable
from datetime import UTC, datetime
from time import sleep as _time_sleep

from backend.orchestration.exceptions import RetryExhaustedError
from backend.orchestration.history import HistoryStore
from backend.orchestration.job_registry import JobRegistry
from backend.orchestration.models import (
    ExecutionHistory,
    Job,
    JobResult,
    JobStatus,
)
from backend.orchestration.retry import RetryExecutor


def _now() -> datetime:
    return datetime.now(UTC)


class JobExecutor:
    """Executes individual jobs and records their history."""

    def __init__(
        self,
        registry: JobRegistry,
        history: HistoryStore,
        sleep: Callable[[float], None] = _time_sleep,
    ) -> None:
        self._registry = registry
        self._history = history
        self._sleep = sleep

    def execute(self, job: Job) -> JobResult:
        """Execute a job and return its result.

        The handler is resolved from the registry and run under the job's
        retry policy. Every attempt is persisted to the history store.
        """
        handler = self._registry.get(job.job_type)
        retry = RetryExecutor(job.retry_policy, sleep=self._sleep)
        start = _now()
        output: dict = {}
        error: str | None = None
        status = JobStatus.SUCCESS

        def _on_attempt(attempt: int, exc: Exception | None, will_retry: bool) -> None:
            end = _now()
            duration = (end - start).total_seconds()
            attempt_status = JobStatus.RUNNING if will_retry else (
                JobStatus.SUCCESS if exc is None else JobStatus.FAILED
            )
            self._history.record(
                ExecutionHistory(
                    job_id=job.job_id,
                    attempt=attempt,
                    status=attempt_status,
                    start_time=start,
                    end_time=end,
                    duration=duration,
                    error=str(exc) if exc is not None else None,
                    timestamp=end,
                )
            )

        try:
            result = retry.execute(handler, job, on_attempt=_on_attempt)
            output = result if isinstance(result, dict) else {"result": result}
        except RetryExhaustedError as exc:
            status = JobStatus.FAILED
            error = str(exc.last_error) if exc.last_error is not None else str(exc)

        end = _now()
        duration = (end - start).total_seconds()
        return JobResult(
            job_id=job.job_id,
            status=status,
            attempt=retry.attempts_used,
            start_time=start,
            end_time=end,
            duration=duration,
            error=error,
            output=output,
        )
