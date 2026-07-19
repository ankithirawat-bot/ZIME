"""
Sprint 15: Trend Quality Engine — pytest Verification Suite.

All tests use mock TrendSnapshot objects. No internet, no yfinance.
"""

from __future__ import annotations

import pytest

from backend.trend.models import TrendQuality, TrendResult, TrendSnapshot, TrendStage
from backend.trend.trend_engine import TrendQualityEngine


@pytest.fixture
def engine() -> TrendQualityEngine:
    return TrendQualityEngine()


def snap(**kwargs) -> TrendSnapshot:
    defaults = dict(
        current_price=2500.0,
        ema20=2480.0, ema50=2400.0, sma150=2300.0, sma200=2200.0,
        high_52w=2600.0, low_52w=1800.0,
        slope_ema20=4.0, slope_ema50=3.0, slope_sma150=2.0, slope_sma200=1.0,
        higher_high_count=3, higher_low_count=3,
        trend_age=150, history_length=250,
    )
    if "price" in kwargs:
        kwargs["current_price"] = kwargs.pop("price")
    defaults.update(kwargs)
    return TrendSnapshot(**defaults)


# =========================================================
# Models
# =========================================================
class TestModels:
    def test_trend_quality_enum(self) -> None:
        assert TrendQuality.EXCEPTIONAL.value == "Exceptional"
        assert TrendQuality.STRONG.value == "Strong"
        assert TrendQuality.HEALTHY.value == "Healthy"
        assert TrendQuality.WEAK.value == "Weak"
        assert TrendQuality.BROKEN.value == "Broken"

    def test_trend_stage_enum(self) -> None:
        assert TrendStage.EARLY.value == "Early"
        assert TrendStage.ESTABLISHED.value == "Established"
        assert TrendStage.EXTENDED.value == "Extended"
        assert TrendStage.LATE.value == "Late"
        assert TrendStage.BROKEN.value == "Broken"

    def test_snapshot_defaults(self) -> None:
        s = TrendSnapshot(current_price=100)
        assert s.current_price == 100
        assert s.ema20 is None
        assert s.slope_ema20 is None
        assert s.higher_high_count is None

    def test_result_fields(self) -> None:
        r = TrendResult(
            overall_score=90, alignment_score=20, price_position_score=15,
            slope_score=20, structure_score=20, persistence_score=10,
            high_score=15, trend_quality=TrendQuality.EXCEPTIONAL,
            trend_stage=TrendStage.ESTABLISHED, confidence=100,
            reasons=["test"], warnings=[],
        )
        assert r.overall_score == 90
        assert r.trend_quality == TrendQuality.EXCEPTIONAL


# =========================================================
# Perfect / Exceptional Trend
# =========================================================
class TestExceptional:
    def test_perfect_trend(self, engine: TrendQualityEngine) -> None:
        r = engine.evaluate(snap())
        assert r.overall_score >= 90
        assert r.trend_quality == TrendQuality.EXCEPTIONAL

    def test_alignment_full(self, engine: TrendQualityEngine) -> None:
        r = engine.evaluate(snap(ema20=2500, ema50=2400, sma150=2300, sma200=2200))
        assert r.alignment_score == 20
        assert any("perfectly aligned" in x.lower() for x in r.reasons)


# =========================================================
# Strong Trend
# =========================================================
class TestStrong:
    def test_strong_trend(self, engine: TrendQualityEngine) -> None:
        r = engine.evaluate(snap(
            higher_high_count=1, higher_low_count=1, trend_age=40,
        ))
        assert 75 <= r.overall_score < 90
        assert r.trend_quality == TrendQuality.STRONG


# =========================================================
# Healthy Trend
# =========================================================
class TestHealthy:
    def test_healthy_trend(self, engine: TrendQualityEngine) -> None:
        r = engine.evaluate(snap(
            ema20=2480, ema50=2400, sma150=2300, sma200=2500,
            slope_ema20=4, slope_ema50=3, slope_sma150=2, slope_sma200=-1,
            higher_high_count=1, higher_low_count=1, trend_age=40,
        ))
        assert 55 <= r.overall_score < 75
        assert r.trend_quality == TrendQuality.HEALTHY


# =========================================================
# Weak Trend
# =========================================================
class TestWeak:
    def test_weak_trend(self, engine: TrendQualityEngine) -> None:
        r = engine.evaluate(snap(
            price=2500, ema20=2480, ema50=2600, sma150=2700, sma200=2800,
            slope_ema20=-2, slope_ema50=-1, slope_sma150=1, slope_sma200=-3,
            higher_high_count=1, higher_low_count=4, trend_age=10,
            high_52w=3000,
        ))
        assert 35 <= r.overall_score < 55
        assert r.trend_quality == TrendQuality.WEAK


# =========================================================
# Broken Trend
# =========================================================
class TestBroken:
    def test_broken_trend(self, engine: TrendQualityEngine) -> None:
        r = engine.evaluate(snap(
            price=2000, ema20=2500, ema50=2600, sma150=2700, sma200=2800,
            slope_ema20=-5, slope_ema50=-4, slope_sma150=-3, slope_sma200=-2,
            higher_high_count=0, higher_low_count=0, trend_age=0,
            high_52w=3500,
        ))
        assert r.overall_score < 35
        assert r.trend_quality == TrendQuality.BROKEN
        assert r.trend_stage == TrendStage.BROKEN


