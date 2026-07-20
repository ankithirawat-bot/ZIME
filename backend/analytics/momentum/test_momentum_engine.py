"""
Momentum Engine tests.

Covers every momentum state, mixed and conflicting signals, missing/edge data,
registry integration, and that the public API never exposes indicator values.
"""

from __future__ import annotations

from datetime import date, timedelta

import pytest

from backend.analytics.models import (
    AnalyticsContext,
    CorporateAction,
    MarketBar,
)
from backend.analytics.momentum.evaluators import WeightedEvaluator
from backend.analytics.momentum.evidence import Evidence, evidence_texts
from backend.analytics.momentum.exceptions import SignalError
from backend.analytics.momentum.models import (
    EvaluatorResult,
    MomentumConfig,
    MomentumState,
    SignalOutput,
)
from backend.analytics.momentum.momentum_engine import MomentumEngine
from backend.analytics.momentum.scoring import MomentumScorer
from backend.analytics.momentum.signals import (
    SignalRegistry,
    _pct,
    breakout_continuation,
    build_default_signal_registry,
    momentum_persistence,
    rate_of_change,
)


def _bar(day: int, close: float) -> MarketBar:
    return MarketBar(
        trade_date=date(2024, 1, 1) + timedelta(days=day),
        open=close - 0.5, high=close + 1, low=close - 1, close=close, volume=1000,
    )


def _series(n: int, fn) -> tuple[MarketBar, ...]:
    return tuple(_bar(i, fn(i)) for i in range(n))


CFG = MomentumConfig(
    roc_short_period=10, roc_long_period=30, acceleration_window=10,
    momentum_persistence_threshold=20, breakout_window=20,
    weight_roc=0.30, weight_acceleration=0.25,
    weight_momentum_persistence=0.20, weight_breakout=0.25,
)


def _ctx(prices, config=CFG, actions=()):
    return AnalyticsContext(
        symbol="RELIANCE", exchange="NSE", prices=prices, config=config,
        corporate_actions=actions,
    )


