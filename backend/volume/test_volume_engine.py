"""
Sprint 17: Volume Intelligence Engine — pytest Verification Suite.

All tests use mock VolumeSnapshot objects. No internet, no yfinance.
"""

from __future__ import annotations

import pytest

from backend.volume.models import VolumeQuality, VolumeResult, VolumeSnapshot
from backend.volume.volume_engine import VolumeEngine


@pytest.fixture
def engine() -> VolumeEngine:
    return VolumeEngine()


def snap(**kwargs) -> VolumeSnapshot:
    defaults = dict(
        price=100.0,
        volume=1_500_000.0,
        avg_volume_20=1_000_000.0,
        avg_volume_50=1_100_000.0,
        breakout_volume=2_000_000.0,
        consolidation_volume=600_000.0,
        rvol=1.5,
        accumulation_days=4,
        distribution_days=1,
        close_position_percent=75.0,
        trend_quality=75.0,
        atr=2.0,
    )
    defaults.update(kwargs)
    return VolumeSnapshot(**defaults)


# =========================================================
# Models
# =========================================================
class TestModels:
    def test_volume_quality_enum(self) -> None:
        assert VolumeQuality.EXCEPTIONAL.value == "Exceptional"
        assert VolumeQuality.STRONG.value == "Strong"
        assert VolumeQuality.HEALTHY.value == "Healthy"
        assert VolumeQuality.WEAK.value == "Weak"
        assert VolumeQuality.POOR.value == "Poor"

    def test_snapshot_defaults(self) -> None:
        s = VolumeSnapshot(price=50)
        assert s.price == 50
        assert s.volume == 0.0
        assert s.rvol is None

    def test_result_fields(self) -> None:
        r = VolumeResult(
            overall_score=80, rvol_score=16, breakout_score=16,
            dryup_score=10, accumulation_score=16, distribution_score=5,
            institutional_score=8, volume_quality=VolumeQuality.STRONG,
            confidence=85, reasons=["test"], warnings=[],
        )
        assert r.overall_score == 80
        assert r.volume_quality == VolumeQuality.STRONG


# =========================================================
# Strong Breakout
# =========================================================
class TestStrongBreakout:
    def test_strong_breakout(self, engine: VolumeEngine) -> None:
        r = engine.evaluate(snap())
        assert r.overall_score >= 55
        assert r.volume_quality in (
            VolumeQuality.EXCEPTIONAL,
            VolumeQuality.STRONG,
            VolumeQuality.HEALTHY,
        )

    def test_breakout_volume_high(self, engine: VolumeEngine) -> None:
        r = engine.evaluate(snap(
            breakout_volume=3_000_000,
            avg_volume_20=1_000_000,
        ))
        assert r.breakout_score >= 10
        assert any("breakout volume" in x.lower() for x in r.reasons)

    def test_close_near_highs(self, engine: VolumeEngine) -> None:
        r = engine.evaluate(snap(close_position_percent=85))
        assert any("close near highs" in x.lower() for x in r.reasons)


# =========================================================
# Failed Breakout
# =========================================================
class TestFailedBreakout:
    def test_weak_breakout(self, engine: VolumeEngine) -> None:
        r = engine.evaluate(snap(
            breakout_volume=800_000,
            avg_volume_20=1_000_000,
            close_position_percent=30,
            trend_quality=30,
        ))
        assert r.breakout_score < 10
        assert any("weak" in w.lower() or "lacks" in w.lower() for w in r.warnings)


# =========================================================
# RVOL
# =========================================================
class TestRVOL:
    def test_high_rvol(self, engine: VolumeEngine) -> None:
        r = engine.evaluate(snap(rvol=2.5))
        assert r.rvol_score == 20
        assert any("strong" in x.lower() for x in r.reasons)

    def test_elevated_rvol(self, engine: VolumeEngine) -> None:
        r = engine.evaluate(snap(rvol=1.7))
        assert r.rvol_score == 16

    def test_above_rvol(self, engine: VolumeEngine) -> None:
        r = engine.evaluate(snap(rvol=1.3))
        assert r.rvol_score == 12

    def test_normal_rvol(self, engine: VolumeEngine) -> None:
        r = engine.evaluate(snap(rvol=1.0))
        assert r.rvol_score == 8

    def test_low_rvol(self, engine: VolumeEngine) -> None:
        r = engine.evaluate(snap(rvol=0.5))
        assert r.rvol_score == 4
        assert any("below-average" in x.lower() for x in r.reasons)

    def test_missing_rvol_estimated(self, engine: VolumeEngine) -> None:
        r = engine.evaluate(snap(
            rvol=None, volume=2_000_000, avg_volume_20=1_000_000,
        ))
        assert r.rvol_score == 20

    def test_missing_rvol_no_data(self, engine: VolumeEngine) -> None:
        r = engine.evaluate(snap(
            rvol=None, volume=0, avg_volume_20=None,
        ))
        assert r.rvol_score == 0
        assert any("missing" in w.lower() for w in r.warnings)


