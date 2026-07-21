"""Screener models.

Frozen dataclasses for screen definitions, filter conditions,
evaluation context, and results.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from datetime import datetime
from enum import StrEnum
from typing import Any


class FilterCategory(StrEnum):
    """Categories of screening filters."""

    FUNDAMENTAL = "fundamental"
    TECHNICAL = "technical"
    PRICE = "price"
    LIQUIDITY = "liquidity"
    CUSTOM = "custom"


class LogicalOperator(StrEnum):
    """Logical operators for combining filter conditions."""

    AND = "AND"
    OR = "OR"
    NOT = "NOT"


class ComparisonOperator(StrEnum):
    """Comparison operators for filter conditions."""

    EQ = "=="
    NEQ = "!="
    GT = ">"
    GTE = ">="
    LT = "<"
    LTE = "<="
    IN = "IN"
    NOT_IN = "NOT_IN"
    BETWEEN = "BETWEEN"


@dataclass(frozen=True)
class FilterCondition:
    """A single filter condition.

    Attributes:
        name:     Filter name (e.g. "market_cap", "trend_state").
        operator: Comparison operator.
        value:    Comparison value(s).
        category: Filter category.
        negate:   Whether to negate the result.
    """

    name: str
    operator: ComparisonOperator
    value: Any
    category: FilterCategory = FilterCategory.CUSTOM
    negate: bool = False


@dataclass(frozen=True)
class FilterGroup:
    """A group of filter conditions combined with logical operators.

    Attributes:
        operator: Logical operator combining conditions.
        conditions: Individual filter conditions.
        groups: Nested filter groups.
    """

    operator: LogicalOperator = LogicalOperator.AND
    conditions: tuple[FilterCondition, ...] = field(default_factory=tuple)
    groups: tuple[FilterGroup, ...] = field(default_factory=tuple)


@dataclass(frozen=True)
class ScreenMetadata:
    """Metadata for a screen definition.

    Attributes:
        name:        Screen name.
        description: Screen description.
        version:     Schema version.
        author:      Screen author.
        created_at:  Creation timestamp.
        tags:        Searchable tags.
    """

    name: str
    description: str = ""
    version: str = "1.0"
    author: str = ""
    created_at: datetime = field(default_factory=lambda: datetime.now().astimezone())
    tags: tuple[str, ...] = field(default_factory=tuple)


@dataclass(frozen=True)
class ScreenDefinition:
    """Complete screen definition.

    Attributes:
        metadata: Screen metadata.
        filters:  Root filter group.
    """

    metadata: ScreenMetadata
    filters: FilterGroup


@dataclass(frozen=True)
class EvaluationContext:
    """Context for evaluating a symbol against a screen.

    Attributes:
        symbol:           Ticker symbol.
        exchange:         Exchange identifier.
        data:             Symbol data dictionary.
        fundamentals:     Fundamental metrics.
        technicals:       Technical indicators.
        price_data:       Price-related data.
        liquidity_data:   Liquidity-related data.
    """

    symbol: str
    exchange: str = "NSE"
    data: dict[str, Any] = field(default_factory=dict)
    fundamentals: dict[str, Any] = field(default_factory=dict)
    technicals: dict[str, Any] = field(default_factory=dict)
    price_data: dict[str, Any] = field(default_factory=dict)
    liquidity_data: dict[str, Any] = field(default_factory=dict)


@dataclass(frozen=True)
class FilterStatistics:
    """Statistics for a single filter.

    Attributes:
        filter_name:  Filter name.
        passed_count: Number of symbols that passed.
        failed_count: Number of symbols that failed.
    """

    filter_name: str
    passed_count: int = 0
    failed_count: int = 0


@dataclass(frozen=True)
class ScreenResult:
    """Result of evaluating a screen against symbols.

    Attributes:
        screen_name:       Screen name that was evaluated.
        passed:            Symbols that passed all filters.
        failed:            Symbols that failed at least one filter.
        elapsed_seconds:   Total evaluation time in seconds.
        filter_stats:      Per-filter statistics.
        evaluated_at:      When the evaluation was performed.
        total_evaluated:   Total number of symbols evaluated.
    """

    screen_name: str
    passed: tuple[str, ...] = field(default_factory=tuple)
    failed: tuple[str, ...] = field(default_factory=tuple)
    elapsed_seconds: float = 0.0
    filter_stats: tuple[FilterStatistics, ...] = field(default_factory=tuple)
    evaluated_at: datetime = field(default_factory=lambda: datetime.now().astimezone())
    total_evaluated: int = 0
