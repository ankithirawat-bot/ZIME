"""Tests for the Volatility Engine (analytics)."""

from __future__ import annotations

from datetime import date, timedelta

import pytest

from backend.analytics.models import AnalyticsContext, MarketBar
from backend.analytics.volatility.evaluators import WeightedEvaluator
from backend.analytics.volatility.exceptions import (
    InsufficientDataError,
    SignalError,
    VolatilityError,
)
from backend.analytics.volatility.models import (
    EvaluatorResult,
    SignalOutput,
    VolatilityConfig,
    VolatilityState,
)
from backend.analytics.volatility.scoring import VolatilityScorer
from backend.analytics.volatility.signals import (
    _stdev,
    build_default_signal_registry,
    historical_volatility,
    range_expansion,
    volatility_persistence,
    volatility_trend,
)
from backend.analytics.volatility.volatility_engine import VolatilityEngine


def _make_bars(sigma: float, n: int = 45, seed: int = 7, tight: bool = False) -> list[MarketBar]:
    import random

    random.seed(seed)
    closes = [100.0]
    for _ in range(n - 1):
        closes.append(closes[-1] * (1.0 + random.gauss(0.0, sigma)))

    bars: list[MarketBar] = []
    for i, c in enumerate(closes):
        pc = closes[i - 1] if i > 0 else c
        if tight:
            high = c + 0.01
            low = c - 0.01
        else:
            move = abs(c - pc)
            high = max(c, pc) + move * 0.3 + 0.01
            low = min(c, pc) - move * 0.3 - 0.01
        bars.append(
            MarketBar(
                trade_date=date(2024, 1, 1) + timedelta(days=i),
                open=pc,
                high=high,
                low=low,
                close=c,
                volume=1000,
            )
        )
    return bars


def _context(bars: list[MarketBar], config: VolatilityConfig | None = None) -> AnalyticsContext:
    return AnalyticsContext(
        symbol="ZIME",
        exchange="NSE",
        prices=tuple(bars),
        config=config or VolatilityConfig(),
    )


def _analyze(bars: list[MarketBar], config: VolatilityConfig | None = None):
    return VolatilityEngine().analyze(_context(bars, config))


class TestVolatilityStates:
    def test_very_low(self):
        fact = _analyze(_make_bars(0.0005))
        assert fact.state == VolatilityState.VERY_LOW
        assert fact.confidence > 0

    def test_low(self):
        fact = _analyze(_make_bars(0.006))
        assert fact.state == VolatilityState.LOW
        assert fact.confidence > 0

    def test_normal(self):
        fact = _analyze(_make_bars(0.012))
        assert fact.state == VolatilityState.NORMAL

    def test_high(self):
        fact = _analyze(_make_bars(0.022))
        assert fact.state == VolatilityState.HIGH
        assert fact.confidence > 0

    def test_very_high(self):
        fact = _analyze(_make_bars(0.03))
        assert fact.state == VolatilityState.VERY_HIGH
        assert fact.confidence > 0

    def test_state_ordering(self):
        states = [
            _analyze(_make_bars(s)).state
            for s in (0.0005, 0.006, 0.012, 0.022, 0.03)
        ]
        assert states == [
            VolatilityState.VERY_LOW,
            VolatilityState.LOW,
            VolatilityState.NORMAL,
            VolatilityState.HIGH,
            VolatilityState.VERY_HIGH,
        ]


class TestConflictAndConfidence:
    def test_conflict_downgrades(self):
        bars = _make_bars(0.022, tight=True)
        fact = _analyze(bars)
        assert fact.metadata["conflict"] is True
        assert fact.state != VolatilityState.VERY_HIGH

    def test_agreement_no_conflict(self):
        fact = _analyze(_make_bars(0.03))
        assert fact.metadata["conflict"] is False
        assert fact.metadata["agreement"] >= 0.8