class TestMomentumStates:
    def test_very_strong(self):
        fact = MomentumEngine().analyze(_ctx(_series(45, lambda i: 100 + (i * i) * 0.08)))
        assert fact.state == "Very Strong"
        assert fact.confidence > 80

    def test_strong(self):
        fact = MomentumEngine().analyze(_ctx(_series(45, lambda i: 100 + 2 * i)))
        assert fact.state == "Strong"

    def test_neutral(self):
        fact = MomentumEngine().analyze(_ctx(_series(45, lambda i: 100 + ((i // 5) % 2) * 4)))
        assert fact.state == "Neutral"

    def test_weak(self):
        fact = MomentumEngine().analyze(_ctx(_series(45, lambda i: 100 - (i ** 1.6) * 0.5)))
        assert fact.state == "Weak"

    def test_very_weak(self):
        fact = MomentumEngine().analyze(_ctx(_series(45, lambda i: 100 - 2 * i)))
        assert fact.state == "Very Weak"
        assert fact.confidence > 80


class TestMixedAndConflicting:
    def test_conflicting_signals_downgraded(self):
        reg = SignalRegistry()
        reg.register(
            "bull", lambda ctx: SignalOutput("bull", 1.0, (Evidence("bull", "bullish"),)),
        )
        reg.register(
            "bear", lambda ctx: SignalOutput("bear", -0.1, (Evidence("bear", "bearish"),)),
        )
        fact = MomentumEngine(registry=reg).analyze(_ctx(_series(45, lambda i: 100 + 2 * i)))
        assert fact.metadata["conflict"] is True
        assert fact.state == "Neutral"
        assert any("Conflicting signals" in w for w in fact.metadata["warnings"])

    def test_mixed_signals_resolved(self):
        fact = MomentumEngine().analyze(_ctx(_series(45, lambda i: 100 + 2 * i)))
        assert fact.metadata["conflict"] is False
        assert fact.state in {s.value for s in MomentumState}


class TestMissingAndEdgeData:
    def test_empty_prices(self):
        fact = MomentumEngine().analyze(_ctx(()))
        assert fact.state == "Neutral"
        assert fact.confidence == 0.0
        assert any("No price data" in w for w in fact.metadata["warnings"])

    def test_single_bar(self):
        fact = MomentumEngine().analyze(_ctx(_series(1, lambda i: 100)))
        assert fact.state in {s.value for s in MomentumState}
        assert 0 <= fact.confidence <= 100

    def test_partial_data_warning(self):
        fact = MomentumEngine().analyze(_ctx(_series(12, lambda i: 100 + i)))
        assert 0 < fact.metadata["completeness"] < 1
        assert any("lacked sufficient data" in w for w in fact.metadata["warnings"])

    def test_corporate_actions_in_evidence(self):
        actions = (CorporateAction(date(2024, 1, 20), "SPLIT", 2.0),)
        fact = MomentumEngine().analyze(
            _ctx(_series(45, lambda i: 100 + 2 * i), actions=actions)
        )
        assert any("Corporate action" in e for e in fact.evidence)


class TestPublicApi:
    def test_fact_shape(self):
        fact = MomentumEngine().analyze(_ctx(_series(45, lambda i: 100 + 2 * i)))
        assert fact.name == "Momentum"
        assert isinstance(fact.state, str)
        assert isinstance(fact.evidence, tuple)
        assert all(isinstance(e, str) for e in fact.evidence)
        assert 0 <= fact.confidence <= 100

    def test_no_indicator_values_exposed(self):
        fact = MomentumEngine().analyze(_ctx(_series(45, lambda i: 100 + 2 * i)))
        allowed = {
            "combined_score", "agreement", "completeness", "conflict",
            "signal_scores", "available_signals", "bars_analyzed", "warnings",
        }
        assert set(fact.metadata.keys()) <= allowed
        assert "ema" not in str(fact.metadata).lower()
        assert "roc" not in str({k: v for k, v in fact.metadata.items() if k != "signal_scores"}).lower()


class TestSignalRegistry:
    def test_default_signals_registered(self):
        reg = build_default_signal_registry()
        assert set(reg.names()) == {"acceleration", "breakout", "persistence", "roc"}

    def test_get_missing_raises(self):
        with pytest.raises(SignalError):
            SignalRegistry().get("nope")

    def test_get_success(self):
        reg = build_default_signal_registry()
        assert callable(reg.get("roc"))

    def test_custom_signal_used_by_engine(self):
        reg = build_default_signal_registry()
        reg.register(
            "custom",
            lambda ctx: SignalOutput(
                "custom", 0.5, (Evidence("custom", "custom signal fired"),),
            ),
        )
        fact = MomentumEngine(registry=reg).analyze(_ctx(_series(45, lambda i: 100 + 2 * i)))
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
        cfg = MomentumConfig(
            roc_short_period=10, roc_long_period=30, acceleration_window=10,
            momentum_persistence_threshold=20, breakout_window=20,
            weight_roc=0.0, weight_acceleration=0.0,
            weight_momentum_persistence=0.0, weight_breakout=0.0,
        )
        outputs = [SignalOutput("x", 1.0, ()), SignalOutput("y", -1.0, ())]
        result = WeightedEvaluator().evaluate(outputs, cfg)
        assert result.combined_score == 0.0

    def test_very_strong_score(self):
        result = EvaluatorResult(0.8, 1.0, 4, 4, (), False)
        scoring = MomentumScorer().score(result, 1.0)
        assert scoring.state is MomentumState.VERY_STRONG
        assert scoring.confidence > 80

    def test_conflict_downgrade(self):
        result = EvaluatorResult(-0.8, 0.0, 4, 4, (), True)
        scoring = MomentumScorer().score(result, 1.0)
        assert scoring.state is MomentumState.WEAK
        assert scoring.confidence <= 50.0


class TestEvidence:
    def test_evidence_texts(self):
        items = (Evidence("s", "one"), Evidence("s", "two"))
        assert evidence_texts(items) == ("one", "two")


class TestMomentumStateValues:
    def test_values(self):
        assert {s.value for s in MomentumState} == {
            "Very Strong", "Strong", "Neutral", "Weak", "Very Weak",
        }


class TestDirectSignals:
    def test_pct_helper(self):
        assert _pct(5, 10) == 0.5
        assert _pct(5, 0) == 0.0

    def test_rate_of_change_available(self):
        out = rate_of_change(_ctx(_series(45, lambda i: 100 + 2 * i)))
        assert out.name == "roc"
        assert out.available is True
        assert -1.0 <= out.score <= 1.0

    def test_rate_of_change_unavailable(self):
        out = rate_of_change(_ctx(_series(12, lambda i: 100 + i)))
        assert out.available is False

    def test_rate_of_change_zero_base(self):
        bars = list(_series(45, lambda i: 100 + 2 * i))
        bars[34] = _bar(34, 0.0)
        out = rate_of_change(_ctx(tuple(bars)))
        assert out.available is False

    def test_persistence_corporate_action(self):
        actions = (CorporateAction(date(2024, 1, 20), "SPLIT", 2.0),)
        out = momentum_persistence(_ctx(_series(45, lambda i: 100 + 2 * i), actions=actions))
        assert any("Corporate action" in e.text for e in out.evidence)

    def test_breakout_runs(self):
        out = breakout_continuation(_ctx(_series(45, lambda i: 100 + 2 * i)))
        assert out.name == "breakout"
        assert -1.0 <= out.score <= 1.0
