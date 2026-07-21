"""
Job registry.

Maps job types to handler callables via registration. No switch statements:
dispatch is data-driven through the handler dictionary.
"""

from __future__ import annotations

from collections.abc import Callable
from typing import Any

from backend.orchestration.exceptions import UnsupportedJobTypeError
from backend.orchestration.models import Job

JobHandler = Callable[[Job], dict[str, Any]]


class JobRegistry:
    """Registry of job-type -> handler mappings."""

    def __init__(self) -> None:
        self._handlers: dict[str, JobHandler] = {}

    def register(self, job_type: str, handler: JobHandler) -> None:
        """Register a handler for a job type.

        Args:
            job_type: Key used by :class:`Job.job_type`.
            handler:  Callable invoked with the Job, returns a dict.
        """
        self._handlers[job_type] = handler

    def get(self, job_type: str) -> JobHandler:
        """Return the handler for a job type.

        Raises:
            UnsupportedJobTypeError: If no handler is registered.
        """
        handler = self._handlers.get(job_type)
        if handler is None:
            raise UnsupportedJobTypeError(job_type)
        return handler

    def is_registered(self, job_type: str) -> bool:
        """Return True when a handler exists for the job type."""
        return job_type in self._handlers

    def registered_types(self) -> tuple[str, ...]:
        """Return all registered job type keys."""
        return tuple(sorted(self._handlers))
