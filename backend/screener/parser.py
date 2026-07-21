"""Screener parser.

Converts declarative screen definitions into executable filter trees.
Designed for future JSON/YAML support.
"""

from __future__ import annotations

from datetime import datetime
from typing import Any

from backend.screener.exceptions import InvalidScreenDefinitionError, ParserError
from backend.screener.models import (
    ComparisonOperator,
    FilterCategory,
    FilterCondition,
    FilterGroup,
    LogicalOperator,
    ScreenDefinition,
    ScreenMetadata,
)


def parse_comparison_operator(value: str) -> ComparisonOperator:
    """Parse a string into a ComparisonOperator.

    Args:
        value: Operator string.

    Returns:
        The corresponding ComparisonOperator.

    Raises:
        ParserError: If the operator string is invalid.
    """
    try:
        return ComparisonOperator(value)
    except ValueError:
        raise ParserError(f"Invalid comparison operator: {value}")


def parse_logical_operator(value: str) -> LogicalOperator:
    """Parse a string into a LogicalOperator.

    Args:
        value: Operator string.

    Returns:
        The corresponding LogicalOperator.

    Raises:
        ParserError: If the operator string is invalid.
    """
    try:
        return LogicalOperator(value.upper())
    except ValueError:
        raise ParserError(f"Invalid logical operator: {value}")


def parse_filter_category(value: str) -> FilterCategory:
    """Parse a string into a FilterCategory.

    Args:
        value: Category string.

    Returns:
        The corresponding FilterCategory.
    """
    try:
        return FilterCategory(value.lower())
    except ValueError:
        return FilterCategory.CUSTOM


def parse_condition(data: dict[str, Any]) -> FilterCondition:
    """Parse a condition dictionary into a FilterCondition.

    Args:
        data: Dictionary with 'name', 'operator', 'value' keys.

    Returns:
        A FilterCondition instance.

    Raises:
        ParserError: If the condition is invalid.
    """
    if "name" not in data:
        raise ParserError("Condition missing 'name' field")
    if "operator" not in data:
        raise ParserError("Condition missing 'operator' field")
    if "value" not in data:
        raise ParserError("Condition missing 'value' field")

    name = str(data["name"])
    operator = parse_comparison_operator(str(data["operator"]))
    value = data["value"]
    category = parse_filter_category(str(data.get("category", "custom")))
    negate = bool(data.get("negate", False))

    return FilterCondition(
        name=name,
        operator=operator,
        value=value,
        category=category,
        negate=negate,
    )


def parse_group(data: dict[str, Any]) -> FilterGroup:
    """Parse a group dictionary into a FilterGroup.

    Args:
        data: Dictionary with 'operator', 'conditions', and optional 'groups'.

    Returns:
        A FilterGroup instance.
    """
    operator = parse_logical_operator(str(data.get("operator", "AND")))

    conditions_data = data.get("conditions", [])
    conditions = tuple(parse_condition(c) for c in conditions_data)

    groups_data = data.get("groups", [])
    groups = tuple(parse_group(g) for g in groups_data)

    return FilterGroup(
        operator=operator,
        conditions=conditions,
        groups=groups,
    )


def parse_metadata(data: dict[str, Any]) -> ScreenMetadata:
    """Parse metadata dictionary into a ScreenMetadata.

    Args:
        data: Dictionary with metadata fields.

    Returns:
        A ScreenMetadata instance.
    """
    name = str(data.get("name", "Unnamed Screen"))
    description = str(data.get("description", ""))
    version = str(data.get("version", "1.0"))
    author = str(data.get("author", ""))
    tags = tuple(str(t) for t in data.get("tags", []))

    created_at_str = data.get("created_at")
    if isinstance(created_at_str, str):
        try:
            created_at = datetime.fromisoformat(created_at_str)
        except ValueError:
            created_at = datetime.now().astimezone()
    elif isinstance(created_at_str, datetime):
        created_at = created_at_str
    else:
        created_at = datetime.now().astimezone()

    return ScreenMetadata(
        name=name,
        description=description,
        version=version,
        author=author,
        created_at=created_at,
        tags=tags,
    )


def parse_screen(data: dict[str, Any]) -> ScreenDefinition:
    """Parse a complete screen definition dictionary.

    Args:
        data: Dictionary with 'metadata' and 'filters' keys.

    Returns:
        A ScreenDefinition instance.

    Raises:
        InvalidScreenDefinitionError: If the screen definition is invalid.
    """
    if "filters" not in data:
        raise InvalidScreenDefinitionError("Missing 'filters' field")

    metadata_data = data.get("metadata", {})
    metadata = parse_metadata(metadata_data)

    filters = parse_group(data["filters"])

    return ScreenDefinition(
        metadata=metadata,
        filters=filters,
    )


def parse_screen_from_list(conditions: list[dict[str, Any]]) -> ScreenDefinition:
    """Parse a simple list of conditions into a ScreenDefinition.

    Args:
        conditions: List of condition dictionaries.

    Returns:
        A ScreenDefinition with AND logic.

    Example:
        parse_screen_from_list([
            {"name": "market_cap", "operator": ">", "value": 10000},
            {"name": "roe", "operator": ">", "value": 15},
        ])
    """
    metadata = ScreenMetadata(name="Simple Screen")
    filters = FilterGroup(
        operator=LogicalOperator.AND,
        conditions=tuple(parse_condition(c) for c in conditions),
    )
    return ScreenDefinition(metadata=metadata, filters=filters)
