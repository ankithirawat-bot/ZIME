"""
Scheduler.

Orchestrates the execution of a DAG of jobs. Responsibilities: register and
schedule jobs, cancel/pause/resume individual jobs, run the whole pipeline in
dependency order, propagate failures to dependents, and expose results and
status. Execution is synchronous and in-process (no multiprocessing/queues).
"""

from __future__ import annotations

from collections.abc import Callable, Iterable
from datetime import UTC, datetime
from time import sleep as _time_sleep

from backend.orchestration.dependency_graph import DependencyGraph
from backend.orchestration.exceptions import (
    DependencyError,
    JobAlreadyExistsError,
    JobNotFoundError,
)
from backend.orchestration.executor import JobExecutor
from backend.orchestration.history import HistoryStore
from backend.orchestration.job_registry import JobRegistry
from backend.orchestration.models import (
    ExecutionHistory,
    Job,
    JobResult,
    JobStatus,
)


def _now() -> datetime:
    return datetime.now(UTC)


class Scheduler:
    """Schedules and runs jobs respecting their dependency graph."""

    def __init__(
        self,
        registry: JobRegistry | None = None,
        history: HistoryStore | None = None,
        executor: JobExecutor | None = None,
        sleep: Callable[[float], None] = _time_sleep,
    ) -> None:
        self._registry = registry or JobRegistry()
        self._history = history or HistoryStore()
        self._executor = executor or JobExecutor(
            self._registry, self._history, sleep=sleep
        )
        self._graph = DependencyGraph()
        self._jobs: dict[str, Job] = {}
        self._status: dict[str, JobStatus] = {}
        self._cancelled: set[str] = set()
        self._paused: set[str] = set()
        self._results: dict[str, JobResult] = {}

    def register_job(self, job: Job) -> None:
        """Register a single job and its dependencies."""
        if job.job_id in self._jobs:
            raise JobAlreadyExistsError(job.job_id)
        self._jobs[job.job_id] = job
        self._graph.add_job(job.job_id, job.dependencies)
        self._status[job.job_id] = JobStatus.PENDING

    def schedule(self, jobs: Iterable[Job]) -> None:
        """Register multiple jobs at once."""
        for job in jobs:
            self.register_job(job)

    def cancel(self, job_id: str) -> None:
        """Mark a job (and implicitly its dependents) as cancelled."""
        if job_id not in self._jobs:
            raise JobNotFoundError(job_id)
        self._cancelled.add(job_id)

    def pause(self, job_id: str) -> None:
        """Defer a job so it is skipped on the next run."""
        if job_id not in self._jobs:
            raise JobNotFoundError(job_id)
        self._paused.add(job_id)

    def resume(self, job_id: str) -> None:
        """Remove a job from the paused set so it can run again."""
        if job_id not in self._jobs:
            raise JobNotFoundError(job_id)
        self._paused.discard(job_id)

    def get_job(self, job_id: str) -> Job | None:
        """Return a registered job by id, or None."""
        return self._jobs.get(job_id)

    def status_of(self, job_id: str) -> JobStatus | None:
        """Return the last recorded status for a job, or None."""
        return self._status.get(job_id)

    def results(self) -> dict[str, JobResult]:
        """Return the results of the most recent run."""
        return dict(self._results)

    def history(self) -> HistoryStore:
        """Return the execution history store."""
        return self._history

    def _validate_graph(self) -> None:
        for job_id, job in self._jobs.items():
            for dep in job.dependencies:
                if dep not in self._jobs:
                    raise DependencyError(
                        f"Job '{job_id}' depends on unknown job '{dep}'"
                    )
        self._graph.validate()

    def run(self) -> dict[str, JobResult]:
        """Execute all scheduled jobs in dependency order.

        Returns:
            Mapping of job_id -> JobResult for every executed or resolved job.

        Raises:
            DependencyError: On missing dependencies or cycles.
        """
        self._validate_graph()
        order = self._graph.topological_order()
        self._results = {}
        failed: set[str] = set()

        for job_id in order:
            job = self._jobs[job_id]

            if job_id in self._results:
                continue

            if job_id in self._cancelled:
                self._resolve_terminal(job, JobStatus.CANCELLED, "Job cancelled")
                failed.add(job_id)
                self._propagate_skip(job_id, failed)
                continue

            if job_id in self._paused:
                self._status[job_id] = JobStatus.PENDING
                self._propagate_skip(job_id, failed)
                continue

            deps = self._graph.dependencies_of(job_id)
            if any(dep in failed for dep in deps):
                self._resolve_terminal(
                    job, JobStatus.SKIPPED, "Skipped: dependency did not succeed"
                )
                failed.add(job_id)
                continue

            self._status[job_id] = JobStatus.RUNNING
            result = self._executor.execute(job)
            self._results[job_id] = result
            self._status[job_id] = result.status
            if result.status is not JobStatus.SUCCESS:
                failed.add(job_id)

        return self._results

    def _propagate_skip(self, job_id: str, failed: set[str]) -> None:
        for dependent in self._graph.dependents_of(job_id):
            if dependent in self._results or dependent in failed:
                continue
            self._resolve_terminal(
                self._jobs[dependent],
                JobStatus.SKIPPED,
                "Skipped: upstream job not executed",
            )
            failed.add(dependent)
            self._propagate_skip(dependent, failed)

    def _resolve_terminal(
        self, job: Job, status: JobStatus, error: str
    ) -> None:
        now = _now()
        result = JobResult(
            job_id=job.job_id,
            status=status,
            attempt=0,
            start_time=now,
            end_time=now,
            duration=0.0,
            error=error,
            output={},
        )
        self._results[job.job_id] = result
        self._status[job.job_id] = status
        self._history.record(
            ExecutionHistory(
                job_id=job.job_id,
                attempt=0,
                status=status,
                start_time=now,
                end_time=now,
                duration=0.0,
                error=error,
                timestamp=now,
            )
        )
