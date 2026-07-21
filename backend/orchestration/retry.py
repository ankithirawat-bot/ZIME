"""
Retry executor.

Runs a callable according to a :class:`RetryPolicy`, honouring retryable
exception types and backoff delays. Each attempt is reported through an
optional ``on_attempt`` callback so the caller can persist history.
"""

from __future__ import annotations

from collections.abc import Callable
from time import sleep as _time_sleep
from typing import Any

from backend.orchestration.exceptions import RetryExhaustedError
from backend.orchestration.models import RetryPolicy


class RetryExecutor:
    """Executes a callable with retries defined by a policy."""

    def __init__(
        self,
        policy: RetryPolicy,
        sleep: Callable[[float], None] = _time_sleep,
    ) -> None:
        self._policy = policy
        self._sleep = sleep
        self.attempts_used = 0

    def _is_retryable(self, exc: Exception) -> bool:
        return isinstance(exc, self._policy.retryable_exceptions)

    def execute(
        self,
        func: Callable[..., Any],
        *args: Any,
        on_attempt: Callable[[int, Exception | None, bool], None] | None = None,
        **kwargs: Any,
    ) -> Any:
        """Run ``func`` honoring the retry policy.

        Args:
            func:        Callable to execute.
            *args:       Positional arguments for func.
            on_attempt:  Optional callback (attempt, exc_or_none, will_retry).
            **kwargs:    Keyword arguments for func.

        Returns:
            The return value of func on its successful attempt.

        Raises:
            RetryExhaustedError: When attempts are exhausted without success.
            Exception: When a non-retryable exception is raised.
        """
        errors: list[Exception] = []
        attempt = 0
        while attempt < self._policy.max_attempts:
            attempt += 1
            self.attempts_used = attempt
            try:
                result = func(*args, **kwargs)
            except Exception as exc:
                errors.append(exc)
                will_retry = self._is_retryable(exc) and attempt < self._policy.max_attempts
                if on_attempt is not None:
                    on_attempt(attempt, exc, will_retry)
                if not self._is_retryable(exc):
                    raise
                if will_retry:
                    wait = self._policy.backoff(attempt)
                    if wait > 0:
                        self._sleep(wait)
            else:
                if on_attempt is not None:
                    on_attempt(attempt, None, False)
                return result

        last = errors[-1] if errors else RuntimeError("no attempts executed")
        raise RetryExhaustedError(self._policy.max_attempts, last, errors) from last
