"""
Execution history store.

Persists :class:`ExecutionHistory` records in memory. The interface is kept
deliberately small so a durable backend can be substituted later without
changing callers.
"""

from __future__ import annotations

from backend.orchestration.models import ExecutionHistory


class HistoryStore:
    """In-memory store of execution history records."""

    def __init__(self) -> None:
        self._records: list[ExecutionHistory] = []

    def record(self, entry: ExecutionHistory) -> None:
        """Append an execution history record."""
        self._records.append(entry)

    def get(self, job_id: str) -> tuple[ExecutionHistory, ...]:
        """Return all history records for a job, in insertion order."""
        return tuple(r for r in self._records if r.job_id == job_id)

    def latest(self, job_id: str) -> ExecutionHistory | None:
        """Return the most recently recorded entry for a job, if any."""
        matches = [r for r in self._records if r.job_id == job_id]
        return matches[-1] if matches else None

    def all(self) -> tuple[ExecutionHistory, ...]:
        """Return every recorded history entry in insertion order."""
        return tuple(self._records)

    def clear(self) -> None:
        """Remove all recorded history."""
        self._records.clear()
