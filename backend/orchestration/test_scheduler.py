"""
Data Orchestration Platform tests.

Covers scheduling, dependency ordering, retries, cancellation, pause/resume,
execution history, failure propagation, handler registration and cycle/missing
dependency validation.
"""

from __future__ import annotations

import pytest

from backend.orchestration.dependency_graph import DependencyGraph
from backend.orchestration.exceptions import (
    DependencyError,
    JobAlreadyExistsError,
    JobNotFoundError,
    RetryExhaustedError,
    UnsupportedJobTypeError,
)
from backend.orchestration.executor import JobExecutor
from backend.orchestration.history import HistoryStore
from backend.orchestration.job_registry import JobRegistry
from backend.orchestration.models import (
    JOB_TYPE_CORPORATE_ACTION,
    JOB_TYPE_FUNDAMENTAL,
    JOB_TYPE_HISTORICAL_PRICE,
    JOB_TYPE_VALIDATION,
    Job,
    JobStatus,
    RetryPolicy,
    exponential_backoff,
    no_backoff,
)
from backend.orchestration.retry import RetryExecutor
from backend.orchestration.scheduler import Scheduler


def _noop_sleep(seconds: float) -> None:
    return None


def _raise(exc: Exception) -> dict:
    raise exc


class TestBackoffHelpers:
    def test_no_backoff(self):
        assert no_backoff(1) == 0.0
        assert no_backoff(5) == 0.0

    def test_exponential_backoff(self):
        backoff = exponential_backoff(base=1.0, factor=2.0)
        assert backoff(1) == 1.0
        assert backoff(2) == 2.0
        assert backoff(3) == 4.0

    def test_retry_policy_defaults(self):
        policy = RetryPolicy()
        assert policy.max_attempts == 1
        assert policy.backoff is no_backoff
        assert policy.retryable_exceptions == (Exception,)


class TestJobRegistry:
    def test_register_and_get(self):
        reg = JobRegistry()
        reg.register("T", lambda job: {"ok": True})
        handler = reg.get("T")
        assert reg.get("T") is handler
        assert reg.is_registered("T") is True
        assert reg.is_registered("X") is False

    def test_registered_types(self):
        reg = JobRegistry()
        reg.register("A", lambda job: {})
        reg.register("B", lambda job: {})
        assert reg.registered_types() == ("A", "B")

    def test_get_unknown_raises(self):
        reg = JobRegistry()
        with pytest.raises(UnsupportedJobTypeError):
            reg.get("MISSING")


class TestRetryExecutor:
    def test_success_first_try(self):
        exec = RetryExecutor(RetryPolicy(max_attempts=3))
        calls = []
        result = exec.execute(lambda: calls.append(1) or "done")
        assert result == "done"
        assert exec.attempts_used == 1
        assert len(calls) == 1

    def test_retry_then_success(self):
        policy = RetryPolicy(max_attempts=3, backoff=no_backoff)
        exec = RetryExecutor(policy, sleep=_noop_sleep)
        attempts: list[int] = []

        def flaky():
            attempts.append(len(attempts) + 1)
            if len(attempts) < 3:
                raise ValueError("transient")
            return "ok"

        recorded = []
        result = exec.execute(
            flaky,
            on_attempt=lambda a, exc, will: recorded.append((a, exc, will)),
        )
        assert result == "ok"
        assert exec.attempts_used == 3
        assert len(attempts) == 3
        assert recorded[0][2] is True
        assert recorded[-1][1] is None
        assert recorded[-1][2] is False

    def test_non_retryable_raises_immediately(self):
        policy = RetryPolicy(
            max_attempts=4,
            retryable_exceptions=(KeyError,),
            backoff=no_backoff,
        )
        exec = RetryExecutor(policy, sleep=_noop_sleep)
        with pytest.raises(ValueError):
            exec.execute(lambda: (_ for _ in ()).throw(ValueError("boom")))
        assert exec.attempts_used == 1

    def test_retry_exhausted(self):
        policy = RetryPolicy(max_attempts=2, backoff=no_backoff)
        exec = RetryExecutor(policy, sleep=_noop_sleep)

        def always_fail():
            raise RuntimeError("nope")

        with pytest.raises(RetryExhaustedError) as excinfo:
            exec.execute(always_fail)
        assert exec.attempts_used == 2
        assert excinfo.value.max_attempts == 2
        assert len(excinfo.value.errors) == 2

    def test_backoff_sleep_invoked(self):
        sleeps: list[float] = []
        policy = RetryPolicy(
            max_attempts=3,
            backoff=exponential_backoff(base=0.5, factor=2.0),
        )
        exec = RetryExecutor(policy, sleep=lambda s: sleeps.append(s))

        def fail_once():
            if len(sleeps) < 2:
                raise OSError("x")
            return "ok"

        result = exec.execute(fail_once)
        assert result == "ok"
        assert sleeps == [0.5, 1.0]


