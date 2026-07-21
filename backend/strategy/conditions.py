"""Strategy conditions.

Comparison and logical operators for evaluating strategy conditions.
"""

from __future__ import annotations

from typing import Any

from backend.strategy.exceptions import InvalidConditionError
from backend.strategy.models import ComparisonOperator, Condition, ConditionGroup, LogicalOperator


def get_nested_value(data: dict[str, Any], field_path: str) -> Any:
    """Get a value from nested dictionaries using dot notation.

    Args:
        data:       Dictionary to search.
        field_path: Dot-notation field path.

    Returns:
        The value if found, None otherwise.
    """
    parts = field_path.split(".")
    current = data
    for part in parts:
        if isinstance(current, dict):
            current = current.get(part)
        else:
            return None
    return current


def evaluate_condition(condition: Condition, data: dict[str, Any]) -> bool:
    """Evaluate a single condition.

    Args:
        condition: Condition to evaluate.
        data:      Data dictionary.

    Returns:
        True if the condition holds.
    """
    actual = get_nested_value(data, condition.field)
    expected = condition.value

    if actual is None:
        return False

    op = condition.operator
    if op is ComparisonOperator.EQ:
        return actual == expected
    if op is ComparisonOperator.NEQ:
        return actual != expected
    if op is ComparisonOperator.GT:
        return actual > expected
    if op is ComparisonOperator.GTE:
        return actual >= expected
    if op is ComparisonOperator.LT:
        return actual < expected
    if op is ComparisonOperator.LTE:
        return actual <= expected
    if op is ComparisonOperator.IN:
        if isinstance(expected, (list, tuple, set, frozenset)):
            return actual in expected
        return actual == expected
    if op is ComparisonOperator.NOT_IN:
        if isinstance(expected, (list, tuple, set, frozenset)):
            return actual not in expected
        return actual != expected
    if op is ComparisonOperator.BETWEEN:
        if isinstance(expected, (list, tuple)) and len(expected) == 2:
            return expected[0] <= actual <= expected[1]
        raise InvalidConditionError("BETWEEN requires a tuple/list of (low, high)")

    return False


def evaluate_group(group: ConditionGroup, data: dict[str, Any]) -> bool:
    """Evaluate a condition group recursively.

    Args:
        group: Condition group to evaluate.
        data:  Data dictionary.

    Returns:
        True if the group conditions are satisfied.
    """
    results: list[bool] = []

    for condition in group.conditions:
        result = evaluate_condition(condition, data)
        results.append(result)

    for subgroup in group.groups:
        result = evaluate_group(subgroup, data)
        results.append(result)

    if not results:
        combined = True
    elif group.operator is LogicalOperator.AND:
        combined = all(results)
    elif group.operator is LogicalOperator.OR:
        combined = any(results)
    else:
        combined = True

    if group.negate:
        combined = not combined

    return combined


def format_condition(condition: Condition) -> str:
    """Format a condition as a human-readable string.

    Args:
        condition: Condition to format.

    Returns:
        Formatted string.
    """
    return f"{condition.field} {condition.operator.value} {condition.value}"


def format_group(group: ConditionGroup, indent: int = 0) -> str:
    """Format a condition group as a human-readable string.

    Args:
        group:  Condition group to format.
        indent: Indentation level.

    Returns:
        Formatted string.
    """
    prefix = "  " * indent
    parts: list[str] = []

    for condition in group.conditions:
        parts.append(f"{prefix}{format_condition(condition)}")

    for subgroup in group.groups:
        parts.append(f"{prefix}({format_group(subgroup, indent + 1)})")

    op = group.operator.value
    joined = f" {op} ".join(parts) if parts else "TRUE"

    if group.negate:
        joined = f"NOT ({joined})"

    return joined
