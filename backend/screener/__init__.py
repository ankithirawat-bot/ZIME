"""
Universal Screening Engine.

Production-ready screening engine for building reusable investment screens
using composable filters and logical operators.
"""

from backend.screener.engine import ScreenerEngine
from backend.screener.exceptions import (
    EvaluationError,
    FilterNotFoundError,
    InvalidFilterError,
    InvalidOperatorError,
    InvalidScreenDefinitionError,
    OperatorNotFoundError,
    ParserError,
    ScreenerError,
)
from backend.screener.factory import ScreenerFactory
from backend.screener.models import (
    ComparisonOperator,
    EvaluationContext,
    FilterCategory,
    FilterCondition,
    FilterGroup,
    FilterStatistics,
    LogicalOperator,
    ScreenDefinition,
    ScreenMetadata,
    ScreenResult,
)
from backend.screener.operators import OperatorRegistry, evaluate_comparison, evaluate_logical
from backend.screener.parser import (
    parse_condition,
    parse_group,
    parse_screen,
    parse_screen_from_list,
)
from backend.screener.registry import FilterRegistry, build_default_filter_registry

__all__ = [
    "ComparisonOperator",
    "EvaluationContext",
    "EvaluationError",
    "FilterCategory",
    "FilterCondition",
    "FilterGroup",
    "FilterNotFoundError",
    "FilterRegistry",
    "FilterStatistics",
    "InvalidFilterError",
    "InvalidOperatorError",
    "InvalidScreenDefinitionError",
    "LogicalOperator",
    "OperatorNotFoundError",
    "OperatorRegistry",
    "ParserError",
    "ScreenDefinition",
    "ScreenMetadata",
    "ScreenResult",
    "ScreenerEngine",
    "ScreenerError",
    "ScreenerFactory",
    "build_default_filter_registry",
    "evaluate_comparison",
    "evaluate_logical",
    "parse_condition",
    "parse_group",
    "parse_screen",
    "parse_screen_from_list",
]
