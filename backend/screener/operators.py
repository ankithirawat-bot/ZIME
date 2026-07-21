"""Screener operators.

Comparison and logical operators for evaluating filter conditions.
"""

from __future__ import annotations

from collections.abc import Callable
from typing import Any

from backend.screener.exceptions import InvalidOperatorError, OperatorNotFoundError
from backend.screener.models import ComparisonOperator, LogicalOperator

ComparisonFunc = Callable[[Any, Any], bool]


def _eq(actual: Any, expected: Any) -> bool:
    """Equal to."""
    return actual == expected


def _neq(actual: Any, expected: Any) -> bool:
    """Not equal to."""
    return actual != expected


def _gt(actual: Any, expected: Any) -> bool:
    """Greater than."""
    return actual > expected


def _gte(actual: Any, expected: Any) -> bool:
    """Greater than or equal to."""
    return actual >= expected


def _lt(actual: Any, expected: Any) -> bool:
    """Less than."""
    return actual < expected


def _lte(actual: Any, expected: Any) -> bool:
    """Less than or equal to."""
    return actual <= expected


def _in(actual: Any, expected: Any) -> bool:
    """Contains (membership test)."""
    if isinstance(expected, (list, tuple, set, frozenset)):
        return actual in expected
    return actual == expected


def _not_in(actual: Any, expected: Any) -> bool:
    """Not contains (negated membership test)."""
    if isinstance(expected, (list, tuple, set, frozenset)):
        return actual not in expected
    return actual != expected


def _between(actual: Any, expected: Any) -> bool:
    """Between (inclusive range)."""
    if isinstance(expected, (list, tuple)) and len(expected) == 2:
        low, high = expected
        return low <= actual <= high
    raise InvalidOperatorError("BETWEEN requires a tuple/list of (low, high)")


_COMPARISON_FUNCTIONS: dict[ComparisonOperator, ComparisonFunc] = {
    ComparisonOperator.EQ: _eq,
    ComparisonOperator.NEQ: _neq,
    ComparisonOperator.GT: _gt,
    ComparisonOperator.GTE: _gte,
    ComparisonOperator.LT: _lt,
    ComparisonOperator.LTE: _lte,
    ComparisonOperator.IN: _in,
    ComparisonOperator.NOT_IN: _not_in,
    ComparisonOperator.BETWEEN: _between,
}


class OperatorRegistry:
    """Registry of comparison operators.

    Supports custom operators for extensibility.
    """

    def __init__(self) -> None:
        self._operators: dict[ComparisonOperator, ComparisonFunc] = dict(
            _COMPARISON_FUNCTIONS
        )

    def register(self, operator: ComparisonOperator, func: ComparisonFunc) -> None:
        """Register a comparison operator.

        Args:
            operator: The operator enum value.
            func:     The comparison function.
        """
        self._operators[operator] = func

    def get(self, operator: ComparisonOperator) -> ComparisonFunc:
        """Get a comparison function by operator.

        Args:
            operator: The operator enum value.

        Returns:
            The comparison function.

        Raises:
            OperatorNotFoundError: If the operator is not registered.
        """
        if operator not in self._operators:
            raise OperatorNotFoundError(operator.value)
        return self._operators[operator]

    def is_registered(self, operator: ComparisonOperator) -> bool:
        """Check if an operator is registered."""
        return operator in self._operators

    def registered_operators(self) -> tuple[ComparisonOperator, ...]:
        """Return all registered operators."""
        return tuple(self._operators.keys())


def evaluate_comparison(
    actual: Any,
    operator: ComparisonOperator,
    expected: Any,
    registry: OperatorRegistry | None = None,
) -> bool:
    """Evaluate a comparison.

    Args:
        actual:   The actual value.
        operator: The comparison operator.
        expected: The expected value.
        registry: Optional custom registry.

    Returns:
        True if the comparison holds.
    """
    reg = registry or OperatorRegistry()
    func = reg.get(operator)
    return func(actual, expected)


def evaluate_logical(
    results: tuple[bool, ...],
    operator: LogicalOperator,
) -> bool:
    """Evaluate logical combination of results.

    Args:
        results:  Tuple of boolean results.
        operator: The logical operator.

    Returns:
        Combined boolean result.
    """
    if not results:
        return True

    if operator is LogicalOperator.AND:
        return all(results)
    if operator is LogicalOperator.OR:
        return any(results)
    if operator is LogicalOperator.NOT:
        return not all(results)
    return True
