"""
Volume Engine tests.

Covers every volume state, mixed and conflicting signals, missing/edge data,
registry integration, and that the public API never exposes indicator values.
"""

from __future__ import annotations

from datetime import date, timedelta

import pytest

from backend.analytics.models import AnalyticsContext, MarketBar
from backend.analytics.volume.evaluators import WeightedEvaluator
from backend.analytics.volume.evidence import Evidence, evidence_texts
from backend.analytics.volume.exceptions import SignalError
from backend.analytics.volume.models import (
    EvaluatorResult,
    SignalOutput,
    VolumeConfig,
    VolumeState,
)
from backend.analytics.volume.scoring import VolumeScorer
from backend.analytics.volume.signals import (
    SignalRegistry,
    accumulation_distribution,
    build_default_signal_registry,
    relative_volume,
    volume_consistency,
    volume_trend,
)
from backend.analytics.volume.volume_engine import VolumeEngine


def _mk(prices, volumes) -> tuple[MarketBar, ...]:
    return tuple(
        MarketBar(
            trade_date=date(2024, 1, 1) + timedelta(days=i),
            open=p - 0.5, high=p + 1, low=p - 1, close=p, volume=v,
        )
        for i, (p, v) in enumerate(zip(prices, volumes))
    )


CFG = VolumeConfig()

_N = 45
PRICES_UP = [100 + i * 0.5 for i in range(_N)]
VOLS_EXP_UP = [round(1000 * (1.05 ** i)) for i in range(_N)]

PRICES_OSC_UP = [100 + i * 0.3 + 3 * ((i % 2) * 2 - 1) for i in range(_N)]
VOLS_RAMP = [500 + i * 150 for i in range(_N)]

PRICES_FLAT = [100 + 0.5 * ((i % 2) * 2 - 1) for i in range(_N)]
VOLS_FLAT = [1000 + (50 if i % 7 == 0 else 0) for i in range(_N)]

PRICES_OSC_DN = [130 - i * 0.3 + 3 * ((i % 2) * 2 - 1) for i in range(_N)]
VOLS_DEC = [max(200, 3000 - i * 60) for i in range(_N)]

PRICES_DN = [200 - i * 0.5 for i in range(_N)]
VOLS_VB = [max(100, round(9000 * 0.95 ** i) - (i % 3) * 1500) for i in range(_N)]

VOLS_SPIKE = [2000] * 44 + [7000]


def _ctx(prices, volumes, config=CFG, actions=()):
    return AnalyticsContext(
        symbol="RELIANCE", exchange="NSE", prices=_mk(prices, volumes),
        config=config, corporate_actions=actions,
    )


class TestVolumeStates:
    def test_very_strong(self):
        fact = VolumeEngine().analyze(_ctx(PRICES_UP, VOLS_EXP_UP))
        assert fact.state == "Very Strong"
        assert fact.confidence > 80

    def test_strong(self):
        fact = VolumeEngine().analyze(_ctx(PRICES_OSC_UP, VOLS_RAMP))
        assert fact.state == "Strong"

    def test_neutral(self):
        fact = VolumeEngine().analyze(_ctx(PRICES_FLAT, VOLS_FLAT))
        assert fact.state == "Neutral"

    def test_weak(self):
        fact = VolumeEngine().analyze(_ctx(PRICES_OSC_DN, VOLS_DEC))
        assert fact.state == "Weak"

    def test_very_weak(self):
        fact = VolumeEngine().analyze(_ctx(PRICES_DN, VOLS_VB))
        assert fact.state == "Very Weak"
        assert fact.confidence > 80


class TestMixedAndConflicting:
    def test_conflicting_signals_downgraded(self):
        fact = VolumeEngine().analyze(_ctx(PRICES_OSC_UP, VOLS_SPIKE))
        assert fact.metadata["conflict"] is True
        assert fact.state == "Neutral"
        assert any("Conflicting signals" in w for w in fact.metadata["warnings"])

    def test_mixed_signals_resolved(self):
        fact = VolumeEngine().analyze(_ctx(PRICES_OSC_UP, VOLS_RAMP))
        assert fact.metadata["conflict"] is False
        assert fact.state in {s.value for s in VolumeState}


class TestMissingAndEdgeData:
    def test_empty_prices(self):
        fact = VolumeEngine().analyze(_ctx([], []))
        assert fact.state == "Neutral"
        assert fact.confidence == 0.0
        assert any("No price data" in w for w in fact.metadata["warnings"])

    def test_single_bar(self):
        fact = VolumeEngine().analyze(_ctx([100], [1000]))
        assert fact.state in {s.value for s in VolumeState}
        assert 0 <= fact.confidence <= 100

    def test_partial_data_warning(self):
        fact = VolumeEngine().analyze(_ctx(list(range(100, 112)), [1500] * 12))
        assert 0 < fact.metadata["completeness"] < 1
        assert any("lacked sufficient data" in w for w in fact.metadata["warnings"])


