"""
Relative Strength Engine tests.

Covers every relative-strength state, mixed and conflicting signals,
missing/edge data, registry integration, and that the public API never exposes
indicator values.
"""

from __future__ import annotations

import math
from datetime import date, timedelta

import pytest

from backend.analytics.models import AnalyticsContext, MarketBar
from backend.analytics.relative_strength.evaluators import WeightedEvaluator
from backend.analytics.relative_strength.evidence import Evidence, evidence_texts
from backend.analytics.relative_strength.exceptions import SignalError
from backend.analytics.relative_strength.models import (
    EvaluatorResult,
    RelativeStrengthConfig,
    RelativeStrengthState,
    SignalOutput,
)
from backend.analytics.relative_strength.relative_strength_engine import (
    RelativeStrengthEngine,
)
from backend.analytics.relative_strength.scoring import RelativeStrengthScorer
from backend.analytics.relative_strength.signals import (
    SignalRegistry,
    _window_return,
    benchmark_outperformance,
    build_default_signal_registry,
    industry_leadership,
    relative_momentum_persistence,
    sector_leadership,
)


def _mk(prices) -> tuple[MarketBar, ...]:
    return tuple(
        MarketBar(
            trade_date=date(2024, 1, 1) + timedelta(days=i),
            open=p - 0.5, high=p + 1, low=p - 1, close=p, volume=1000,
        )
        for i, p in enumerate(prices)
    )


N = 45
CFG = RelativeStrengthConfig(rs_window=30, rs_persistence_window=20)

INSTR_VS = [100 + i * 1.0 for i in range(N)]
BENCH = [100 + i * 0.3 for i in range(N)]
SECTOR_VS = [100 + i * 0.5 for i in range(N)]
IND_VS = [100 + i * 0.4 for i in range(N)]

INSTR_VW = [150 - i * 1.0 for i in range(N)]

INSTR_STR = [100 + i * 0.6 for i in range(N)]
SECTOR_STR = [100 + i * 0.45 for i in range(N)]
IND_STR = [100 + i * 0.4 for i in range(N)]

INSTR_WK = [100 + i * 0.2 for i in range(N)]
SECTOR_WK = [100 + i * 0.28 for i in range(N)]
IND_WK = [100 + i * 0.25 for i in range(N)]

INSTR_NEUT = [100 + i * 0.3 + 2 * math.sin(i * 0.7) for i in range(N)]
SECTOR_NEUT = [100 + i * 0.3 + 1.5 * math.sin(i * 0.7 + 1) for i in range(N)]
IND_NEUT = [100 + i * 0.3 + 1.2 * math.sin(i * 0.7 + 2) for i in range(N)]

INSTR_CONF = [
    (100 + i * 0.1) if i < 40 else (100 + 40 * 0.1 + (i - 39) * 6) for i in range(N)
]
SECTOR_CONF = [100 + i * 1.5 for i in range(N)]


def _ctx(instr, bench=(), sector=(), industry=(), config=CFG, actions=()):
    return AnalyticsContext(
        symbol="RELIANCE", exchange="NSE", prices=_mk(instr),
        benchmark_prices=_mk(bench), sector_prices=_mk(sector),
        industry_prices=_mk(industry), config=config, corporate_actions=actions,
    )


class TestRelativeStrengthStates:
    def test_very_strong(self):
        fact = RelativeStrengthEngine().analyze(_ctx(INSTR_VS, BENCH, SECTOR_VS, IND_VS))
        assert fact.state == "Very Strong"
        assert fact.confidence > 80

    def test_strong(self):
        fact = RelativeStrengthEngine().analyze(_ctx(INSTR_STR, BENCH, SECTOR_STR, IND_STR))
        assert fact.state == "Strong"

    def test_neutral(self):
        fact = RelativeStrengthEngine().analyze(_ctx(INSTR_NEUT, BENCH, SECTOR_NEUT, IND_NEUT))
        assert fact.state == "Neutral"

    def test_weak(self):
        fact = RelativeStrengthEngine().analyze(_ctx(INSTR_WK, BENCH, SECTOR_WK, IND_WK))
        assert fact.state == "Weak"

    def test_very_weak(self):
        fact = RelativeStrengthEngine().analyze(_ctx(INSTR_VW, BENCH, SECTOR_VS, IND_VS))
        assert fact.state == "Very Weak"
        assert fact.confidence > 80


class TestMixedAndConflicting:
    def test_conflicting_signals_downgraded(self):
        fact = RelativeStrengthEngine().analyze(_ctx(INSTR_CONF, BENCH, SECTOR_CONF, BENCH))
        assert fact.metadata["conflict"] is True
        assert fact.state == "Neutral"
        assert any("Conflicting signals" in w for w in fact.metadata["warnings"])

    def test_mixed_signals_resolved(self):
        fact = RelativeStrengthEngine().analyze(_ctx(INSTR_VS, BENCH, SECTOR_VS, IND_VS))
        assert fact.metadata["conflict"] is False
        assert fact.state in {s.value for s in RelativeStrengthState}


