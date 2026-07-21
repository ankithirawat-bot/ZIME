"""
Screener tests.

Covers all operators, combined AND/OR expressions, empty universe,
invalid filters, invalid operators, parser, registry, execution
statistics, and multiple symbols.
"""

from __future__ import annotations

import pytest

from backend.screener.exceptions import (
    EvaluationError,
    FilterNotFoundError,
    InvalidScreenDefinitionError,
    OperatorNotFoundError,
    ParserError,
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

# ---------------------------------------------------------------------------
# Fixtures & Helpers
# ---------------------------------------------------------------------------


def _context(
    symbol: str = "RELIANCE",
    market_cap: float = 100000,
    roe: float = 20,
    close: float = 2500,
    trend: str = "Strong Bullish",
    avg_volume: float = 1000000,
) -> EvaluationContext:
    """Create an EvaluationContext for testing."""
    return EvaluationContext(
        symbol=symbol,
        exchange="NSE",
        fundamentals={"market_cap": market_cap, "roe": roe},
        technicals={"trend_state": trend},
        price_data={"close": close},
        liquidity_data={"avg_volume": avg_volume},
    )


def _simple_screen(
    name: str = "Test Screen",
    operator: str = "AND",
    conditions: list[dict] | None = None,
) -> ScreenDefinition:
    """Create a simple ScreenDefinition for testing."""
    if conditions is None:
        conditions = [
            {"name": "market_cap", "operator": ">", "value": 50000},
            {"name": "roe", "operator": ">", "value": 15},
        ]
    return ScreenDefinition(
        metadata=ScreenMetadata(name=name),
        filters=FilterGroup(
            operator=LogicalOperator(operator),
            conditions=tuple(
                FilterCondition(
                    name=c["name"],
                    operator=ComparisonOperator(c["operator"]),
                    value=c["value"],
                )
                for c in conditions
            ),
        ),
    )


# ---------------------------------------------------------------------------
# Comparison Operators tests
# ---------------------------------------------------------------------------


class TestComparisonOperators:
    def test_eq(self):
        assert evaluate_comparison(10, ComparisonOperator.EQ, 10) is True
        assert evaluate_comparison(10, ComparisonOperator.EQ, 20) is False

    def test_neq(self):
        assert evaluate_comparison(10, ComparisonOperator.NEQ, 20) is True
        assert evaluate_comparison(10, ComparisonOperator.NEQ, 10) is False

    def test_gt(self):
        assert evaluate_comparison(10, ComparisonOperator.GT, 5) is True
        assert evaluate_comparison(10, ComparisonOperator.GT, 10) is False
        assert evaluate_comparison(10, ComparisonOperator.GT, 15) is False

    def test_gte(self):
        assert evaluate_comparison(10, ComparisonOperator.GTE, 10) is True
        assert evaluate_comparison(10, ComparisonOperator.GTE, 5) is True
        assert evaluate_comparison(10, ComparisonOperator.GTE, 15) is False

    def test_lt(self):
        assert evaluate_comparison(10, ComparisonOperator.LT, 15) is True
        assert evaluate_comparison(10, ComparisonOperator.LT, 10) is False
        assert evaluate_comparison(10, ComparisonOperator.LT, 5) is False

    def test_lte(self):
        assert evaluate_comparison(10, ComparisonOperator.LTE, 10) is True
        assert evaluate_comparison(10, ComparisonOperator.LTE, 15) is True
        assert evaluate_comparison(10, ComparisonOperator.LTE, 5) is False

    def test_in(self):
        assert evaluate_comparison(10, ComparisonOperator.IN, [5, 10, 15]) is True
        assert evaluate_comparison(10, ComparisonOperator.IN, [5, 15]) is False

    def test_not_in(self):
        assert evaluate_comparison(10, ComparisonOperator.NOT_IN, [5, 15]) is True
        assert evaluate_comparison(10, ComparisonOperator.NOT_IN, [5, 10]) is False

    def test_between(self):
        assert evaluate_comparison(10, ComparisonOperator.BETWEEN, [5, 15]) is True
        assert evaluate_comparison(10, ComparisonOperator.BETWEEN, [10, 15]) is True
        assert evaluate_comparison(10, ComparisonOperator.BETWEEN, [15, 20]) is False

    def test_string_comparison(self):
        assert evaluate_comparison("A", ComparisonOperator.EQ, "A") is True
        assert evaluate_comparison("A", ComparisonOperator.NEQ, "B") is True
        assert evaluate_comparison("A", ComparisonOperator.IN, ["A", "B"]) is True


# ---------------------------------------------------------------------------
# Logical Operators tests
# ---------------------------------------------------------------------------


class TestLogicalOperators:
    def test_and_true(self):
        assert evaluate_logical((True, True, True), LogicalOperator.AND) is True

    def test_and_false(self):
        assert evaluate_logical((True, False, True), LogicalOperator.AND) is False

    def test_or_true(self):
        assert evaluate_logical((False, True, False), LogicalOperator.OR) is True

    def test_or_false(self):
        assert evaluate_logical((False, False, False), LogicalOperator.OR) is False

    def test_not(self):
        assert evaluate_logical((True,), LogicalOperator.NOT) is False
        assert evaluate_logical((False,), LogicalOperator.NOT) is True

    def test_empty_results(self):
        assert evaluate_logical((), LogicalOperator.AND) is True
        assert evaluate_logical((), LogicalOperator.OR) is True


# ---------------------------------------------------------------------------
# Operator Registry tests
# ---------------------------------------------------------------------------


class TestOperatorRegistry:
    def test_default_operators(self):
        registry = OperatorRegistry()
        assert registry.is_registered(ComparisonOperator.EQ)
        assert registry.is_registered(ComparisonOperator.GT)
        assert len(registry.registered_operators()) == 9

    def test_get_operator(self):
        registry = OperatorRegistry()
        func = registry.get(ComparisonOperator.EQ)
        assert func(10, 10) is True

    def test_get_unregistered_operator(self):
        registry = OperatorRegistry()
        # ComparisonOperator("INVALID") raises ValueError, so use a different approach
        # Test that the registry raises OperatorNotFoundError for missing keys
        # by temporarily removing an operator
        original_operators = registry._operators.copy()
        try:
            del registry._operators[ComparisonOperator.EQ]
            with pytest.raises(OperatorNotFoundError):
                registry.get(ComparisonOperator.EQ)
        finally:
            registry._operators.update(original_operators)


# ---------------------------------------------------------------------------
# Filter Registry tests
# ---------------------------------------------------------------------------


class TestFilterRegistry:
    def test_default_filters(self):
        registry = build_default_filter_registry()
        assert registry.is_registered("market_cap")
        assert registry.is_registered("roe")
        assert registry.is_registered("trend_state")
        assert registry.is_registered("close")
        assert registry.is_registered("avg_volume")

    def test_filter_by_category(self):
        registry = build_default_filter_registry()
        fundamental = registry.filters_by_category(FilterCategory.FUNDAMENTAL)
        assert "market_cap" in fundamental
        assert "roe" in fundamental

    def test_custom_filter(self):
        registry = FilterRegistry(load_defaults=False)
        assert not registry.is_registered("custom_filter")

        def custom_func(ctx: EvaluationContext) -> float:
            return 42.0

        registry.register("custom_filter", custom_func, FilterCategory.CUSTOM)
        assert registry.is_registered("custom_filter")
        assert registry.get("custom_filter")(_context()) == 42.0

    def test_get_unregistered_filter(self):
        registry = FilterRegistry(load_defaults=False)
        with pytest.raises(FilterNotFoundError):
            registry.get("nonexistent")


# ---------------------------------------------------------------------------
# Filter Functions tests
# ---------------------------------------------------------------------------


class TestFilterFunctions:
    def test_market_cap(self):
        from backend.screener.filters import filter_market_cap

        ctx = _context(market_cap=50000)
        assert filter_market_cap(ctx) == 50000

    def test_roe(self):
        from backend.screener.filters import filter_roe

        ctx = _context(roe=25)
        assert filter_roe(ctx) == 25

    def test_trend_state(self):
        from backend.screener.filters import filter_trend_state

        ctx = _context(trend="Bullish")
        assert filter_trend_state(ctx) == "Bullish"

    def test_close(self):
        from backend.screener.filters import filter_close

        ctx = _context(close=1500)
        assert filter_close(ctx) == 1500

    def test_average_volume(self):
        from backend.screener.filters import filter_average_volume

        ctx = _context(avg_volume=500000)
        assert filter_average_volume(ctx) == 500000


# ---------------------------------------------------------------------------
# Parser tests
# ---------------------------------------------------------------------------


class TestParser:
    def test_parse_condition(self):
        data = {"name": "market_cap", "operator": ">", "value": 10000}
        condition = parse_condition(data)
        assert condition.name == "market_cap"
        assert condition.operator == ComparisonOperator.GT
        assert condition.value == 10000

    def test_parse_condition_with_category(self):
        data = {
            "name": "roe",
            "operator": ">",
            "value": 15,
            "category": "fundamental",
        }
        condition = parse_condition(data)
        assert condition.category == FilterCategory.FUNDAMENTAL

    def test_parse_condition_negate(self):
        data = {"name": "roe", "operator": ">", "value": 15, "negate": True}
        condition = parse_condition(data)
        assert condition.negate is True

    def test_parse_condition_missing_name(self):
        data = {"operator": ">", "value": 10000}
        with pytest.raises(ParserError, match="missing 'name'"):
            parse_condition(data)

    def test_parse_condition_missing_operator(self):
        data = {"name": "market_cap", "value": 10000}
        with pytest.raises(ParserError, match="missing 'operator'"):
            parse_condition(data)

    def test_parse_condition_missing_value(self):
        data = {"name": "market_cap", "operator": ">"}
        with pytest.raises(ParserError, match="missing 'value'"):
            parse_condition(data)

    def test_parse_condition_invalid_operator(self):
        data = {"name": "market_cap", "operator": "INVALID", "value": 10000}
        with pytest.raises(ParserError, match="Invalid comparison operator"):
            parse_condition(data)

    def test_parse_group(self):
        data = {
            "operator": "AND",
            "conditions": [
                {"name": "market_cap", "operator": ">", "value": 10000},
                {"name": "roe", "operator": ">", "value": 15},
            ],
        }
        group = parse_group(data)
        assert group.operator == LogicalOperator.AND
        assert len(group.conditions) == 2

    def test_parse_group_nested(self):
        data = {
            "operator": "OR",
            "conditions": [
                {"name": "market_cap", "operator": ">", "value": 10000},
            ],
            "groups": [
                {
                    "operator": "AND",
                    "conditions": [
                        {"name": "roe", "operator": ">", "value": 15},
                        {"name": "close", "operator": ">", "value": 100},
                    ],
                }
            ],
        }
        group = parse_group(data)
        assert group.operator == LogicalOperator.OR
        assert len(group.conditions) == 1
        assert len(group.groups) == 1

    def test_parse_screen(self):
        data = {
            "metadata": {"name": "My Screen", "author": "Test"},
            "filters": {
                "operator": "AND",
                "conditions": [
                    {"name": "market_cap", "operator": ">", "value": 10000},
                ],
            },
        }
        screen = parse_screen(data)
        assert screen.metadata.name == "My Screen"
        assert screen.metadata.author == "Test"
        assert len(screen.filters.conditions) == 1

    def test_parse_screen_missing_filters(self):
        data = {"metadata": {"name": "My Screen"}}
        with pytest.raises(InvalidScreenDefinitionError, match="Missing 'filters'"):
            parse_screen(data)

    def test_parse_screen_from_list(self):
        conditions = [
            {"name": "market_cap", "operator": ">", "value": 10000},
            {"name": "roe", "operator": ">", "value": 15},
        ]
        screen = parse_screen_from_list(conditions)
        assert screen.metadata.name == "Simple Screen"
        assert len(screen.filters.conditions) == 2
        assert screen.filters.operator == LogicalOperator.AND


# ---------------------------------------------------------------------------
# Engine tests
# ---------------------------------------------------------------------------


class TestScreenerEngine:
    def test_evaluate_pass(self):
        engine = ScreenerFactory.create()
        screen = _simple_screen()
        ctx = _context(market_cap=100000, roe=20)

        assert engine.evaluate(screen, ctx) is True

    def test_evaluate_fail(self):
        engine = ScreenerFactory.create()
        screen = _simple_screen()
        ctx = _context(market_cap=10000, roe=20)

        assert engine.evaluate(screen, ctx) is False

    def test_evaluate_or_logic(self):
        engine = ScreenerFactory.create()
        screen = _simple_screen(operator="OR")
        ctx = _context(market_cap=10000, roe=20)

        assert engine.evaluate(screen, ctx) is True

    def test_evaluate_many(self):
        engine = ScreenerFactory.create()
        screen = _simple_screen()
        contexts = [
            _context("RELIANCE", market_cap=100000, roe=20),   # both pass
            _context("TCS", market_cap=5000, roe=25),          # market_cap fails
            _context("INFY", market_cap=200000, roe=10),       # roe fails
        ]

        result = engine.evaluate_many(screen, contexts)
        assert result.screen_name == "Test Screen"
        assert "RELIANCE" in result.passed
        assert "TCS" in result.failed
        assert "INFY" in result.failed
        assert result.total_evaluated == 3

    def test_evaluate_empty_universe(self):
        engine = ScreenerFactory.create()
        screen = _simple_screen()

        result = engine.evaluate_many(screen, [])
        assert result.passed == ()
        assert result.failed == ()
        assert result.total_evaluated == 0

    def test_evaluate_universe(self):
        engine = ScreenerFactory.create()
        screen = _simple_screen()

        def provider():
            return [
                _context("RELIANCE", market_cap=100000, roe=20),
                _context("TCS", market_cap=5000, roe=25),
            ]

        result = engine.evaluate_universe(screen, provider)
        assert result.total_evaluated == 2

    def test_filter_statistics(self):
        engine = ScreenerFactory.create()
        screen = _simple_screen()
        contexts = [
            _context("RELIANCE", market_cap=100000, roe=20),
            _context("TCS", market_cap=5000, roe=25),
        ]

        result = engine.evaluate_many(screen, contexts)
        assert len(result.filter_stats) == 2

        mc_stats = next(s for s in result.filter_stats if s.filter_name == "market_cap")
        assert mc_stats.passed_count == 1
        assert mc_stats.failed_count == 1

    def test_negate_condition(self):
        engine = ScreenerFactory.create()
        screen = ScreenDefinition(
            metadata=ScreenMetadata(name="Negate Test"),
            filters=FilterGroup(
                operator=LogicalOperator.AND,
                conditions=(
                    FilterCondition(
                        name="market_cap",
                        operator=ComparisonOperator.GT,
                        value=50000,
                        negate=True,
                    ),
                ),
            ),
        )
        ctx = _context(market_cap=100000)

        assert engine.evaluate(screen, ctx) is False

    def test_in_operator(self):
        engine = ScreenerFactory.create()
        screen = ScreenDefinition(
            metadata=ScreenMetadata(name="IN Test"),
            filters=FilterGroup(
                operator=LogicalOperator.AND,
                conditions=(
                    FilterCondition(
                        name="trend_state",
                        operator=ComparisonOperator.IN,
                        value=["Strong Bullish", "Bullish"],
                    ),
                ),
            ),
        )
        ctx = _context(trend="Bullish")
        assert engine.evaluate(screen, ctx) is True

        ctx_fail = _context(trend="Bearish")
        assert engine.evaluate(screen, ctx_fail) is False

    def test_between_operator(self):
        engine = ScreenerFactory.create()
        screen = ScreenDefinition(
            metadata=ScreenMetadata(name="BETWEEN Test"),
            filters=FilterGroup(
                operator=LogicalOperator.AND,
                conditions=(
                    FilterCondition(
                        name="close",
                        operator=ComparisonOperator.BETWEEN,
                        value=[2000, 3000],
                    ),
                ),
            ),
        )
        ctx = _context(close=2500)
        assert engine.evaluate(screen, ctx) is True

        ctx_fail = _context(close=3500)
        assert engine.evaluate(screen, ctx_fail) is False


# ---------------------------------------------------------------------------
# Factory tests
# ---------------------------------------------------------------------------


class TestScreenerFactory:
    def test_create_default(self):
        engine = ScreenerFactory.create()
        assert engine is not None
        assert engine.filter_registry.is_registered("market_cap")

    def test_create_custom_filters_only(self):
        engine = ScreenerFactory.create_with_custom_filters()
        assert not engine.filter_registry.is_registered("market_cap")

    def test_create_from_registries(self):
        filter_reg = FilterRegistry(load_defaults=False)
        operator_reg = OperatorRegistry()
        engine = ScreenerFactory.create_from_registries(filter_reg, operator_reg)
        assert not engine.filter_registry.is_registered("market_cap")


# ---------------------------------------------------------------------------
# Exception tests
# ---------------------------------------------------------------------------


class TestExceptions:
    def test_screener_error(self):
        from backend.screener.exceptions import ScreenerError

        with pytest.raises(ScreenerError):
            raise ScreenerError("test")

    def test_filter_not_found(self):
        with pytest.raises(FilterNotFoundError) as excinfo:
            raise FilterNotFoundError("my_filter")
        assert excinfo.value.name == "my_filter"
        assert "my_filter" in str(excinfo.value)

    def test_operator_not_found(self):
        with pytest.raises(OperatorNotFoundError) as excinfo:
            raise OperatorNotFoundError("my_op")
        assert excinfo.value.name == "my_op"

    def test_parser_error(self):
        with pytest.raises(ParserError, match="syntax"):
            raise ParserError("syntax error")

    def test_evaluation_error(self):
        with pytest.raises(EvaluationError) as excinfo:
            raise EvaluationError("RELIANCE", "missing data")
        assert excinfo.value.symbol == "RELIANCE"
        assert "RELIANCE" in str(excinfo.value)

    def test_invalid_screen_definition(self):
        with pytest.raises(InvalidScreenDefinitionError):
            raise InvalidScreenDefinitionError("bad def")


# ---------------------------------------------------------------------------
# Model tests
# ---------------------------------------------------------------------------


class TestModels:
    def test_screen_metadata(self):
        meta = ScreenMetadata(name="Test", author="Author", tags=("a", "b"))
        assert meta.name == "Test"
        assert meta.tags == ("a", "b")

    def test_filter_condition(self):
        cond = FilterCondition(
            name="close",
            operator=ComparisonOperator.GT,
            value=100,
        )
        assert cond.name == "close"
        assert cond.operator == ComparisonOperator.GT

    def test_screen_result(self):
        result = ScreenResult(
            screen_name="Test",
            passed=("A", "B"),
            failed=("C",),
            total_evaluated=3,
        )
        assert result.passed == ("A", "B")
        assert result.total_evaluated == 3

    def test_filter_statistics(self):
        stats = FilterStatistics(
            filter_name="market_cap",
            passed_count=10,
            failed_count=5,
        )
        assert stats.passed_count == 10

    def test_evaluation_context(self):
        ctx = EvaluationContext(
            symbol="RELIANCE",
            fundamentals={"market_cap": 100000},
        )
        assert ctx.symbol == "RELIANCE"
        assert ctx.fundamentals["market_cap"] == 100000


# ---------------------------------------------------------------------------
# Integration tests
# ---------------------------------------------------------------------------


class TestIntegration:
    def test_complex_screen(self):
        """Test a complex screen with nested AND/OR logic."""
        screen = ScreenDefinition(
            metadata=ScreenMetadata(name="Complex Screen"),
            filters=FilterGroup(
                operator=LogicalOperator.AND,
                conditions=(
                    FilterCondition(
                        name="market_cap",
                        operator=ComparisonOperator.GT,
                        value=50000,
                    ),
                ),
                groups=(
                    FilterGroup(
                        operator=LogicalOperator.OR,
                        conditions=(
                            FilterCondition(
                                name="roe",
                                operator=ComparisonOperator.GT,
                                value=15,
                            ),
                            FilterCondition(
                                name="trend_state",
                                operator=ComparisonOperator.IN,
                                value=["Strong Bullish", "Bullish"],
                            ),
                        ),
                    ),
                ),
            ),
        )

        engine = ScreenerFactory.create()

        # Passes: market_cap > 50000 AND (roe > 15 OR trend in [Strong Bullish, Bullish])
        ctx_pass = _context("RELIANCE", market_cap=100000, roe=20, trend="Neutral")
        assert engine.evaluate(screen, ctx_pass) is True

        # Passes: market_cap > 50000 AND trend is Bullish (second OR condition)
        ctx_pass2 = _context("TCS", market_cap=100000, roe=10, trend="Bullish")
        assert engine.evaluate(screen, ctx_pass2) is True

        # Fails: market_cap < 50000
        ctx_fail = _context("INFY", market_cap=10000, roe=20)
        assert engine.evaluate(screen, ctx_fail) is False

    def test_all_built_in_filters_registered(self):
        """Verify all built-in filters are registered."""
        registry = build_default_filter_registry()

        expected_filters = [
            "market_cap", "sales_growth", "profit_growth", "eps_growth",
            "roe", "roce", "debt_equity",
            "trend_state", "momentum_state", "rs_state", "volume_state",
            "volatility_state",
            "close", "ema20", "ema50", "ema200", "atr", "high_52w", "low_52w",
            "avg_volume", "delivery_pct", "traded_value",
        ]

        for name in expected_filters:
            assert registry.is_registered(name), f"Filter '{name}' not registered"

    def test_screen_result_statistics_accuracy(self):
        """Verify filter statistics are computed correctly."""
        engine = ScreenerFactory.create()
        screen = _simple_screen()
        contexts = [
            _context("A", market_cap=100000, roe=20),   # both pass
            _context("B", market_cap=100000, roe=10),   # mc pass, roe fail
            _context("C", market_cap=10000, roe=20),    # mc fail, roe pass
            _context("D", market_cap=10000, roe=10),    # both fail
        ]

        result = engine.evaluate_many(screen, contexts)

        mc_stats = next(s for s in result.filter_stats if s.filter_name == "market_cap")
        assert mc_stats.passed_count == 2
        assert mc_stats.failed_count == 2

        roe_stats = next(s for s in result.filter_stats if s.filter_name == "roe")
        assert roe_stats.passed_count == 2
        assert roe_stats.failed_count == 2
