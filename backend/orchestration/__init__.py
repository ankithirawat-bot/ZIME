"""
Data Orchestration Platform.

Schedules, orders by dependency, executes, retries and records the market
data pipeline. The architecture is handler-driven: job types map to handlers
registered in a :class:`JobRegistry`, so new job types need no code changes
elsewhere.
"""

from backend.orchestration.dependency_graph import DependencyGraph
from backend.orchestration.exceptions import (
    DependencyError,
    JobAlreadyExistsError,
    JobNotFoundError,
    OrchestrationError,
    RetryExhaustedError,
    SchedulerError,
    UnsupportedJobTypeError,
)
from backend.orchestration.executor import JobExecutor
from backend.orchestration.history import HistoryStore
from backend.orchestration.job_registry import JobHandler, JobRegistry
from backend.orchestration.models import (
    JOB_TYPE_CORPORATE_ACTION,
    JOB_TYPE_FUNDAMENTAL,
    JOB_TYPE_HISTORICAL_PRICE,
    JOB_TYPE_VALIDATION,
    ExecutionHistory,
    Job,
    JobResult,
    JobStatus,
    RetryPolicy,
    exponential_backoff,
    no_backoff,
)
from backend.orchestration.retry import RetryExecutor
from backend.orchestration.scheduler import Scheduler

__all__ = [
    "DependencyError",
    "DependencyGraph",
    "ExecutionHistory",
    "Job",
    "JobAlreadyExistsError",
    "JobExecutor",
    "JobHandler",
    "JobNotFoundError",
    "JobRegistry",
    "JobResult",
    "JobStatus",
    "JOB_TYPE_CORPORATE_ACTION",
    "JOB_TYPE_FUNDAMENTAL",
    "JOB_TYPE_HISTORICAL_PRICE",
    "JOB_TYPE_VALIDATION",
    "HistoryStore",
    "OrchestrationError",
    "RetryExhaustedError",
    "RetryExecutor",
    "RetryPolicy",
    "Scheduler",
    "SchedulerError",
    "UnsupportedJobTypeError",
    "exponential_backoff",
    "no_backoff",
]