class TestMissingAndEdgeData:
    def test_empty_prices(self):
        fact = RelativeStrengthEngine().analyze(_ctx([]))
        assert fact.state == "Neutral"
        assert fact.confidence == 0.0
        assert any("No price data" in w for w in fact.metadata["warnings"])

    def test_single_bar(self):
        fact = RelativeStrengthEngine().analyze(_ctx([100]))
        assert fact.state in {s.value for s in RelativeStrengthState}
        assert 0 <= fact.confidence <= 100

    def test_partial_data_warning(self):
        fact = RelativeStrengthEngine().analyze(_ctx(INSTR_VS, BENCH))
        assert 0 < fact.metadata["completeness"] < 1
        assert any("lacked sufficient data" in w for w in fact.metadata["warnings"])


class TestPublicApi:
    def test_fact_shape(self):
        fact = RelativeStrengthEngine().analyze(_ctx(INSTR_VS, BENCH, SECTOR_VS, IND_VS))
        assert fact.name == "Relative Strength"
        assert isinstance(fact.state, str)
        assert isinstance(fact.evidence, tuple)
        assert all(isinstance(e, str) for e in fact.evidence)
        assert 0 <= fact.confidence <= 100

    def test_no_indicator_values_exposed(self):
        fact = RelativeStrengthEngine().analyze(_ctx(INSTR_VS, BENCH, SECTOR_VS, IND_VS))
        allowed = {
            "combined_score", "agreement", "completeness", "conflict",
            "signal_scores", "available_signals", "bars_analyzed", "warnings",
        }
        assert set(fact.metadata.keys()) <= allowed
        low = str(fact.metadata).lower()
        assert "beta" not in low
        assert "correlation" not in low
        assert "alpha" not in low
        assert "rs_ratio" not in low
        assert "sharpe" not in low


class TestSignalRegistry:
    def test_default_signals_registered(self):
        reg = build_default_signal_registry()
        assert set(reg.names()) == {"benchmark", "industry", "persistence", "sector"}

    def test_get_missing_raises(self):
        with pytest.raises(SignalError):
            SignalRegistry().get("nope")

    def test_get_success(self):
        reg = build_default_signal_registry()
        assert callable(reg.get("benchmark"))

    def test_custom_signal_used_by_engine(self):
        reg = build_default_signal_registry()
        reg.register(
            "custom",
            lambda ctx: SignalOutput(
                "custom", 0.5, (Evidence("custom", "custom signal fired"),),
            ),
        )
        fact = RelativeStrengthEngine(registry=reg).analyze(
            _ctx(INSTR_VS, BENCH, SECTOR_VS, IND_VS)
        )
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
        cfg = RelativeStrengthConfig(
            rs_window=30, rs_persistence_window=20,
            weight_benchmark=0.0, weight_sector=0.0,
            weight_industry=0.0, weight_persistence=0.0,
        )
        outputs = [SignalOutput("x", 1.0, ()), SignalOutput("y", -1.0, ())]
        result = WeightedEvaluator().evaluate(outputs, cfg)
        assert result.combined_score == 0.0

    def test_very_strong_score(self):
        result = EvaluatorResult(0.8, 1.0, 4, 4, (), False)
        scoring = RelativeStrengthScorer().score(result, 1.0)
        assert scoring.state is RelativeStrengthState.VERY_STRONG
        assert scoring.confidence > 80

    def test_conflict_downgrade(self):
        result = EvaluatorResult(-0.8, 0.0, 4, 4, (), True)
        scoring = RelativeStrengthScorer().score(result, 1.0)
        assert scoring.state is RelativeStrengthState.WEAK
        assert scoring.confidence <= 50.0


class TestEvidence:
    def test_evidence_texts(self):
        items = (Evidence("s", "one"), Evidence("s", "two"))
        assert evidence_texts(items) == ("one", "two")


class TestRelativeStrengthStateValues:
    def test_values(self):
        assert {s.value for s in RelativeStrengthState} == {
            "Very Strong", "Strong", "Neutral", "Weak", "Very Weak",
        }


class TestDirectSignals:
    def test_window_return(self):
        assert _window_return([1, 2], 5) is None
        assert _window_return([0, 0, 0], 1) is None
        assert _window_return([100, 110], 1) == 0.1

    def test_benchmark_available(self):
        out = benchmark_outperformance(_ctx(INSTR_VS, BENCH))
        assert out.name == "benchmark"
        assert out.available is True
        assert -1.0 <= out.score <= 1.0

    def test_benchmark_unavailable(self):
        out = benchmark_outperformance(_ctx(INSTR_VS))
        assert out.available is False

    def test_sector_unavailable(self):
        out = sector_leadership(_ctx(INSTR_VS, BENCH))
        assert out.available is False

    def test_industry_unavailable(self):
        out = industry_leadership(_ctx(INSTR_VS, BENCH))
        assert out.available is False

    def test_benchmark_zero_base_short(self):
        out = benchmark_outperformance(_ctx([0, 1, 2], [0, 0, 0]))
        assert out.available is False

    def test_benchmark_zero_base_long(self):
        instr = [0] * 5 + [100] * 30
        peer = [100] * 35
        out = benchmark_outperformance(_ctx(instr, peer))
        assert out.available is False

    def test_persistence_available(self):
        out = relative_momentum_persistence(_ctx(INSTR_VS, BENCH))
        assert out.name == "persistence"
        assert out.available is True

    def test_persistence_unavailable_short(self):
        out = relative_momentum_persistence(_ctx([100, 101, 102], [100, 101, 102]))
        assert out.available is False
