"""Strategy models.

Frozen dataclasses for strategy definitions, rules, signals, and results.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from datetime import datetime
from enum import StrEnum
from typing import Any

from backend.strategy.signals import SignalType


class RuleCategory(StrEnum):
    """Categories of strategy rules."""

    SCREEN = "screen"
    RANKING = "ranking"
    TECHNICAL = "technical"
    FUNDAMENTAL = "fundamental"
    PORTFOLIO = "portfolio"
    RISK = "risk"
    CUSTOM = "custom"


class LogicalOperator(StrEnum):
    """Logical operators for combining conditions."""

    AND = "AND"
    OR = "OR"
    NOT = "NOT"


class ComparisonOperator(StrEnum):
    """Comparison operators for conditions."""

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
class StrategyMetadata:
    """Metadata for a strategy definition.

    Attributes:
        name:        Strategy name.
        description: Strategy description.
        version:     Schema version.
        author:      Strategy author.
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
class Condition:
    """A single comparison condition.

    Attributes:
        field:    Data field path (e.g. "fundamentals.roe").
        operator: Comparison operator.
        value:    Comparison value(s).
    """

    field: str
    operator: ComparisonOperator
    value: Any


@dataclass(frozen=True)
class ConditionGroup:
    """A group of conditions combined with logical operators.

    Attributes:
        operator:   Logical operator.
        conditions: Individual conditions.
        groups:     Nested condition groups.
        negate:     Whether to negate the group result.
    """

    operator: LogicalOperator = LogicalOperator.AND
    conditions: tuple[Condition, ...] = field(default_factory=tuple)
    groups: tuple[ConditionGroup, ...] = field(default_factory=tuple)
    negate: bool = False


@dataclass(frozen=True)
class StrategyRule:
    """A strategy rule with conditions and signal.

    Attributes:
        name:        Rule name.
        description: Rule description.
        conditions:  Condition group to evaluate.
        signal:      Signal to emit if conditions match.
        weight:      Rule weight (0.0 to 1.0).
        category:    Rule category.
    """

    name: str
    description: str = ""
    conditions: ConditionGroup = field(default_factory=ConditionGroup)
    signal: SignalType = SignalType.HOLD
    weight: float = 1.0
    category: RuleCategory = RuleCategory.CUSTOM


@dataclass(frozen=True)
class MatchedRule:
    """A rule that was evaluated.

    Attributes:
        rule_name:  Rule name.
        matched:    Whether the rule matched.
        signal:     Signal from the rule.
        description: Rule description.
    """

    rule_name: str
    matched: bool
    signal: SignalType
    description: str = ""


@dataclass(frozen=True)
class StrategySignal:
    """Signal generated for a symbol.

    Attributes:
        symbol:       Ticker symbol.
        signal:       Signal type.
        confidence:   Confidence score (0-100).
        matched_rules: Rules that matched.
        failed_rules:  Rules that failed.
        total_rules:   Total rules evaluated.
    """

    symbol: str
    signal: SignalType
    confidence: float = 0.0
    matched_rules: tuple[MatchedRule, ...] = field(default_factory=tuple)
    failed_rules: tuple[MatchedRule, ...] = field(default_factory=tuple)
    total_rules: int = 0


@dataclass(frozen=True)
class StrategyStatistics:
    """Statistics for a strategy evaluation run.

    Attributes:
        total_symbols:    Total symbols evaluated.
        total_rules:      Total rules evaluated.
        elapsed_seconds:  Evaluation time.
        signals_by_type:  Count of each signal type.
        mean_confidence:  Mean confidence score.
    """

    total_symbols: int = 0
    total_rules: int = 0
    elapsed_seconds: float = 0.0
    signals_by_type: dict[str, int] = field(default_factory=dict)
    mean_confidence: float = 0.0


@dataclass(frozen=True)
class StrategyDefinition:
    """Complete strategy definition.

    Attributes:
        metadata: Strategy metadata.
        rules:    Strategy rules.
    """

    metadata: StrategyMetadata
    rules: tuple[StrategyRule, ...] = field(default_factory=tuple)


@dataclass(frozen=True)
class StrategyResult:
    """Result of a strategy evaluation.

    Attributes:
        strategy_name: Name of the strategy used.
        signals:       Signals for each symbol.
        statistics:    Evaluation statistics.
        evaluated_at:  When the evaluation was performed.
    """

    strategy_name: str
    signals: tuple[StrategySignal, ...] = field(default_factory=tuple)
    statistics: StrategyStatistics = field(default_factory=StrategyStatistics)
    evaluated_at: datetime = field(default_factory=lambda: datetime.now().astimezone())
