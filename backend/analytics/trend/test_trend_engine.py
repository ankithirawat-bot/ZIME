"""
Trend Engine tests.

Covers every trend state, mixed and conflicting signals, missing/edge data,
registry integration, and that the public API never exposes indicator values.
"""

from __future__ import annotations

from datetime import date, timedelta

import pytest

from backend.analytics.models import (
    AnalyticsContext,
    CorporateAction,
    MarketBar,
    TrendConfig,
)
from backend.analytics.trend.evaluators import WeightedEvaluator
from backend.analytics.trend.evidence import Evidence, evidence_texts
from backend.analytics.trend.exceptions import SignalError
from backend.analytics.trend.models import EvaluatorResult, SignalOutput, TrendState
from backend.analytics.trend.scoring import TrendScorer
from backend.analytics.trend.signals import (
    SignalRegistry,
    build_default_signal_registry,
    moving_average_alignment,
    slope_direction,
)
from backend.analytics.trend.trend_engine import TrendEngine


def _bar(day: int, close: float) -> MarketBar:
    return MarketBar(
        trade_date=date(2024, 1, 1) + timedelta(days=day),
        open=close - 0.5, high=close + 1, low=close - 1, close=close, volume=1000,
    )


def _series(n: int, fn) -> tuple[MarketBar, ...]:
    return tuple(_bar(i, fn(i)) for i in range(n))


CFG = TrendConfig(
    ema_short_period=5, ema_mid_period=10, sma_long_period=20,
    slope_window=10, structure_window=15, persistence_threshold=15,
)
BEAR_CFG = TrendConfig(
    ema_short_period=5, ema_mid_period=10, sma_long_period=20,
    slope_window=10, structure_window=15, persistence_threshold=15,
    weight_ma=0.1, weight_structure=0.4, weight_slope=0.4, weight_persistence=0.1,
)


def _ctx(prices, config=CFG, actions=()):
    return AnalyticsContext(
        symbol="RELIANCE", exchange="NSE", prices=prices, config=config,
        corporate_actions=actions,
    )


class TestTrendStates:
    def test_strong_bullish(self):
        fact = TrendEngine().analyze(_ctx(_series(40, lambda i: 100 + i)))
        assert fact.state == "Strong Bullish"
        assert fact.confidence > 80

    def test_bullish(self):
        fact = TrendEngine().analyze(_ctx(_series(25, lambda i: 100 + (i if i < 10 else 10))))
        assert fact.state == "Bullish"

    def test_neutral(self):
        fact = TrendEngine().analyze(_ctx(_series(40, lambda i: 100 + (0.05 * i if i < 10 else 0.5))))
        assert fact.state == "Neutral"
        assert 0 < fact.confidence <= 100

    def test_bearish(self):
        fact = TrendEngine().analyze(_ctx(_series(40, lambda i: 100 - 0.15 * i), config=BEAR_CFG))
        assert fact.state == "Bearish"

    def test_strong_bearish(self):
        fact = TrendEngine().analyze(_ctx(_series(40, lambda i: 100 - i)))
        assert fact.state == "Strong Bearish"
        assert fact.confidence > 80


class TestMixedAndConflicting:
    def _conflict_series(self):
        return _series(40, lambda i: 100 + i if i < 35 else 135 - (i - 35) * 4)

    def test_conflicting_signals_downgraded(self):
        reg = SignalRegistry()
        reg.register(
            "bull", lambda ctx: SignalOutput("bull", 1.0, (Evidence("bull", "bullish"),)),
        )
        reg.register(
            "bear", lambda ctx: SignalOutput("bear", -0.1, (Evidence("bear", "bearish"),)),
        )
        fact = TrendEngine(registry=reg).analyze(_ctx(self._conflict_series()))
        assert fact.metadata["conflict"] is True
        assert fact.state == "Neutral"
        assert any("Conflicting signals" in w for w in fact.metadata["warnings"])

    def test_mixed_signals_resolved(self):
        engine = TrendEngine(evaluator=WeightedEvaluator(conflict_threshold=0.3))
        fact = engine.analyze(_ctx(self._conflict_series()))
        assert fact.metadata["conflict"] is False
        assert fact.state in {s.value for s in TrendState}


class TestMissingAndEdgeData:
    def test_empty_prices(self):
        fact = TrendEngine().analyze(_ctx(()))
        assert fact.state == "Neutral"
        assert fact.confidence == 0.0
        assert any("No price data" in w for w in fact.metadata["warnings"])

    def test_single_bar(self):
        fact = TrendEngine().analyze(_ctx(_series(1, lambda i: 100)))
        assert fact.state in {s.value for s in TrendState}
        assert 0 <= fact.confidence <= 100

    def test_partial_data_warning(self):
        fact = TrendEngine().analyze(_ctx(_series(5, lambda i: 100 + i)))
        assert 0 < fact.metadata["completeness"] < 1
        assert any("lacked sufficient data" in w for w in fact.metadata["warnings"])

    def test_corporate_actions_in_evidence(self):
        actions = (CorporateAction(date(2024, 1, 20), "SPLIT", 2.0),)
        fact = TrendEngine().analyze(_ctx(_series(40, lambda i: 100 + i), actions=actions))
        assert any("Corporate action" in e for e in fact.evidence)