# =========================================================
# Accumulation
# =========================================================
class TestAccumulation:
    def test_strong_accumulation(self, engine: VolumeEngine) -> None:
        r = engine.evaluate(snap(
            accumulation_days=6, close_position_percent=80,
            volume=1_500_000, avg_volume_20=1_000_000,
        ))
        assert r.accumulation_score >= 12
        assert any("accumulation" in x.lower() for x in r.reasons)

    def test_moderate_accumulation(self, engine: VolumeEngine) -> None:
        r = engine.evaluate(snap(accumulation_days=3))
        assert r.accumulation_score >= 4

    def test_no_accumulation(self, engine: VolumeEngine) -> None:
        r = engine.evaluate(snap(accumulation_days=0))
        assert any("no accumulation" in w.lower() for w in r.warnings)

    def test_missing_accumulation(self, engine: VolumeEngine) -> None:
        r = engine.evaluate(snap(accumulation_days=None))
        assert r.accumulation_score == 0


# =========================================================
# Distribution
# =========================================================
class TestDistribution:
    def test_heavy_distribution(self, engine: VolumeEngine) -> None:
        r = engine.evaluate(snap(distribution_days=5))
        assert r.distribution_score == 15
        assert any("distribution" in x.lower() for x in r.reasons)

    def test_moderate_distribution(self, engine: VolumeEngine) -> None:
        r = engine.evaluate(snap(distribution_days=3))
        assert r.distribution_score == 10

    def test_light_distribution(self, engine: VolumeEngine) -> None:
        r = engine.evaluate(snap(distribution_days=1))
        assert r.distribution_score == 5

    def test_no_distribution(self, engine: VolumeEngine) -> None:
        r = engine.evaluate(snap(distribution_days=0))
        assert r.distribution_score == 0

    def test_missing_distribution(self, engine: VolumeEngine) -> None:
        r = engine.evaluate(snap(distribution_days=None))
        assert r.distribution_score == 0


# =========================================================
# Volume Dry-up
# =========================================================
class TestDryup:
    def test_strong_dryup(self, engine: VolumeEngine) -> None:
        r = engine.evaluate(snap(
            consolidation_volume=400_000, avg_volume_20=1_000_000,
        ))
        assert r.dryup_score == 15
        assert any("contracted" in x.lower() for x in r.reasons)

    def test_moderate_dryup(self, engine: VolumeEngine) -> None:
        r = engine.evaluate(snap(
            consolidation_volume=600_000, avg_volume_20=1_000_000,
        ))
        assert r.dryup_score == 10

    def test_weak_dryup(self, engine: VolumeEngine) -> None:
        r = engine.evaluate(snap(
            consolidation_volume=850_000, avg_volume_20=1_000_000,
        ))
        assert r.dryup_score == 5

    def test_no_dryup(self, engine: VolumeEngine) -> None:
        r = engine.evaluate(snap(
            consolidation_volume=1_000_000, avg_volume_20=1_000_000,
        ))
        assert r.dryup_score == 0

    def test_missing_dryup_data(self, engine: VolumeEngine) -> None:
        r = engine.evaluate(snap(
            consolidation_volume=None, avg_volume_20=None,
        ))
        assert r.dryup_score == 0


# =========================================================
# Institutional Footprint
# =========================================================
class TestInstitutional:
    def test_strong_institutional(self, engine: VolumeEngine) -> None:
        r = engine.evaluate(snap(
            rvol=2.5, breakout_volume=3_000_000,
            avg_volume_20=1_000_000, consolidation_volume=400_000,
            accumulation_days=6, distribution_days=0,
            close_position_percent=80, trend_quality=80,
        ))
        assert r.institutional_score >= 8

    def test_weak_institutional(self, engine: VolumeEngine) -> None:
        r = engine.evaluate(snap(
            rvol=0.5, breakout_volume=500_000,
            avg_volume_20=1_000_000, consolidation_volume=900_000,
            accumulation_days=0, distribution_days=4,
            close_position_percent=30, trend_quality=30,
        ))
        assert r.institutional_score <= 4


