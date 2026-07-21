"""
Data orchestration exceptions.

Domain-specific errors for the orchestration platform. Every error derives
from :class:`OrchestrationError` so callers can catch the whole family.
"""

from __future__ import annotations


class OrchestrationError(Exception):
    """Base exception for all orchestration errors."""


class JobNotFoundError(OrchestrationError):
    """Raised when a referenced job does not exist."""

    def __init__(self, job_id: str) -> None:
        self.job_id = job_id
        super().__init__(f"Job not found: {job_id}")


class JobAlreadyExistsError(OrchestrationError):
    """Raised when registering a job whose id is already present."""

    def __init__(self, job_id: str) -> None:
        self.job_id = job_id
        super().__init__(f"Job already exists: {job_id}")


class UnsupportedJobTypeError(OrchestrationError):
    """Raised when no handler is registered for a job type."""

    def __init__(self, job_type: str) -> None:
        self.job_type = job_type
        super().__init__(f"Unsupported job type: {job_type}")


class DependencyError(OrchestrationError):
    """Raised when the dependency graph is invalid (cycle or missing dep)."""

    def __init__(self, message: str) -> None:
        self.message = message
        super().__init__(message)


class RetryExhaustedError(OrchestrationError):
    """Raised when a job fails after exhausting all retry attempts."""

    def __init__(
        self,
        max_attempts: int,
        last_error: Exception,
        errors: list[Exception],
    ) -> None:
        self.max_attempts = max_attempts
        self.last_error = last_error
        self.errors = errors
        super().__init__(
            f"Job failed after {max_attempts} attempt(s): {last_error}"
        )


class SchedulerError(OrchestrationError):
    """Raised for generic scheduler-level failures."""
