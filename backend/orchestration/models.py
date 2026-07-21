"""
Orchestration immutable models.

All runtime state is captured by immutable frozen dataclasses. A :class:`Job`
is a *definition* (id, type, dependencies, parameters, retry policy) and never
mutates; its evolving status lives in :class:`JobResult` and
:class:`ExecutionHistory` records instead.
"""

from __future__ import annotations

from collections.abc import Callable
from dataclasses import dataclass, field
from datetime import datetime
from enum import Enum
from typing import Any

JOB_TYPE_HISTORICAL_PRICE = "HistoricalPriceUpdate"
JOB_TYPE_CORPORATE_ACTION = "CorporateActionUpdate"
JOB_TYPE_FUNDAMENTAL = "FundamentalUpdate"
JOB_TYPE_VALIDATION = "ValidationRun"


class JobStatus(Enum):
    """Lifecycle status of a job execution."""

    PENDING = "pending"
    RUNNING = "running"
    SUCCESS = "success"
    FAILED = "failed"
    CANCELLED = "cancelled"
    SKIPPED = "skipped"


def no_backoff(attempt: int) -> float:
    """Default backoff: no delay between attempts."""
    return 0.0


def exponential_backoff(base: float = 1.0, factor: float = 2.0) -> Callable[[int], float]:
    """Build an exponential backoff callable (base * factor ** (attempt - 1))."""

    def _backoff(attempt: int) -> float:
        return base * (factor ** max(attempt - 1, 0))

    return _backoff


@dataclass(frozen=True)
class RetryPolicy:
    """Immutable retry configuration for a job.

    Attributes:
        max_attempts:        Maximum number of execution attempts.
        backoff:             Callable mapping attempt number -> wait seconds.
        retryable_exceptions: Tuple of exception types eligible for retry.
    """

    max_attempts: int = 1
    backoff: Callable[[int], float] = no_backoff
    retryable_exceptions: tuple[type[Exception], ...] = (Exception,)


@dataclass(frozen=True)
class Job:
    """Immutable job definition.

    Attributes:
        job_id:         Unique job identifier.
        job_type:       Registered handler key (e.g. "HistoricalPriceUpdate").
        name:           Human readable name.
        dependencies:   Job ids that must succeed before this job runs.
        retry_policy:   Retry configuration.
        params:         Arbitrary parameters passed to the handler.
    """

    job_id: str
    job_type: str
    name: str = ""
    dependencies: tuple[str, ...] = ()
    retry_policy: RetryPolicy = field(default_factory=RetryPolicy)
    params: dict[str, Any] = field(default_factory=dict)


@dataclass(frozen=True)
class JobResult:
    """Immutable outcome of a single job execution.

    Attributes:
        job_id:     Identifier of the executed job.
        status:     Final status of the execution.
        attempt:    Number of attempts consumed.
        start_time: Execution start timestamp.
        end_time:   Execution end timestamp.
        duration:   Wall-clock duration in seconds.
        error:      Error message if the job failed, else None.
        output:     Handler return value (dict).
    """

    job_id: str
    status: JobStatus
    attempt: int
    start_time: datetime
    end_time: datetime
    duration: float
    error: str | None = None
    output: dict[str, Any] = field(default_factory=dict)


@dataclass(frozen=True)
class ExecutionHistory:
    """Immutable record of one execution attempt.

    Attributes:
        job_id:     Identifier of the executed job.
        attempt:    Attempt number (1-based).
        status:     Status recorded for this attempt.
        start_time: Execution start timestamp.
        end_time:   Execution end timestamp (None if still running).
        duration:   Wall-clock duration in seconds (None if still running).
        error:      Error message if the attempt failed, else None.
        timestamp:  When this history record was persisted.
    """

    job_id: str
    attempt: int
    status: JobStatus
    start_time: datetime
    end_time: datetime | None
    duration: float | None
    error: str | None
    timestamp: datetime
