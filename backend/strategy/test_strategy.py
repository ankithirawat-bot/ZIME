"""
Strategy engine tests.

Covers all signal types, nested rules, confidence scoring, rule failures,
multiple symbols, registry, statistics, and empty universe.
"""

from __future__ import annotations

import pytest

from backend.strategy.conditions import (
    evaluate_condition,
    evaluate_group,
    format_condition,
    format_group,
    get_nested_value,
)
from backend.strategy.exceptions import (
    EmptyUniverseError,
    InvalidConditionError,
    RuleNotFoundError,
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
from backend.strategy.signals import SIGNAL_SCORES, SignalType, signal_confidence, signal_from_score

# ---------------------------------------------------------------------------
# Fixtures & Helpers
# ---------------------------------------------------------------------------


def _data(
    roe: float = 20.0,
    roce: float = 25.0,
    trend: str = "Bullish",
    momentum: str = "Positive",
    screen_passed: bool = True,
    ranking_score: float = 85.0,
) -> dict:
    """Create test data dictionary."""
    return {
        "fundamentals": {"roe": roe, "roce": roce},
        "technicals": {"trend_state": trend, "momentum_state": momentum},
        "screen": {"passed": screen_passed},
        "ranking": {"total_score": ranking_score},
    }


def _simple_definition(
    name: str = "Test Strategy",
    rules: tuple[StrategyRule, ...] | None = None,
) -> StrategyDefinition:
    """Create a simple strategy definition for testing."""
    if rules is None:
        rules = (
            create_rule(
                name="ROCE > 20",
                conditions=ConditionGroup(
                    operator=LogicalOperator.AND,
                    conditions=(
                        Condition(field="fundamentals.roce", operator=ComparisonOperator.GT, value=20),
                    ),
                ),
                signal=SignalType.BUY,
                weight=0.5,
            ),
            create_rule(
                name="Trend = Bullish",
                conditions=ConditionGroup(
                    operator=LogicalOperator.AND,
                    conditions=(
                        Condition(field="technicals.trend_state", operator=ComparisonOperator.EQ, value="Bullish"),
                    ),
                ),
                signal=SignalType.BUY,
                weight=0.5,
            ),
        )
    return StrategyDefinition(
        metadata=StrategyMetadata(name=name),
        rules=rules,
    )


# ---------------------------------------------------------------------------
# Signal tests
# ---------------------------------------------------------------------------


class TestSignals:
    def test_signal_types(self):
        assert SignalType.STRONG_BUY == "STRONG_BUY"
        assert SignalType.BUY == "BUY"
        assert SignalType.HOLD == "HOLD"
        assert SignalType.REDUCE == "REDUCE"
        assert SignalType.SELL == "SELL"
        assert SignalType.STRONG_SELL == "STRONG_SELL"
        assert SignalType.WATCH == "WATCH"
        assert SignalType.IGNORE == "IGNORE"

    def test_signal_scores(self):
        assert SIGNAL_SCORES[SignalType.STRONG_BUY] == 1.0
        assert SIGNAL_SCORES[SignalType.BUY] == 0.75
        assert SIGNAL_SCORES[SignalType.HOLD] == 0.5
        assert SIGNAL_SCORES[SignalType.SELL] == 0.0

    def test_signal_from_score(self):
        assert signal_from_score(1.0) == SignalType.STRONG_BUY
        assert signal_from_score(0.8) == SignalType.BUY
        assert signal_from_score(0.5) == SignalType.HOLD
        assert signal_from_score(0.3) == SignalType.REDUCE
        assert signal_from_score(0.0) == SignalType.SELL
        assert signal_from_score(-0.2) == SignalType.STRONG_SELL

    def test_signal_confidence(self):
        assert signal_confidence(5, 5, SignalType.BUY) == 100.0
        assert signal_confidence(3, 5, SignalType.BUY) == 60.0
        assert signal_confidence(0, 5, SignalType.BUY) == 0.0

    def test_signal_confidence_watch(self):
        assert signal_confidence(5, 5, SignalType.WATCH) == 50.0

    def test_signal_confidence_empty(self):
        assert signal_confidence(0, 0, SignalType.BUY) == 0.0


# ---------------------------------------------------------------------------
# Condition tests
# ---------------------------------------------------------------------------


class TestConditions:
    def test_get_nested_value(self):
        data = {"a": {"b": {"c": 42}}}
        assert get_nested_value(data, "a.b.c") == 42

    def test_get_nested_value_missing(self):
        data = {"a": {"b": 1}}
        assert get_nested_value(data, "a.c") is None

    def test_evaluate_condition_eq(self):
        cond = Condition(field="x", operator=ComparisonOperator.EQ, value=10)
        assert evaluate_condition(cond, {"x": 10}) is True
        assert evaluate_condition(cond, {"x": 20}) is False

    def test_evaluate_condition_gt(self):
        cond = Condition(field="x", operator=ComparisonOperator.GT, value=10)
        assert evaluate_condition(cond, {"x": 15}) is True
        assert evaluate_condition(cond, {"x": 5}) is False

    def test_evaluate_condition_gte(self):
        cond = Condition(field="x", operator=ComparisonOperator.GTE, value=10)
        assert evaluate_condition(cond, {"x": 10}) is True
        assert evaluate_condition(cond, {"x": 9}) is False

    def test_evaluate_condition_lt(self):
        cond = Condition(field="x", operator=ComparisonOperator.LT, value=10)
        assert evaluate_condition(cond, {"x": 5}) is True
        assert evaluate_condition(cond, {"x": 15}) is False

    def test_evaluate_condition_lte(self):
        cond = Condition(field="x", operator=ComparisonOperator.LTE, value=10)
        assert evaluate_condition(cond, {"x": 10}) is True
        assert evaluate_condition(cond, {"x": 11}) is False

    def test_evaluate_condition_in(self):
        cond = Condition(field="x", operator=ComparisonOperator.IN, value=[1, 2, 3])
        assert evaluate_condition(cond, {"x": 2}) is True
        assert evaluate_condition(cond, {"x": 4}) is False

    def test_evaluate_condition_not_in(self):
        cond = Condition(field="x", operator=ComparisonOperator.NOT_IN, value=[1, 2, 3])
        assert evaluate_condition(cond, {"x": 4}) is True
        assert evaluate_condition(cond, {"x": 2}) is False

    def test_evaluate_condition_between(self):
        cond = Condition(field="x", operator=ComparisonOperator.BETWEEN, value=[10, 20])
        assert evaluate_condition(cond, {"x": 15}) is True
        assert evaluate_condition(cond, {"x": 5}) is False
        assert evaluate_condition(cond, {"x": 25}) is False

    def test_evaluate_condition_neq(self):
        cond = Condition(field="x", operator=ComparisonOperator.NEQ, value=10)
        assert evaluate_condition(cond, {"x": 20}) is True
        assert evaluate_condition(cond, {"x": 10}) is False

    def test_evaluate_condition_missing_field(self):
        cond = Condition(field="x", operator=ComparisonOperator.EQ, value=10)
        assert evaluate_condition(cond, {"y": 10}) is False

    def test_evaluate_group_and(self):
        group = ConditionGroup(
            operator=LogicalOperator.AND,
            conditions=(
                Condition(field="a", operator=ComparisonOperator.GT, value=5),
                Condition(field="b", operator=ComparisonOperator.LT, value=10),
            ),
        )
        assert evaluate_group(group, {"a": 7, "b": 8}) is True
        assert evaluate_group(group, {"a": 3, "b": 8}) is False

    def test_evaluate_group_or(self):
        group = ConditionGroup(
            operator=LogicalOperator.OR,
            conditions=(
                Condition(field="a", operator=ComparisonOperator.GT, value=5),
                Condition(field="b", operator=ComparisonOperator.LT, value=10),
            ),
        )
        assert evaluate_group(group, {"a": 3, "b": 8}) is True
        assert evaluate_group(group, {"a": 3, "b": 15}) is False

    def test_evaluate_group_not(self):
        group = ConditionGroup(
            operator=LogicalOperator.AND,
            conditions=(Condition(field="a", operator=ComparisonOperator.EQ, value=10),),
            negate=True,
        )
        assert evaluate_group(group, {"a": 10}) is False
        assert evaluate_group(group, {"a": 20}) is True

    def test_evaluate_group_nested(self):
        group = ConditionGroup(
            operator=LogicalOperator.AND,
            conditions=(Condition(field="a", operator=ComparisonOperator.GT, value=5),),
            groups=(
                ConditionGroup(
                    operator=LogicalOperator.OR,
                    conditions=(
                        Condition(field="b", operator=ComparisonOperator.EQ, value=10),
                        Condition(field="c", operator=ComparisonOperator.EQ, value=20),
                    ),
                ),
            ),
        )
        assert evaluate_group(group, {"a": 7, "b": 10}) is True
        assert evaluate_group(group, {"a": 7, "c": 20}) is True
        assert evaluate_group(group, {"a": 3, "b": 10}) is False

    def test_evaluate_group_empty(self):
        group = ConditionGroup()
        assert evaluate_group(group, {}) is True

    def test_format_condition(self):
        cond = Condition(field="a", operator=ComparisonOperator.GT, value=10)
        assert format_condition(cond) == "a > 10"

    def test_format_group(self):
        group = ConditionGroup(
            operator=LogicalOperator.AND,
            conditions=(
                Condition(field="a", operator=ComparisonOperator.GT, value=5),
                Condition(field="b", operator=ComparisonOperator.LT, value=10),
            ),
        )
        result = format_group(group)
        assert "a > 5" in result
        assert "b < 10" in result
        assert "AND" in result


# ---------------------------------------------------------------------------
# Rule tests
# ---------------------------------------------------------------------------


class TestRules:
    def test_create_rule(self):
        rule = create_rule(
            name="Test Rule",
            conditions=ConditionGroup(
                operator=LogicalOperator.AND,
                conditions=(Condition(field="a", operator=ComparisonOperator.GT, value=5),),
            ),
            signal=SignalType.BUY,
        )
        assert rule.name == "Test Rule"
        assert rule.signal == SignalType.BUY

    def test_evaluate_rule_match(self):
        rule = create_buy_rule("ROCE > 20", "fundamentals.roce", ComparisonOperator.GT, 20)
        data = _data(roce=25)
        result = evaluate_rule(rule, data)
        assert result.matched is True
        assert result.signal == SignalType.BUY

    def test_evaluate_rule_no_match(self):
        rule = create_buy_rule("ROCE > 30", "fundamentals.roce", ComparisonOperator.GT, 30)
        data = _data(roce=25)
        result = evaluate_rule(rule, data)
        assert result.matched is False

    def test_create_sell_rule(self):
        rule = create_sell_rule("ROE < 10", "fundamentals.roe", ComparisonOperator.LT, 10)
        assert rule.signal == SignalType.SELL

    def test_create_trend_rule(self):
        rule = create_trend_rule("Bullish")
        assert rule.signal == SignalType.BUY
        data = _data(trend="Bullish")
        result = evaluate_rule(rule, data)
        assert result.matched is True

    def test_create_momentum_rule(self):
        rule = create_momentum_rule("Positive")
        assert rule.signal == SignalType.BUY

    def test_create_screen_rule(self):
        rule = create_screen_rule(True)
        assert rule.signal == SignalType.BUY

    def test_create_ranking_rule(self):
        rule = create_ranking_rule(ComparisonOperator.GT, 80)
        assert rule.signal == SignalType.BUY


# ---------------------------------------------------------------------------
# Registry tests
# ---------------------------------------------------------------------------


class TestRegistry:
    def test_empty_registry(self):
        registry = build_default_rule_registry()
        assert registry.registered_names() == ()

    def test_register_rule(self):
        registry = RuleRegistry()
        rule = create_buy_rule("Test", "a", ComparisonOperator.GT, 5)
        registry.register(rule)
        assert registry.is_registered("Test")
        assert registry.get("Test") is rule

    def test_get_unregistered_rule(self):
        registry = RuleRegistry()
        with pytest.raises(RuleNotFoundError):
            registry.get("Nonexistent")

    def test_registered_names(self):
        registry = RuleRegistry()
        registry.register(create_buy_rule("A", "a", ComparisonOperator.GT, 5))
        registry.register(create_buy_rule("B", "b", ComparisonOperator.GT, 5))
        names = registry.registered_names()
        assert "A" in names
        assert "B" in names

    def test_rules_by_category(self):
        registry = RuleRegistry()
        rule = create_buy_rule("Fund Rule", "a", ComparisonOperator.GT, 5)
        registry.register(rule)
        fund_rules = registry.rules_by_category(RuleCategory.FUNDAMENTAL)
        assert len(fund_rules) == 1

    def test_clear(self):
        registry = RuleRegistry()
        registry.register(create_buy_rule("A", "a", ComparisonOperator.GT, 5))
        registry.clear()
        assert registry.registered_names() == ()


# ---------------------------------------------------------------------------
# Model tests
# ---------------------------------------------------------------------------


class TestModels:
    def test_strategy_metadata(self):
        meta = StrategyMetadata(name="Test", author="Author", tags=("a", "b"))
        assert meta.name == "Test"
        assert meta.tags == ("a", "b")

    def test_strategy_definition(self):
        defn = StrategyDefinition(
            metadata=StrategyMetadata(name="Test"),
            rules=(),
        )
        assert defn.metadata.name == "Test"
        assert defn.rules == ()

    def test_strategy_signal(self):
        signal = StrategySignal(
            symbol="RELIANCE",
            signal=SignalType.BUY,
            confidence=85.0,
        )
        assert signal.symbol == "RELIANCE"
        assert signal.confidence == 85.0

    def test_matched_rule(self):
        rule = MatchedRule(
            rule_name="Test",
            matched=True,
            signal=SignalType.BUY,
        )
        assert rule.matched is True

    def test_strategy_statistics(self):
        stats = StrategyStatistics(total_symbols=100)
        assert stats.total_symbols == 100

    def test_strategy_result(self):
        result = StrategyResult(strategy_name="Test")
        assert result.strategy_name == "Test"


# ---------------------------------------------------------------------------
# Engine tests
# ---------------------------------------------------------------------------


class TestStrategyEngine:
    def test_evaluate_single(self):
        engine = StrategyFactory.create()
        definition = _simple_definition()
        data = _data(roce=25, trend="Bullish")

        signal = engine.evaluate(definition, "RELIANCE", data)

        assert signal.symbol == "RELIANCE"
        assert signal.signal in (SignalType.BUY, SignalType.STRONG_BUY, SignalType.HOLD)
        assert signal.confidence >= 0
        assert signal.total_rules == 2

    def test_evaluate_many(self):
        engine = StrategyFactory.create()
        definition = _simple_definition()
        symbols_data = {
            "RELIANCE": _data(roce=25, trend="Bullish"),
            "TCS": _data(roce=15, trend="Bearish"),
            "INFY": _data(roce=30, trend="Bullish"),
        }

        signals = engine.evaluate_many(definition, symbols_data)

        assert len(signals) == 3
        assert all(isinstance(s, StrategySignal) for s in signals)

    def test_evaluate_empty_universe(self):
        engine = StrategyFactory.create()
        definition = _simple_definition()

        signals = engine.evaluate_many(definition, {})
        assert len(signals) == 0

    def test_evaluate_matched_rules(self):
        engine = StrategyFactory.create()
        definition = _simple_definition()
        data = _data(roce=25, trend="Bullish")

        signal = engine.evaluate(definition, "RELIANCE", data)

        assert len(signal.matched_rules) == 2

    def test_evaluate_failed_rules(self):
        rules = (
            create_rule(
                name="ROCE > 30",
                conditions=ConditionGroup(
                    operator=LogicalOperator.AND,
                    conditions=(Condition(field="fundamentals.roce", operator=ComparisonOperator.GT, value=30),),
                ),
                signal=SignalType.BUY,
            ),
            create_rule(
                name="Trend = Bullish",
                conditions=ConditionGroup(
                    operator=LogicalOperator.AND,
                    conditions=(Condition(field="technicals.trend_state", operator=ComparisonOperator.EQ, value="Bullish"),),
                ),
                signal=SignalType.BUY,
            ),
        )
        definition = StrategyDefinition(
            metadata=StrategyMetadata(name="Test"),
            rules=rules,
        )
        engine = StrategyFactory.create()
        data = _data(roce=25, trend="Bullish")

        signal = engine.evaluate(definition, "RELIANCE", data)

        assert len(signal.matched_rules) == 1
        assert len(signal.failed_rules) == 1

    def test_evaluate_no_rules(self):
        definition = StrategyDefinition(
            metadata=StrategyMetadata(name="Empty"),
            rules=(),
        )
        engine = StrategyFactory.create()
        data = _data()

        signal = engine.evaluate(definition, "RELIANCE", data)

        assert signal.signal == SignalType.HOLD
        assert signal.confidence == 0.0

    def test_evaluate_and_rank(self):
        engine = StrategyFactory.create()
        definition = _simple_definition()
        symbols_data = {
            "A": _data(roce=30, trend="Bullish"),
            "B": _data(roce=10, trend="Bearish"),
        }

        signals = engine.evaluate_and_rank(definition, symbols_data)

        assert len(signals) == 2
        assert signals[0].confidence >= signals[1].confidence

    def test_signal_explainability(self):
        engine = StrategyFactory.create()
        definition = _simple_definition()
        data = _data(roce=25, trend="Bullish")

        signal = engine.evaluate(definition, "RELIANCE", data)

        assert len(signal.matched_rules) > 0 or len(signal.failed_rules) > 0
        for rule in signal.matched_rules:
            assert rule.rule_name
            assert rule.signal

    def test_custom_signal_types(self):
        rules = (
            create_rule(
                name="Strong Buy Rule",
                conditions=ConditionGroup(
                    operator=LogicalOperator.AND,
                    conditions=(Condition(field="fundamentals.roce", operator=ComparisonOperator.GT, value=30),),
                ),
                signal=SignalType.STRONG_BUY,
                weight=1.0,
            ),
        )
        definition = StrategyDefinition(
            metadata=StrategyMetadata(name="Strong Buy Test"),
            rules=rules,
        )
        engine = StrategyFactory.create()
        data = _data(roce=35)

        signal = engine.evaluate(definition, "RELIANCE", data)

        assert signal.signal in (SignalType.STRONG_BUY, SignalType.BUY, SignalType.HOLD)


# ---------------------------------------------------------------------------
# Factory tests
# ---------------------------------------------------------------------------


class TestStrategyFactory:
    def test_create_default(self):
        engine = StrategyFactory.create()
        assert engine is not None

    def test_create_custom_rules_only(self):
        engine = StrategyFactory.create_with_custom_rules()
        assert engine.rule_registry.registered_names() == ()

    def test_create_from_registry(self):
        registry = RuleRegistry()
        engine = StrategyFactory.create_from_registry(registry)
        assert engine.rule_registry is registry


# ---------------------------------------------------------------------------
# Exception tests
# ---------------------------------------------------------------------------


class TestExceptions:
    def test_strategy_error(self):
        from backend.strategy.exceptions import StrategyError

        with pytest.raises(StrategyError):
            raise StrategyError("test")

    def test_rule_not_found(self):
        with pytest.raises(RuleNotFoundError) as excinfo:
            raise RuleNotFoundError("my_rule")
        assert excinfo.value.name == "my_rule"
        assert "my_rule" in str(excinfo.value)

    def test_empty_universe(self):
        with pytest.raises(EmptyUniverseError):
            raise EmptyUniverseError()

    def test_invalid_condition(self):
        with pytest.raises(InvalidConditionError):
            raise InvalidConditionError("bad")


# ---------------------------------------------------------------------------
# Integration tests
# ---------------------------------------------------------------------------


class TestIntegration:
    def test_complete_strategy_flow(self):
        """Test a complete strategy flow with multiple rules."""
        rules = (
            create_buy_rule("ROCE > 20", "fundamentals.roce", ComparisonOperator.GT, 20, weight=0.25),
            create_buy_rule("ROE > 15", "fundamentals.roe", ComparisonOperator.GT, 15, weight=0.25),
            create_trend_rule("Bullish", weight=0.25),
            create_momentum_rule("Positive", weight=0.25),
        )
        definition = StrategyDefinition(
            metadata=StrategyMetadata(name="Growth Strategy"),
            rules=rules,
        )

        engine = StrategyFactory.create()
        symbols_data = {
            "RELIANCE": _data(roce=25, roe=20, trend="Bullish", momentum="Positive"),
            "TCS": _data(roce=15, roe=25, trend="Bearish", momentum="Negative"),
            "INFY": _data(roce=30, roe=18, trend="Bullish", momentum="Positive"),
        }

        signals = engine.evaluate_many(definition, symbols_data)

        assert len(signals) == 3
        for signal in signals:
            assert signal.total_rules == 4
            assert signal.confidence >= 0

    def test_all_signal_types(self):
        """Test that all signal types are defined."""
        assert len(SignalType) == 8
        types = [s.value for s in SignalType]
        assert "STRONG_BUY" in types
        assert "BUY" in types
        assert "HOLD" in types
        assert "REDUCE" in types
        assert "SELL" in types
        assert "STRONG_SELL" in types
        assert "WATCH" in types
        assert "IGNORE" in types

    def test_nested_rule_groups(self):
        """Test nested rule groups."""
        definition = StrategyDefinition(
            metadata=StrategyMetadata(name="Nested Test"),
            rules=(
                create_rule(
                    name="Complex Rule",
                    conditions=ConditionGroup(
                        operator=LogicalOperator.AND,
                        conditions=(
                            Condition(field="fundamentals.roce", operator=ComparisonOperator.GT, value=20),
                        ),
                        groups=(
                            ConditionGroup(
                                operator=LogicalOperator.OR,
                                conditions=(
                                    Condition(field="technicals.trend_state", operator=ComparisonOperator.EQ, value="Bullish"),
                                    Condition(field="technicals.momentum_state", operator=ComparisonOperator.EQ, value="Positive"),
                                ),
                            ),
                        ),
                    ),
                    signal=SignalType.BUY,
                ),
            ),
        )

        engine = StrategyFactory.create()

        data_bullish = _data(roce=25, trend="Bullish", momentum="Negative")
        signal = engine.evaluate(definition, "A", data_bullish)
        assert signal.matched_rules[0].matched is True

        data_neutral = _data(roce=25, trend="Neutral", momentum="Neutral")
        signal = engine.evaluate(definition, "B", data_neutral)
        assert signal.failed_rules[0].matched is False

    def test_all_comparison_operators(self):
        """Test all comparison operators."""
        operators = [
            (ComparisonOperator.EQ, 10, 10, True),
            (ComparisonOperator.EQ, 10, 20, False),
            (ComparisonOperator.NEQ, 10, 20, True),
            (ComparisonOperator.NEQ, 10, 10, False),
            (ComparisonOperator.GT, 15, 10, True),
            (ComparisonOperator.GT, 5, 10, False),
            (ComparisonOperator.GTE, 10, 10, True),
            (ComparisonOperator.GTE, 9, 10, False),
            (ComparisonOperator.LT, 5, 10, True),
            (ComparisonOperator.LT, 15, 10, False),
            (ComparisonOperator.LTE, 10, 10, True),
            (ComparisonOperator.LTE, 11, 10, False),
            (ComparisonOperator.IN, 5, [1, 5, 10], True),
            (ComparisonOperator.IN, 3, [1, 5, 10], False),
            (ComparisonOperator.NOT_IN, 3, [1, 5, 10], True),
            (ComparisonOperator.NOT_IN, 5, [1, 5, 10], False),
            (ComparisonOperator.BETWEEN, 15, [10, 20], True),
            (ComparisonOperator.BETWEEN, 5, [10, 20], False),
        ]

        for op, actual, expected, should_pass in operators:
            cond = Condition(field="x", operator=op, value=expected)
            result = evaluate_condition(cond, {"x": actual})
            assert result == should_pass, f"Failed for {op.value}: {actual} {op.value} {expected}"

    def test_signal_confidence_scoring(self):
        """Test confidence scoring for different scenarios."""
        assert signal_confidence(10, 10, SignalType.BUY) == 100.0
        assert signal_confidence(5, 10, SignalType.BUY) == 50.0
        assert signal_confidence(0, 10, SignalType.BUY) == 0.0
        assert signal_confidence(10, 10, SignalType.WATCH) == 50.0
        assert signal_confidence(10, 10, SignalType.HOLD) == 100.0