# =========================================================
# Alignment
# =========================================================
class TestAlignment:
    def test_broken_alignment(self, engine: TrendQualityEngine) -> None:
        r = engine.evaluate(snap(ema20=2200, ema50=2300, sma150=2400, sma200=2500))
        assert r.alignment_score == 0
        assert any("not aligned" in x.lower() for x in r.reasons)

    def test_partial_alignment(self, engine: TrendQualityEngine) -> None:
        r = engine.evaluate(snap(ema20=2500, ema50=2400, sma150=2300, sma200=2500))
        assert 0 < r.alignment_score < 20
        assert any("partially aligned" in x.lower() for x in r.reasons)

    def test_missing_averages(self, engine: TrendQualityEngine) -> None:
        s = TrendSnapshot(current_price=2500)
        r = engine.evaluate(s)
        assert r.alignment_score == 0
        assert any("missing averages" in w.lower() for w in r.warnings)


# =========================================================
# Slopes
# =========================================================
class TestSlopes:
    def test_all_rising(self, engine: TrendQualityEngine) -> None:
        r = engine.evaluate(snap(slope_ema20=5, slope_ema50=4, slope_sma150=3, slope_sma200=2))
        assert r.slope_score == 20
        assert any("rising" in x.lower() for x in r.reasons)

    def test_all_falling(self, engine: TrendQualityEngine) -> None:
        r = engine.evaluate(snap(slope_ema20=-5, slope_ema50=-4, slope_sma150=-3, slope_sma200=-2))
        assert r.slope_score == 0
        assert any("declining" in x.lower() for x in r.reasons)

    def test_missing_slopes(self, engine: TrendQualityEngine) -> None:
        s = TrendSnapshot(current_price=2500)
        r = engine.evaluate(s)
        assert r.slope_score == 0
        assert any("missing slopes" in w.lower() for w in r.warnings)


# =========================================================
# Structure
# =========================================================
class TestStructure:
    def test_strong_hh_hl(self, engine: TrendQualityEngine) -> None:
        r = engine.evaluate(snap(higher_high_count=5, higher_low_count=5))
        assert r.structure_score == 20
        assert any("higher-high" in x.lower() for x in r.reasons)
        assert any("higher-low" in x.lower() for x in r.reasons)

    def test_no_hh_hl(self, engine: TrendQualityEngine) -> None:
        r = engine.evaluate(snap(higher_high_count=0, higher_low_count=0))
        assert r.structure_score == 0
        assert any("no higher highs" in w.lower() for w in r.warnings)
        assert any("lower lows" in w.lower() for w in r.warnings)

    def test_missing_structure(self, engine: TrendQualityEngine) -> None:
        s = TrendSnapshot(current_price=2500)
        r = engine.evaluate(s)
        assert r.structure_score == 0
        assert any("missing structure" in w.lower() for w in r.warnings)


# =========================================================
# Persistence
# =========================================================
class TestPersistence:
    def test_mature_trend(self, engine: TrendQualityEngine) -> None:
        r = engine.evaluate(snap(trend_age=150))
        assert r.persistence_score == 10
        assert any("150 bars" in x for x in r.reasons)

    def test_young_trend(self, engine: TrendQualityEngine) -> None:
        r = engine.evaluate(snap(trend_age=5))
        assert r.persistence_score == 2

    def test_missing_age(self, engine: TrendQualityEngine) -> None:
        s = TrendSnapshot(current_price=2500)
        r = engine.evaluate(s)
        assert r.persistence_score == 0


# =========================================================
# High Proximity
# =========================================================
class TestHighProximity:
    def test_within_5pct(self, engine: TrendQualityEngine) -> None:
        r = engine.evaluate(snap(price=2500, high_52w=2600))
        assert r.high_score == 15

    def test_5_to_10pct(self, engine: TrendQualityEngine) -> None:
        r = engine.evaluate(snap(price=2400, high_52w=2600))
        assert r.high_score == 12

    def test_10_to_20pct(self, engine: TrendQualityEngine) -> None:
        r = engine.evaluate(snap(price=2200, high_52w=2600))
        assert r.high_score == 8

    def test_20_to_35pct(self, engine: TrendQualityEngine) -> None:
        r = engine.evaluate(snap(price=1800, high_52w=2600))
        assert r.high_score == 4

    def test_beyond_35pct(self, engine: TrendQualityEngine) -> None:
        r = engine.evaluate(snap(price=1500, high_52w=2600))
        assert r.high_score == 0

    def test_missing_high(self, engine: TrendQualityEngine) -> None:
        s = TrendSnapshot(current_price=2500, high_52w=None)
        r = engine.evaluate(s)
        assert r.high_score == 0