class TestEdgeAndMissingData:
    def test_insufficient_bars(self):
        bars = _make_bars(0.022, n=10)
        fact = _analyze(bars)
        assert fact.metadata["completeness"] == 0.0
        assert fact.state == VolatilityState.NORMAL
        assert fact.confidence == 0.0
        assert fact.metadata["warnings"]

    def test_exactly_minimum_bars(self):
        bars = _make_bars(0.022, n=41)
        fact = _analyze(bars)
        assert fact.metadata["completeness"] == 1.0

    def test_empty_prices_raises(self):
        with pytest.raises(VolatilityError):
            _analyze([])

    def test_none_close_raises(self):
        bars = _make_bars(0.022, n=45)
        broken = list(bars)
        broken[10] = MarketBar(
            trade_date=broken[10].trade_date,
            open=broken[10].open,
            high=broken[10].high,
            low=broken[10].low,
            close=None,
            volume=broken[10].volume,
        )
        with pytest.raises(VolatilityError):
            _analyze(broken)

    def test_missing_prices_attribute_raises(self):
        ctx = AnalyticsContext(symbol="Z", exchange="NSE", prices=None)
        with pytest.raises(VolatilityError):
            VolatilityEngine().analyze(ctx)


class TestPublicApi:
    def test_no_raw_volatility_values_exposed(self):
        fact = _analyze(_make_bars(0.022))
        banned = {"atr", "bollinger", "vix", "volatility_value", "stddev", "std_dev"}
        flat = " ".join(str(k).lower() for k in fact.metadata)
        for token in banned:
            assert token not in flat
        assert fact.name == "Volatility"

    def test_signal_names(self):
        fact = _analyze(_make_bars(0.022))
        names = set(fact.metadata["signal_scores"])
        assert names == {
            "historical_volatility",
            "volatility_trend",
            "range_expansion",
            "persistence",
        }

    def test_warnings_present_for_low_completeness(self):
        fact = _analyze(_make_bars(0.022, n=25))
        assert any("sufficient data" in w.lower() for w in fact.metadata["warnings"])

    def test_warnings_no_prices(self):
        from backend.analytics.volatility.models import EvaluatorResult

        ctx = AnalyticsContext(symbol="X", exchange="NSE", prices=())
        result = EvaluatorResult(0.0, 1.0, 0, 0, (), False)
        warnings = VolatilityEngine()._warnings(ctx, [], result)
        assert any("No price data" in w for w in warnings)

    def test_exports(self):
        import backend.analytics
        import backend.analytics.volatility as vol

        assert hasattr(backend.analytics, "VolatilityEngine")
        assert hasattr(vol, "VolatilityEngine")
        assert hasattr(vol, "VolatilityState")
        assert hasattr(vol, "VolatilityConfig")


class TestSignals:
    def test_historical_volatility(self):
        out = historical_volatility(_context(_make_bars(0.03)))
        assert isinstance(out, SignalOutput)
        assert out.name == "historical_volatility"
        assert out.score > 0
        assert out.evidence

    def test_volatility_trend(self):
        out = volatility_trend(_context(_make_bars(0.03)))
        assert out.name == "volatility_trend"
        assert -1.0 <= out.score <= 1.0

    def test_range_expansion(self):
        out = range_expansion(_context(_make_bars(0.03)))
        assert out.name == "range_expansion"
        assert out.score > 0

    def test_persistence(self):
        out = volatility_persistence(_context(_make_bars(0.03)))
        assert out.name == "persistence"
        assert out.score > 0

    def test_signal_handles_short_series(self):
        out = historical_volatility(_context(_make_bars(0.02, n=10)))
        assert out.score == 0.0
        assert out.available is False
        assert out.evidence

    def test_all_signals_unavailable_on_tiny_series(self):
        ctx = _context(_make_bars(0.02, n=5))
        for name in ("historical_volatility", "volatility_trend", "range_expansion", "persistence"):
            out = build_default_signal_registry().get(name)(ctx)
            assert out.available is False
            assert out.score == 0.0

    def test_evidence_texts(self):
        from backend.analytics.volatility.evidence import Evidence, evidence_texts

        items = [Evidence("a", "one"), Evidence("b", "two")]
        assert evidence_texts(items) == ("one", "two")


class TestSignalRegistry:
    def test_default_registry_has_four(self):
        reg = build_default_signal_registry()
        assert len(reg._signals) == 4
        assert set(reg.names()) == {
            "historical_volatility",
            "volatility_trend",
            "range_expansion",
            "persistence",
        }

    def test_registry_get(self):
        reg = build_default_signal_registry()
        assert callable(reg.get("historical_volatility"))

    def test_registry_unknown_raises(self):
        reg = build_default_signal_registry()
        with pytest.raises(SignalError):
            reg.get("does_not_exist")

    def test_registry_callable(self):
        reg = build_default_signal_registry()
        out = reg.get("historical_volatility")(_context(_make_bars(0.02)))
        assert isinstance(out, SignalOutput)