class TestDependencyGraph:
    def test_add_and_queries(self):
        g = DependencyGraph()
        g.add_job("B", ("A",))
        g.add_job("A")
        assert g.has_node("A") and g.has_node("B")
        assert g.dependencies_of("B") == ("A",)
        assert g.dependents_of("A") == ("B",)
        assert g.dependencies_of("A") == ()

    def test_add_dependency(self):
        g = DependencyGraph()
        g.add_dependency("C", "B")
        g.add_dependency("B", "A")
        assert g.dependencies_of("C") == ("B",)
        assert g.dependents_of("A") == ("B",)

    def test_topological_order_chain(self):
        g = DependencyGraph()
        g.add_job("C", ("B",))
        g.add_job("B", ("A",))
        g.add_job("A")
        assert g.topological_order() == ["A", "B", "C"]

    def test_topological_order_diamond(self):
        g = DependencyGraph()
        g.add_job("D", ("B", "C"))
        g.add_job("B", ("A",))
        g.add_job("C", ("A",))
        g.add_job("A")
        order = g.topological_order()
        assert order.index("A") < order.index("B") < order.index("D")
        assert order.index("A") < order.index("C") < order.index("D")

    def test_cycle_detection(self):
        g = DependencyGraph()
        g.add_job("A", ("B",))
        g.add_job("B", ("A",))
        with pytest.raises(DependencyError):
            g.topological_order()
        cycle = g._find_cycle()
        assert "A" in cycle and "B" in cycle

    def test_validate_passes_acyclic(self):
        g = DependencyGraph()
        g.add_job("B", ("A",))
        g.add_job("A")
        g.validate()

    def test_find_cycle_acyclic_returns_empty(self):
        g = DependencyGraph()
        g.add_job("C", ("B",))
        g.add_job("B", ("A",))
        g.add_job("A")
        assert g._find_cycle() == []


class TestHistoryStore:
    def test_record_and_get(self):
        store = HistoryStore()
        entry = _history_entry("J1", 1)
        store.record(entry)
        assert store.get("J1") == (entry,)
        assert store.all() == (entry,)
        assert store.latest("J1") is entry

    def test_latest_empty(self):
        store = HistoryStore()
        assert store.latest("NOPE") is None
        assert store.get("NOPE") == ()

    def test_clear(self):
        store = HistoryStore()
        store.record(_history_entry("J1", 1))
        store.clear()
        assert store.all() == ()


def _history_entry(job_id, attempt):
    from datetime import UTC, datetime

    from backend.orchestration.models import ExecutionHistory, JobStatus

    now = datetime.now(UTC)
    return ExecutionHistory(
        job_id=job_id,
        attempt=attempt,
        status=JobStatus.SUCCESS,
        start_time=now,
        end_time=now,
        duration=0.0,
        error=None,
        timestamp=now,
    )