# =========================================================
# Price Extension
# =========================================================
class TestPriceExtension:
    def test_extended_price(self, engine: TrendQualityEngine) -> None:
        r = engine.evaluate(snap(price=3000, ema20=2400))
        assert any("extended" in w.lower() for w in r.warnings)

    def test_not_extended(self, engine: TrendQualityEngine) -> None:
        r = engine.evaluate(snap(price=2500, ema20=2400))
        assert not any("extended" in w.lower() for w in r.warnings)


# =========================================================
# Trend Stage
# =========================================================
class TestTrendStage:
    def test_early_stage(self, engine: TrendQualityEngine) -> None:
        r = engine.evaluate(snap(trend_age=10))
        assert r.trend_stage == TrendStage.EARLY

    def test_established_stage(self, engine: TrendQualityEngine) -> None:
        r = engine.evaluate(snap(trend_age=40))
        assert r.trend_stage == TrendStage.ESTABLISHED

    def test_extended_stage(self, engine: TrendQualityEngine) -> None:
        r = engine.evaluate(snap(trend_age=150, price=3000, ema20=2400))
        assert r.trend_stage == TrendStage.EXTENDED

    def test_late_stage(self, engine: TrendQualityEngine) -> None:
        r = engine.evaluate(snap(trend_age=150, price=2500, ema20=2480))
        assert r.trend_stage == TrendStage.LATE

    def test_broken_stage(self, engine: TrendQualityEngine) -> None:
        r = engine.evaluate(snap(
            price=2000, ema20=2500, ema50=2600, sma150=2700, sma200=2800,
            slope_ema20=-5, slope_ema50=-4, slope_sma150=-3, slope_sma200=-2,
            higher_high_count=0, higher_low_count=0, trend_age=0,
            high_52w=3500,
        ))
        assert r.trend_stage == TrendStage.BROKEN


# =========================================================
# Confidence
# =========================================================
class TestConfidence:
    def test_full_data_high_confidence(self, engine: TrendQualityEngine) -> None:
        r = engine.evaluate(snap(history_length=250))
        assert r.confidence >= 70

    def test_missing_data_reduces(self, engine: TrendQualityEngine) -> None:
        r = engine.evaluate(snap(
            history_length=50, ema20=None, ema50=None, sma150=None, sma200=None,
            slope_ema20=None, slope_ema50=None, slope_sma150=None, slope_sma200=None,
            higher_high_count=None, higher_low_count=None,
        ))
        assert r.confidence < 50

    def test_confidence_range(self, engine: TrendQualityEngine) -> None:
        r = engine.evaluate(snap())
        assert 0 <= r.confidence <= 100


# =========================================================
# Reasons
# =========================================================
class TestReasons:
    def test_reasons_are_strings(self, engine: TrendQualityEngine) -> None:
        r = engine.evaluate(snap())
        assert isinstance(r.reasons, list)
        assert len(r.reasons) > 0
        assert all(isinstance(x, str) for x in r.reasons)

    def test_reasons_deduplicated(self, engine: TrendQualityEngine) -> None:
        r = engine.evaluate(snap())
        assert len(r.reasons) == len(set(r.reasons))


# =========================================================
# Warnings
# =========================================================
class TestWarnings:
    def test_warnings_are_strings(self, engine: TrendQualityEngine) -> None:
        r = engine.evaluate(snap())
        assert isinstance(r.warnings, list)
        assert all(isinstance(x, str) for x in r.warnings)

    def test_falling_sma200_warning(self, engine: TrendQualityEngine) -> None:
        r = engine.evaluate(snap(slope_sma200=-5))
        assert any("falling sma200" in w.lower() for w in r.warnings)


# =========================================================
# Score Components
# =========================================================
class TestScoreComponents:
    def test_component_bounds(self, engine: TrendQualityEngine) -> None:
        r = engine.evaluate(snap())
        assert 0 <= r.alignment_score <= 20
        assert 0 <= r.price_position_score <= 15
        assert 0 <= r.slope_score <= 20
        assert 0 <= r.structure_score <= 20
        assert 0 <= r.persistence_score <= 10
        assert 0 <= r.high_score <= 15

    def test_sum_matches_overall(self, engine: TrendQualityEngine) -> None:
        r = engine.evaluate(snap())
        total = (
            r.alignment_score + r.price_position_score + r.slope_score
            + r.structure_score + r.persistence_score + r.high_score
        )
        assert abs(total - r.overall_score) < 0.01

    def test_overall_bounded(self, engine: TrendQualityEngine) -> None:
        r = engine.evaluate(snap())
        assert 0 <= r.overall_score <= 100


# =========================================================
# Missing Data (no crash)
# =========================================================
class TestMissingData:
    def test_all_none(self, engine: TrendQualityEngine) -> None:
        s = TrendSnapshot(current_price=100)
        r = engine.evaluate(s)
        assert r.overall_score == 0
        assert r.trend_quality == TrendQuality.BROKEN
        assert len(r.warnings) > 0
        assert r.confidence >= 0

    def test_partial_none(self, engine: TrendQualityEngine) -> None:
        s = TrendSnapshot(current_price=2500, ema20=2480, slope_ema20=3)
        r = engine.evaluate(s)
        assert r.overall_score >= 0
        assert len(r.warnings) > 0
