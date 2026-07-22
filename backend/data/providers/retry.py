"""
Retry helper.

Configurable retry with exponential backoff.
Provider-agnostic — used by UpstoxClient for HTTP resilience.
"""

from __future__ import annotations

import time
from collections.abc import Callable
from dataclasses import dataclass, field

from backend.core.constants import (
    RETRY_BACKOFF_FACTOR,
    RETRY_BASE_DELAY,
    RETRY_MAX_ATTEMPTS,
    RETRY_MAX_DELAY,
)


@dataclass(frozen=True)
class RetryConfig:
    """Retry configuration.

    Attributes:
        max_attempts:      Maximum number of attempts (including first).
        base_delay:        Base delay in seconds before first retry.
        backoff_factor:    Multiplier applied to delay after each failure.
        max_delay:         Cap on retry delay in seconds.
        retryable_errors:  Exception types that trigger a retry.
    """

    max_attempts: int = RETRY_MAX_ATTEMPTS
    base_delay: float = RETRY_BASE_DELAY
    backoff_factor: float = RETRY_BACKOFF_FACTOR
    max_delay: float = RETRY_MAX_DELAY
    retryable_errors: tuple[type[Exception], ...] = field(default_factory=tuple)


@dataclass(frozen=True)
class RetryResult:
    """Outcome of a retry attempt.

    Attributes:
        success:     True if the callable succeeded.
        result:      Return value on success.
        error:       Last exception on failure.
        attempts:    Total number of attempts made.
        total_delay: Cumulative delay in seconds.
    """

    success: bool
    result: object = None
    error: Exception | None = None
    attempts: int = 0
    total_delay: float = 0.0


def execute_with_retry[T](
    fn: Callable[[], T],
    config: RetryConfig,
) -> RetryResult:
    """Execute *fn* with retry logic.

    Args:
        fn:     Callable to execute (no arguments).
        config: Retry configuration.

    Returns:
        RetryResult with outcome.
    """
    last_error: Exception | None = None
    total_delay = 0.0
    actual_attempts = 0

    for attempt in range(1, config.max_attempts + 1):
        actual_attempts = attempt
        try:
            result = fn()
            return RetryResult(
                success=True,
                result=result,
                attempts=attempt,
                total_delay=total_delay,
            )
        except Exception as exc:
            last_error = exc

            if attempt == config.max_attempts:
                break

            if not isinstance(exc, config.retryable_errors):
                break

            delay = min(
                config.base_delay * (config.backoff_factor ** (attempt - 1)),
                config.max_delay,
            )
            time.sleep(delay)
            total_delay += delay

    return RetryResult(
        success=False,
        error=last_error,
        attempts=actual_attempts,
        total_delay=total_delay,
    )


def compute_delay(
    attempt: int,
    base_delay: float = RETRY_BASE_DELAY,
    backoff_factor: float = RETRY_BACKOFF_FACTOR,
    max_delay: float = RETRY_MAX_DELAY,
) -> float:
    """Compute exponential backoff delay for a given attempt.

    Args:
        attempt:       1-indexed attempt number.
        base_delay:    Base delay in seconds.
        backoff_factor: Multiplier per attempt.
        max_delay:     Maximum delay cap.

    Returns:
        Delay in seconds.
    """
    delay = base_delay * (backoff_factor ** (attempt - 1))
    return min(delay, max_delay)