class TestJobExecutor:
    def test_success(self):
        reg = JobRegistry()
        reg.register("T", lambda job: {"rows": 10})
        store = HistoryStore()
        exec = JobExecutor(reg, store, sleep=_noop_sleep)
        result = exec.execute(Job(job_id="J", job_type="T"))
        assert result.status is JobStatus.SUCCESS
        assert result.output == {"rows": 10}
        assert result.attempt == 1
        assert result.duration >= 0
        assert len(store.get("J")) == 1

    def test_failure(self):
        reg = JobRegistry()
        reg.register("T", lambda job: _raise(RuntimeError("fail")))
        store = HistoryStore()
        exec = JobExecutor(reg, store, sleep=_noop_sleep)
        result = exec.execute(Job(job_id="J", job_type="T", retry_policy=RetryPolicy(max_attempts=1)))
        assert result.status is JobStatus.FAILED
        assert "fail" in (result.error or "")
        assert len(store.get("J")) == 1

    def test_retry_records_each_attempt(self):
        reg = JobRegistry()
        calls = {"n": 0}

        def flaky(job):
            calls["n"] += 1
            if calls["n"] < 2:
                raise ValueError("retry")
            return {"ok": True}

        reg.register("T", flaky)
        store = HistoryStore()
        exec = JobExecutor(reg, store, sleep=_noop_sleep)
        policy = RetryPolicy(max_attempts=3, backoff=no_backoff)
        result = exec.execute(Job(job_id="J", job_type="T", retry_policy=policy))
        assert result.status is JobStatus.SUCCESS
        assert len(store.get("J")) == 2

    def test_non_dict_output_wrapped(self):
        reg = JobRegistry()
        reg.register("T", lambda job: 42)
        exec = JobExecutor(reg, HistoryStore(), sleep=_noop_sleep)
        result = exec.execute(Job(job_id="J", job_type="T"))
        assert result.output == {"result": 42}


def _make_scheduler(handlers, jobs, sleep=_noop_sleep):
    reg = JobRegistry()
    for job_type, handler in handlers.items():
        reg.register(job_type, handler)
    sched = Scheduler(registry=reg, sleep=sleep)
    sched.schedule(jobs)
    return sched


class TestSchedulerScheduling:
    def test_register_and_schedule(self):
        sched = Scheduler()
        sched.schedule([Job(job_id="A", job_type="T")])
        assert sched.get_job("A") is not None
        assert sched.status_of("A") is JobStatus.PENDING

    def test_duplicate_raises(self):
        sched = Scheduler()
        sched.register_job(Job(job_id="A", job_type="T"))
        with pytest.raises(JobAlreadyExistsError):
            sched.register_job(Job(job_id="A", job_type="T"))

    def test_cancel_unknown_raises(self):
        sched = Scheduler()
        with pytest.raises(JobNotFoundError):
            sched.cancel("X")

    def test_pause_resume_unknown_raises(self):
        sched = Scheduler()
        with pytest.raises(JobNotFoundError):
            sched.pause("X")
        with pytest.raises(JobNotFoundError):
            sched.resume("X")