class TestPublicApi:
    def test_fact_shape(self):
        fact = VolumeEngine().analyze(_ctx(PRICES_UP, VOLS_EXP_UP))
        assert fact.name == "Volume"
        assert isinstance(fact.state, str)
        assert isinstance(fact.evidence, tuple)
        assert all(isinstance(e, str) for e in fact.evidence)
        assert 0 <= fact.confidence <= 100

    def test_no_indicator_values_exposed(self):
        fact = VolumeEngine().analyze(_ctx(PRICES_UP, VOLS_EXP_UP))
        allowed = {
            "combined_score", "agreement", "completeness", "conflict",
            "signal_scores", "available_signals", "bars_analyzed", "warnings",
        }
        assert set(fact.metadata.keys()) <= allowed
        low = str(fact.metadata).lower()
        assert "obv" not in low
        assert "vwap" not in low
        assert "cmf" not in low
        assert "ema" not in low


class TestSignalRegistry:
    def test_default_signals_registered(self):
        reg = build_default_signal_registry()
        assert set(reg.names()) == {
            "accumulation", "consistency", "relative_volume", "volume_trend",
        }

    def test_get_missing_raises(self):
        with pytest.raises(SignalError):
            SignalRegistry().get("nope")

    def test_get_success(self):
        reg = build_default_signal_registry()
        assert callable(reg.get("relative_volume"))

    def test_custom_signal_used_by_engine(self):
        reg = build_default_signal_registry()
        reg.register(
            "custom",
            lambda ctx: SignalOutput(
                "custom", 0.5, (Evidence("custom", "custom signal fired"),),
            ),
        )
        fact = VolumeEngine(registry=reg).analyze(_ctx(PRICES_UP, VOLS_EXP_UP))
        assert fact.metadata["signal_scores"]["custom"] == 0.5
        assert any("custom signal fired" in e for e in fact.evidence)


class TestEvaluatorAndScorer:
    def test_no_available_signals(self):
        result = WeightedEvaluator().evaluate([], CFG)
        assert result.combined_score == 0.0
        assert result.conflict is True
        assert result.available_count == 0

    def test_conflict_agreement(self):
        outputs = [SignalOutput("a", 1.0, ()), SignalOutput("b", -1.0, ())]
        result = WeightedEvaluator().evaluate(outputs, CFG)
        assert result.agreement == 0.0
        assert result.conflict is True

    def test_unanimous_when_under_two_directional(self):
        outputs = [SignalOutput("a", 0.0, ()), SignalOutput("b", 0.0, ())]
        result = WeightedEvaluator().evaluate(outputs, CFG)
        assert result.agreement == 1.0
        assert result.conflict is False

    def test_zero_weight_sum(self):
        cfg = VolumeConfig(
            relative_volume_window=20, volume_trend_window=10,
            accumulation_window=20, consistency_window=20,
            weight_relative_volume=0.0, weight_volume_trend=0.0,
            weight_accumulation=0.0, weight_consistency=0.0,
        )
        outputs = [SignalOutput("x", 1.0, ()), SignalOutput("y", -1.0, ())]
        result = WeightedEvaluator().evaluate(outputs, cfg)
        assert result.combined_score == 0.0

    def test_very_strong_score(self):
        result = EvaluatorResult(0.8, 1.0, 4, 4, (), False)
        scoring = VolumeScorer().score(result, 1.0)
        assert scoring.state is VolumeState.VERY_STRONG
        assert scoring.confidence > 80

    def test_conflict_downgrade(self):
        result = EvaluatorResult(-0.8, 0.0, 4, 4, (), True)
        scoring = VolumeScorer().score(result, 1.0)
        assert scoring.state is VolumeState.WEAK
        assert scoring.confidence <= 50.0


class TestEvidence:
    def test_evidence_texts(self):
        items = (Evidence("s", "one"), Evidence("s", "two"))
        assert evidence_texts(items) == ("one", "two")


class TestVolumeStateValues:
    def test_values(self):
        assert {s.value for s in VolumeState} == {
            "Very Strong", "Strong", "Neutral", "Weak", "Very Weak",
        }


class TestDirectSignals:
    def test_relative_volume_available(self):
        out = relative_volume(_ctx(PRICES_UP, VOLS_EXP_UP))
        assert out.name == "relative_volume"
        assert out.available is True
        assert -1.0 <= out.score <= 1.0

    def test_relative_volume_unavailable_short(self):
        out = relative_volume(_ctx([100], [1000]))
        assert out.available is False

    def test_relative_volume_zero_average(self):
        out = relative_volume(_ctx([100, 101, 102], [0, 0, 0]))
        assert out.available is False

    def test_volume_trend_unavailable_short(self):
        out = volume_trend(_ctx(list(range(100, 112)), [1500] * 12))
        assert out.available is False

    def test_volume_trend_zero_baseline(self):
        vols = [0] * 35 + [100] * 10
        out = volume_trend(_ctx(list(range(100, 145)), vols))
        assert out.available is False

    def test_accumulation_distribution(self):
        out = accumulation_distribution(_ctx(PRICES_DN, [1000] * _N))
        assert out.name == "accumulation"
        assert out.score < 0

    def test_accumulation_zero_total(self):
        out = accumulation_distribution(_ctx([100, 101, 102], [0, 0, 0]))
        assert out.available is False

    def test_consistency_zero_mean(self):
        out = volume_consistency(_ctx([100, 101, 102], [0, 0, 0]))
        assert out.available is False

    def test_consistency_runs(self):
        out = volume_consistency(_ctx(PRICES_UP, VOLS_EXP_UP))
        assert out.name == "consistency"
        assert -1.0 <= out.score <= 1.0
