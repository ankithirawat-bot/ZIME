"""
Universal Strategy Engine.

Production-grade strategy engine combining screening, ranking, analytics,
and portfolio constraints to generate actionable investment decisions.
"""

from backend.strategy.conditions import (
    evaluate_condition,
    evaluate_group,
    format_condition,
    format_group,
    get_nested_value,
)
from backend.strategy.engine import StrategyEngine
from backend.strategy.exceptions import (
    ConfigurationError,
    EmptyUniverseError,
    EvaluationError,
    InvalidConditionError,
    InvalidRuleError,
    InvalidStrategyError,
    RuleNotFoundError,
    StrategyError,
)
from backend.strategy.factory import StrategyFactory
from backend.strategy.models import (
    ComparisonOperator,
    Condition,
    ConditionGroup,
    LogicalOperator,
    MatchedRule,
    RuleCategory,
    StrategyDefinition,
    StrategyMetadata,
    StrategyResult,
    StrategyRule,
    StrategySignal,
    StrategyStatistics,
)
from backend.strategy.registry import RuleRegistry, build_default_rule_registry
from backend.strategy.rules import (
    create_buy_rule,
    create_momentum_rule,
    create_ranking_rule,
    create_rule,
    create_screen_rule,
    create_sell_rule,
    create_trend_rule,
    evaluate_rule,
)
from backend.strategy.signals import (
    SIGNAL_SCORES,
    SignalType,
    signal_confidence,
    signal_from_score,
)

__all__ = [
    "ComparisonOperator",
    "Condition",
    "ConditionGroup",
    "ConfigurationError",
    "EmptyUniverseError",
    "EvaluationError",
    "InvalidConditionError",
    "InvalidRuleError",
    "InvalidStrategyError",
    "LogicalOperator",
    "MatchedRule",
    "RuleCategory",
    "RuleNotFoundError",
    "RuleRegistry",
    "SIGNAL_SCORES",
    "SignalType",
    "StrategyDefinition",
    "StrategyEngine",
    "StrategyError",
    "StrategyFactory",
    "StrategyMetadata",
    "StrategyResult",
    "StrategyRule",
    "StrategySignal",
    "StrategyStatistics",
    "build_default_rule_registry",
    "create_buy_rule",
    "create_momentum_rule",
    "create_ranking_rule",
    "create_rule",
    "create_screen_rule",
    "create_sell_rule",
    "create_trend_rule",
    "evaluate_condition",
    "evaluate_group",
    "evaluate_rule",
    "format_condition",
    "format_group",
    "get_nested_value",
    "signal_confidence",
    "signal_from_score",
]