class TestSchedulerRun:
    def test_single_job_success(self):
        order: list[str] = []
        sched = _make_scheduler(
            {"T": lambda job: order.append(job.job_id) or {"ok": True}},
            [Job(job_id="A", job_type="T")],
        )
        results = sched.run()
        assert results["A"].status is JobStatus.SUCCESS
        assert order == ["A"]

    def test_dependency_ordering_chain(self):
        order: list[str] = []
        sched = _make_scheduler(
            {"T": lambda job: order.append(job.job_id)},
            [
                Job(job_id="C", job_type="T", dependencies=("B",)),
                Job(job_id="B", job_type="T", dependencies=("A",)),
                Job(job_id="A", job_type="T"),
            ],
        )
        sched.run()
        assert order == ["A", "B", "C"]

    def test_pipeline_standard_job_types(self):
        order: list[str] = []
        handlers = {
            JOB_TYPE_HISTORICAL_PRICE: lambda job: order.append(job.job_type),
            JOB_TYPE_CORPORATE_ACTION: lambda job: order.append(job.job_type),
            JOB_TYPE_FUNDAMENTAL: lambda job: order.append(job.job_type),
            JOB_TYPE_VALIDATION: lambda job: order.append(job.job_type),
        }
        sched = _make_scheduler(
            handlers,
            [
                Job(job_id="val", job_type=JOB_TYPE_VALIDATION, dependencies=("fund",)),
                Job(job_id="fund", job_type=JOB_TYPE_FUNDAMENTAL, dependencies=("corp",)),
                Job(job_id="corp", job_type=JOB_TYPE_CORPORATE_ACTION, dependencies=("hist",)),
                Job(job_id="hist", job_type=JOB_TYPE_HISTORICAL_PRICE),
            ],
        )
        results = sched.run()
        assert order == [
            JOB_TYPE_HISTORICAL_PRICE,
            JOB_TYPE_CORPORATE_ACTION,
            JOB_TYPE_FUNDAMENTAL,
            JOB_TYPE_VALIDATION,
        ]
        assert all(r.status is JobStatus.SUCCESS for r in results.values())

    def test_retry_in_scheduler(self):
        calls = {"n": 0}

        def flaky(job):
            calls["n"] += 1
            if calls["n"] < 2:
                raise ValueError("retry me")
            return {"done": True}

        sched = _make_scheduler(
            {"T": flaky},
            [Job(job_id="A", job_type="T", retry_policy=RetryPolicy(max_attempts=3, backoff=no_backoff))],
        )
        results = sched.run()
        assert results["A"].status is JobStatus.SUCCESS
        assert results["A"].attempt == 2

    def test_failure_propagation(self):
        sched = _make_scheduler(
            {
                "GOOD": lambda job: {},
                "BAD": lambda job: _raise(RuntimeError("boom")),
            },
            [
                Job(job_id="A", job_type="BAD"),
                Job(job_id="B", job_type="GOOD", dependencies=("A",)),
                Job(job_id="C", job_type="GOOD", dependencies=("B",)),
            ],
        )
        results = sched.run()
        assert results["A"].status is JobStatus.FAILED
        assert results["B"].status is JobStatus.SKIPPED
        assert results["C"].status is JobStatus.SKIPPED

    def test_cancellation_propagates(self):
        sched = _make_scheduler(
            {"T": lambda job: {}},
            [
                Job(job_id="A", job_type="T"),
                Job(job_id="B", job_type="T", dependencies=("A",)),
                Job(job_id="C", job_type="T", dependencies=("B",)),
            ],
        )
        sched.cancel("B")
        results = sched.run()
        assert results["A"].status is JobStatus.SUCCESS
        assert results["B"].status is JobStatus.CANCELLED
        assert results["C"].status is JobStatus.SKIPPED

    def test_pause_then_resume(self):
        order: list[str] = []
        sched = _make_scheduler(
            {"T": lambda job: order.append(job.job_id)},
            [
                Job(job_id="A", job_type="T"),
                Job(job_id="B", job_type="T", dependencies=("A",)),
                Job(job_id="C", job_type="T", dependencies=("B",)),
            ],
        )
        sched.pause("B")
        results = sched.run()
        assert results["A"].status is JobStatus.SUCCESS
        assert "B" not in results
        assert results["C"].status is JobStatus.SKIPPED
        assert order == ["A"]

        sched.resume("B")
        order.clear()
        results2 = sched.run()
        assert results2["B"].status is JobStatus.SUCCESS
        assert results2["C"].status is JobStatus.SUCCESS
        assert order == ["A", "B", "C"]

    def test_missing_dependency_raises(self):
        sched = _make_scheduler(
            {"T": lambda job: {}},
            [Job(job_id="A", job_type="T", dependencies=("GHOST",))],
        )
        with pytest.raises(DependencyError):
            sched.run()

    def test_cycle_raises(self):
        sched = _make_scheduler(
            {"T": lambda job: {}},
            [
                Job(job_id="A", job_type="T", dependencies=("B",)),
                Job(job_id="B", job_type="T", dependencies=("A",)),
            ],
        )
        with pytest.raises(DependencyError):
            sched.run()

    def test_cancellation_diamond_propagates(self):
        sched = _make_scheduler(
            {"T": lambda job: {}},
            [
                Job(job_id="A", job_type="T"),
                Job(job_id="B", job_type="T", dependencies=("A",)),
                Job(job_id="C", job_type="T", dependencies=("A",)),
                Job(job_id="D", job_type="T", dependencies=("B", "C")),
            ],
        )
        sched.cancel("A")
        results = sched.run()
        assert results["A"].status is JobStatus.CANCELLED
        assert results["B"].status is JobStatus.SKIPPED
        assert results["C"].status is JobStatus.SKIPPED
        assert results["D"].status is JobStatus.SKIPPED

    def test_history_persisted(self):
        sched = _make_scheduler(
            {"T": lambda job: {}},
            [Job(job_id="A", job_type="T", retry_policy=RetryPolicy(max_attempts=2, backoff=no_backoff))],
        )
        sched.run()
        assert len(sched.history().get("A")) == 1
        assert sched.history().latest("A") is not None

    def test_results_accessor(self):
        sched = _make_scheduler({"T": lambda job: {}}, [Job(job_id="A", job_type="T")])
        sched.run()
        assert "A" in sched.results()