# =========================================================
# Quality Classification
# =========================================================
class TestQuality:
    def test_strong_quality(self, engine: VolumeEngine) -> None:
        r = engine.evaluate(snap(
            rvol=3.0, breakout_volume=4_000_000,
            avg_volume_20=1_000_000, consolidation_volume=300_000,
            accumulation_days=8, distribution_days=0,
            close_position_percent=90, trend_quality=90,
        ))
        assert r.volume_quality in (VolumeQuality.EXCEPTIONAL, VolumeQuality.STRONG)

    def test_poor(self, engine: VolumeEngine) -> None:
        r = engine.evaluate(snap(
            rvol=0.3, breakout_volume=200_000,
            avg_volume_20=1_000_000, consolidation_volume=1_200_000,
            accumulation_days=0, distribution_days=5,
            close_position_percent=20, trend_quality=20,
        ))
        assert r.volume_quality == VolumeQuality.POOR


# =========================================================
# Confidence
# =========================================================
class TestConfidence:
    def test_high_confidence(self, engine: VolumeEngine) -> None:
        r = engine.evaluate(snap(
            rvol=2.5, breakout_volume=3_000_000,
            avg_volume_20=1_000_000,
            accumulation_days=6, distribution_days=0,
        ))
        assert r.confidence >= 70

    def test_low_confidence(self, engine: VolumeEngine) -> None:
        r = engine.evaluate(snap(
            rvol=0.5, breakout_volume=None,
            avg_volume_20=None, consolidation_volume=None,
            accumulation_days=0, distribution_days=5,
            close_position_percent=20, trend_quality=20,
        ))
        assert r.confidence < 50

    def test_confidence_range(self, engine: VolumeEngine) -> None:
        r = engine.evaluate(snap())
        assert 0 <= r.confidence <= 100


# =========================================================
# Reasons & Warnings
# =========================================================
class TestReasonsWarnings:
    def test_reasons_are_strings(self, engine: VolumeEngine) -> None:
        r = engine.evaluate(snap())
        assert isinstance(r.reasons, list)
        assert len(r.reasons) > 0
        assert all(isinstance(x, str) for x in r.reasons)

    def test_warnings_are_strings(self, engine: VolumeEngine) -> None:
        r = engine.evaluate(snap())
        assert isinstance(r.warnings, list)
        assert all(isinstance(x, str) for x in r.warnings)


# =========================================================
# Score Components
# =========================================================
class TestScoreComponents:
    def test_component_bounds(self, engine: VolumeEngine) -> None:
        r = engine.evaluate(snap())
        assert 0 <= r.rvol_score <= 20
        assert 0 <= r.breakout_score <= 20
        assert 0 <= r.dryup_score <= 15
        assert 0 <= r.accumulation_score <= 20
        assert 0 <= r.distribution_score <= 15
        assert 0 <= r.institutional_score <= 10

    def test_overall_bounded(self, engine: VolumeEngine) -> None:
        r = engine.evaluate(snap())
        assert 0 <= r.overall_score <= 100


# =========================================================
# Missing Data
# =========================================================
class TestMissingData:
    def test_all_none(self, engine: VolumeEngine) -> None:
        s = VolumeSnapshot(price=100)
        r = engine.evaluate(s)
        assert r.overall_score >= 0
        assert len(r.warnings) > 0
        assert r.confidence >= 0

    def test_partial_none(self, engine: VolumeEngine) -> None:
        s = VolumeSnapshot(price=100, volume=1_500_000, avg_volume_20=1_000_000)
        r = engine.evaluate(s)
        assert r.rvol_score == 16


# =========================================================
# Deterministic
# =========================================================
class TestDeterministic:
    def test_same_input_same_output(self, engine: VolumeEngine) -> None:
        data = snap()
        r1 = engine.evaluate(data)
        r2 = engine.evaluate(data)
        assert r1.overall_score == r2.overall_score
        assert r1.volume_quality == r2.volume_quality
        assert r1.reasons == r2.reasons
        assert r1.warnings == r2.warnings


# =========================================================
# Regression
# =========================================================
class TestRegression:
    def test_trend_engine_still_works(self) -> None:
        from backend.trend.models import TrendSnapshot
        from backend.trend.trend_engine import TrendQualityEngine
        engine = TrendQualityEngine()
        r = engine.evaluate(TrendSnapshot(current_price=2500))
        assert r.overall_score >= 0

    def test_pattern_engine_still_works(self) -> None:
        from backend.patterns.engine import PatternEngine
        from backend.patterns.models import PatternSnapshot
        engine = PatternEngine()
        r = engine.evaluate(PatternSnapshot(price=100))
        assert r.score >= 0