class TestPublicApi:
    def test_fact_shape(self):
        fact = TrendEngine().analyze(_ctx(_series(40, lambda i: 100 + i)))
        assert fact.name == "Trend"
        assert isinstance(fact.state, str)
        assert isinstance(fact.evidence, tuple)
        assert all(isinstance(e, str) for e in fact.evidence)
        assert 0 <= fact.confidence <= 100

    def test_no_indicator_values_exposed(self):
        fact = TrendEngine().analyze(_ctx(_series(40, lambda i: 100 + i)))
        allowed = {
            "combined_score", "agreement", "completeness", "conflict",
            "signal_scores", "available_signals", "bars_analyzed", "warnings",
        }
        assert set(fact.metadata.keys()) <= allowed
        assert "ema" not in str(fact.metadata).lower()


class TestSignalRegistry:
    def test_default_signals_registered(self):
        reg = build_default_signal_registry()
        assert set(reg.names()) == {
            "ma_alignment", "structure", "slope", "persistence",
        }

    def test_get_missing_raises(self):
        with pytest.raises(SignalError):
            SignalRegistry().get("nope")

    def test_get_success(self):
        reg = build_default_signal_registry()
        assert callable(reg.get("ma_alignment"))

    def test_custom_signal_used_by_engine(self):
        reg = build_default_signal_registry()
        reg.register(
            "custom",
            lambda ctx: SignalOutput(
                "custom", 0.5, (Evidence("custom", "custom signal fired"),),
            ),
        )
        fact = TrendEngine(registry=reg).analyze(_ctx(_series(40, lambda i: 100 + i)))
        assert fact.metadata["signal_scores"]["custom"] == 0.5
        assert any("custom signal fired" in e for e in fact.evidence)


class TestEvaluatorAndScorer:
    def test_no_available_signals(self):
        result = WeightedEvaluator().evaluate([], CFG)
        assert result.combined_score == 0.0
        assert result.conflict is True
        assert result.available_count == 0

    def test_conflict_agreement(self):
        outputs = [
            SignalOutput("a", 1.0, ()),
            SignalOutput("b", -1.0, ()),
        ]
        result = WeightedEvaluator().evaluate(outputs, CFG)
        assert result.agreement == 0.0
        assert result.conflict is True

    def test_zero_weight_sum(self):
        cfg = TrendConfig(
            ema_short_period=5, ema_mid_period=10, sma_long_period=20,
            slope_window=10, structure_window=15, persistence_threshold=15,
            weight_ma=0.0, weight_structure=0.0, weight_slope=0.0, weight_persistence=0.0,
        )
        outputs = [SignalOutput("x", 1.0, ()), SignalOutput("y", -1.0, ())]
        result = WeightedEvaluator().evaluate(outputs, cfg)
        assert result.combined_score == 0.0

    def test_strong_bullish_score(self):
        result = EvaluatorResult(0.8, 1.0, 4, 4, (), False)
        scoring = TrendScorer().score(result, 1.0)
        assert scoring.state is TrendState.STRONG_BULLISH
        assert scoring.confidence > 80

    def test_conflict_downgrade(self):
        result = EvaluatorResult(-0.8, 0.0, 4, 4, (), True)
        scoring = TrendScorer().score(result, 1.0)
        assert scoring.state is TrendState.BEARISH
        assert scoring.confidence <= 50.0


class TestEvidence:
    def test_evidence_texts(self):
        items = (Evidence("s", "one"), Evidence("s", "two"))
        assert evidence_texts(items) == ("one", "two")


class TestTrendStateValues:
    def test_values(self):
        assert {s.value for s in TrendState} == {
            "Strong Bullish", "Bullish", "Neutral", "Bearish", "Strong Bearish",
        }


class TestDirectSignals:
    def test_moving_average_alignment_runs(self):
        out = moving_average_alignment(_ctx(_series(40, lambda i: 100 + i)))
        assert out.name == "ma_alignment"
        assert out.available is True
        assert -1.0 <= out.score <= 1.0

    def test_signal_unavailable_short(self):
        out = moving_average_alignment(_ctx(_series(5, lambda i: 100 + i)))
        assert out.available is False

    def test_slope_zero_base_price(self):
        bars = list(_series(40, lambda i: 100 + i))
        bars[29] = _bar(29, 0.0)
        out = slope_direction(_ctx(tuple(bars)))
        assert out.available is False
        assert any("Invalid base price" in e.text for e in out.evidence)