class TestEvaluators:
    def test_weighted_evaluator_full(self):
        bars = _make_bars(0.022)
        reg = build_default_signal_registry()
        ctx = _context(bars)
        outputs = [reg.get(name)(ctx) for name in reg.names()]
        result = WeightedEvaluator().evaluate(outputs, VolatilityConfig())
        assert isinstance(result, EvaluatorResult)
        assert result.available_count == result.total_count == 4
        assert result.combined_score is not None

    def test_weighted_evaluator_partial(self):
        bars = _make_bars(0.022, n=25)
        reg = build_default_signal_registry()
        ctx = _context(bars)
        outputs = [reg.get(name)(ctx) for name in reg.names()]
        result = WeightedEvaluator().evaluate(outputs, VolatilityConfig())
        assert result.available_count < result.total_count
        assert result.combined_score is not None


class TestScoring:
    def test_score_very_high(self):
        res = EvaluatorResult(
            combined_score=0.8,
            agreement=1.0,
            available_count=4,
            total_count=4,
            evidence=(),
            conflict=False,
        )
        scoring = VolatilityScorer.score(res, 1.0)
        assert scoring.state == VolatilityState.VERY_HIGH
        assert scoring.confidence > 0

    def test_score_low(self):
        res = EvaluatorResult(
            combined_score=-0.8,
            agreement=1.0,
            available_count=4,
            total_count=4,
            evidence=(),
            conflict=False,
        )
        scoring = VolatilityScorer.score(res, 1.0)
        assert scoring.state == VolatilityState.VERY_LOW

    def test_score_conflict_downgrade(self):
        res = EvaluatorResult(
            combined_score=0.4,
            agreement=0.5,
            available_count=4,
            total_count=4,
            evidence=(),
            conflict=True,
        )
        scoring = VolatilityScorer.score(res, 1.0)
        assert scoring.state != VolatilityState.VERY_HIGH
        assert scoring.state.value != "very high"

    def test_score_conflict_downgrade_low(self):
        res = EvaluatorResult(
            combined_score=-0.4,
            agreement=0.5,
            available_count=4,
            total_count=4,
            evidence=(),
            conflict=True,
        )
        scoring = VolatilityScorer.score(res, 1.0)
        assert scoring.state == VolatilityState.NORMAL

    def test_score_zero_completeness(self):
        res = EvaluatorResult(
            combined_score=0.0,
            agreement=0.0,
            available_count=0,
            total_count=4,
            evidence=(),
            conflict=False,
        )
        scoring = VolatilityScorer.score(res, 0.0)
        assert scoring.state == VolatilityState.NORMAL
        assert scoring.confidence == 0.0


class TestExceptions:
    def test_exception_hierarchy(self):
        assert issubclass(InsufficientDataError, VolatilityError)
        assert issubclass(SignalError, VolatilityError)


class TestDefensiveBranches:
    def test_stdev_empty(self):
        assert _stdev([]) == 0.0

    def test_volatility_trend_flat_earlier(self):
        bars = [
            MarketBar(
                trade_date=date(2024, 1, 1) + timedelta(days=i),
                open=100.0,
                high=100.0,
                low=100.0,
                close=100.0,
                volume=1000,
            )
            for i in range(50)
        ] + [
            MarketBar(
                trade_date=date(2024, 1, 1) + timedelta(days=50 + i),
                open=100.0 + i,
                high=101.0 + i,
                low=99.0 + i,
                close=100.0 + i,
                volume=1000,
            )
            for i in range(10)
        ]
        out = volatility_trend(_context(bars))
        assert out.available is True
        assert out.score >= 0.0

    def test_range_expansion_zero_prices(self):
        bars = [
            MarketBar(
                trade_date=date(2024, 1, 1) + timedelta(days=i),
                open=0.0,
                high=1.0,
                low=-1.0,
                close=0.0,
                volume=1000,
            )
            for i in range(35)
        ]
        out = range_expansion(_context(bars))
        assert out.available is False
        assert out.score == 0.0

    def test_evaluator_zero_weights(self):
        bars = _make_bars(0.022, n=45)
        reg = build_default_signal_registry()
        ctx = _context(bars)
        outputs = [reg.get(name)(ctx) for name in reg.names()]
        cfg = VolatilityConfig(
            weight_hv=0.0,
            weight_vol_trend=0.0,
            weight_range_expansion=0.0,
            weight_persistence=0.0,
        )
        result = WeightedEvaluator().evaluate(outputs, cfg)
        assert result.combined_score == 0.0
        assert result.available_count == 4
