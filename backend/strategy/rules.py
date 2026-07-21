"""Strategy rules.

Built-in rules for common investment strategies.
"""

from __future__ import annotations

from collections.abc import Callable
from typing import Any

from backend.strategy.conditions import evaluate_group, format_group
from backend.strategy.models import (
    ComparisonOperator,
    Condition,
    ConditionGroup,
    LogicalOperator,
    MatchedRule,
    RuleCategory,
    StrategyRule,
)
from backend.strategy.signals import SignalType

RuleFunc = Callable[[dict[str, Any]], bool]


def create_rule(
    name: str,
    conditions: ConditionGroup,
    signal: SignalType = SignalType.HOLD,
    weight: float = 1.0,
    category: RuleCategory = RuleCategory.CUSTOM,
    description: str = "",
) -> StrategyRule:
    """Create a strategy rule.

    Args:
        name:        Rule name.
        conditions:  Condition group.
        signal:      Signal to emit.
        weight:      Rule weight.
        category:    Rule category.
        description: Rule description.

    Returns:
        A StrategyRule instance.
    """
    return StrategyRule(
        name=name,
        description=description or format_group(conditions),
        conditions=conditions,
        signal=signal,
        weight=weight,
        category=category,
    )


def evaluate_rule(rule: StrategyRule, data: dict[str, Any]) -> MatchedRule:
    """Evaluate a single rule.

    Args:
        rule: Rule to evaluate.
        data: Data dictionary.

    Returns:
        MatchedRule with evaluation result.
    """
    matched = evaluate_group(rule.conditions, data)
    return MatchedRule(
        rule_name=rule.name,
        matched=matched,
        signal=rule.signal,
        description=rule.description,
    )


def create_buy_rule(
    name: str,
    field: str,
    operator: ComparisonOperator,
    value: Any,
    weight: float = 1.0,
) -> StrategyRule:
    """Create a simple BUY rule.

    Args:
        name:     Rule name.
        field:    Data field path.
        operator: Comparison operator.
        value:    Comparison value.
        weight:   Rule weight.

    Returns:
        A StrategyRule for BUY signal.
    """
    return create_rule(
        name=name,
        conditions=ConditionGroup(
            operator=LogicalOperator.AND,
            conditions=(Condition(field=field, operator=operator, value=value),),
        ),
        signal=SignalType.BUY,
        weight=weight,
        category=RuleCategory.FUNDAMENTAL,
    )


def create_sell_rule(
    name: str,
    field: str,
    operator: ComparisonOperator,
    value: Any,
    weight: float = 1.0,
) -> StrategyRule:
    """Create a simple SELL rule.

    Args:
        name:     Rule name.
        field:    Data field path.
        operator: Comparison operator.
        value:    Comparison value.
        weight:   Rule weight.

    Returns:
        A StrategyRule for SELL signal.
    """
    return create_rule(
        name=name,
        conditions=ConditionGroup(
            operator=LogicalOperator.AND,
            conditions=(Condition(field=field, operator=operator, value=value),),
        ),
        signal=SignalType.SELL,
        weight=weight,
        category=RuleCategory.FUNDAMENTAL,
    )


def create_trend_rule(
    trend_value: str,
    signal: SignalType = SignalType.BUY,
    weight: float = 1.0,
) -> StrategyRule:
    """Create a trend-based rule.

    Args:
        trend_value: Expected trend state.
        signal:      Signal to emit.
        weight:      Rule weight.

    Returns:
        A StrategyRule for trend.
    """
    return create_rule(
        name=f"Trend = {trend_value}",
        conditions=ConditionGroup(
            operator=LogicalOperator.AND,
            conditions=(
                Condition(
                    field="technicals.trend_state",
                    operator=ComparisonOperator.EQ,
                    value=trend_value,
                ),
            ),
        ),
        signal=signal,
        weight=weight,
        category=RuleCategory.TECHNICAL,
    )


def create_momentum_rule(
    momentum_value: str,
    signal: SignalType = SignalType.BUY,
    weight: float = 1.0,
) -> StrategyRule:
    """Create a momentum-based rule.

    Args:
        momentum_value: Expected momentum state.
        signal:         Signal to emit.
        weight:         Rule weight.

    Returns:
        A StrategyRule for momentum.
    """
    return create_rule(
        name=f"Momentum = {momentum_value}",
        conditions=ConditionGroup(
            operator=LogicalOperator.AND,
            conditions=(
                Condition(
                    field="technicals.momentum_state",
                    operator=ComparisonOperator.EQ,
                    value=momentum_value,
                ),
            ),
        ),
        signal=signal,
        weight=weight,
        category=RuleCategory.TECHNICAL,
    )


def create_screen_rule(
    screen_passed: bool,
    signal: SignalType = SignalType.BUY,
    weight: float = 1.0,
) -> StrategyRule:
    """Create a screen result rule.

    Args:
        screen_passed: Whether the screen passed.
        signal:        Signal to emit.
        weight:        Rule weight.

    Returns:
        A StrategyRule for screen result.
    """
    return create_rule(
        name=f"Screen {'Passed' if screen_passed else 'Failed'}",
        conditions=ConditionGroup(
            operator=LogicalOperator.AND,
            conditions=(
                Condition(
                    field="screen.passed",
                    operator=ComparisonOperator.EQ,
                    value=screen_passed,
                ),
            ),
        ),
        signal=signal,
        weight=weight,
        category=RuleCategory.SCREEN,
    )


def create_ranking_rule(
    operator: ComparisonOperator,
    value: Any,
    signal: SignalType = SignalType.BUY,
    weight: float = 1.0,
) -> StrategyRule:
    """Create a ranking-based rule.

    Args:
        operator: Comparison operator.
        value:    Comparison value.
        signal:   Signal to emit.
        weight:   Rule weight.

    Returns:
        A StrategyRule for ranking.
    """
    return create_rule(
        name=f"Ranking {operator.value} {value}",
        conditions=ConditionGroup(
            operator=LogicalOperator.AND,
            conditions=(
                Condition(
                    field="ranking.total_score",
                    operator=operator,
                    value=value,
                ),
            ),
        ),
        signal=signal,
        weight=weight,
        category=RuleCategory.RANKING,
    )
