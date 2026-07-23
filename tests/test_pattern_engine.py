"""
Sprint 16: Pattern Recognition Engine — pytest Verification Suite.

All tests use mock PatternSnapshot objects. No internet, no yfinance.
"""

from __future__ import annotations

import pytest

from backend.patterns.base import PatternDetector
from backend.patterns.detectors.ascending_triangle import AscendingTriangleDetector
from backend.patterns.detectors.cup_handle import CupHandleDetector
from backend.patterns.detectors.flat_base import FlatBaseDetector
from backend.patterns.detectors.high_tight_flag import HighTightFlagDetector
from backend.patterns.detectors.vcp import VCPDetector
from backend.patterns.engine import PatternEngine
from backend.patterns.models import PatternResult, PatternSnapshot, PatternType


@pytest.fixture
def engine() -> PatternEngine:
    return PatternEngine()


def snap(**kwargs) -> PatternSnapshot:
    defaults = dict(
        price=100.0,
        volume=1_000_000.0,
        highs=[100, 102, 101, 103, 102],
        lows=[95, 96, 94, 95, 96],
        closes=[98, 99, 97, 100, 99],
        pivot_price=103.0,
        high_52w=110.0,
        volatility=12.0,
        atr=2.0,
        contraction_count=3,
        volume_dryup=0.4,
        breakout_volume_ratio=1.5,
        trend_quality=75.0,
        relative_strength=80.0,
    )
    defaults.update(kwargs)
    return PatternSnapshot(**defaults)


# =========================================================
# Models
# =========================================================
class TestModels:
    def test_pattern_type_enum(self) -> None:
        assert PatternType.UNKNOWN.value == "Unknown"
        assert PatternType.VCP.value == "VCP"
        assert PatternType.CUP_HANDLE.value == "CupHandle"
        assert PatternType.FLAT_BASE.value == "FlatBase"
        assert PatternType.ASCENDING_TRIANGLE.value == "AscendingTriangle"
        assert PatternType.HIGH_TIGHT_FLAG.value == "HighTightFlag"

    def test_snapshot_defaults(self) -> None:
        s = PatternSnapshot(price=50)
        assert s.price == 50
        assert s.volume == 0.0
        assert s.highs == []
        assert s.contraction_count is None

    def test_result_fields(self) -> None:
        r = PatternResult(
            pattern_name=PatternType.VCP,
            score=85,
            confidence=90,
            reasons=["test"],
            warnings=[],
        )
        assert r.pattern_name == PatternType.VCP
        assert r.score == 85
        assert r.risk_reward is None


# =========================================================
# Base Detector
# =========================================================
class TestBaseDetector:
    def test_abstract_cannot_instantiate(self) -> None:
        with pytest.raises(TypeError):
            PatternDetector()  # type: ignore

    def test_concrete_detector_has_pattern_type(self) -> None:
        d = VCPDetector()
        assert d.pattern_type == PatternType.VCP


# =========================================================
# VCP Detector
# =========================================================
class TestVCP:
    def test_strong_vcp(self, engine: PatternEngine) -> None:
        r = engine.evaluate(snap())
        assert r.pattern_name == PatternType.VCP
        assert r.score >= 70

    def test_vcp_contraction_scoring(self) -> None:
        d = VCPDetector()
        r = d.detect(snap(contraction_count=5, volatility=10))
        assert r.score >= 50
        assert any("contraction" in x.lower() for x in r.reasons)

    def test_vcp_weak_contraction(self) -> None:
        d = VCPDetector()
        r = d.detect(snap(
            contraction_count=1, volatility=35,
            volume_dryup=0.9, pivot_price=120,
            trend_quality=30, relative_strength=30,
        ))
        assert r.score < 50
        assert any("immature" in w.lower() for w in r.warnings)

    def test_vcp_volume_scoring(self) -> None:
        d = VCPDetector()
        r = d.detect(snap(volume_dryup=0.3))
        assert any("dried" in x.lower() for x in r.reasons)

    def test_vcp_near_pivot(self) -> None:
        d = VCPDetector()
        r = d.detect(snap(pivot_price=101, price=100))
        assert any("near pivot" in x.lower() for x in r.reasons)

    def test_vcp_missing_data(self) -> None:
        d = VCPDetector()
        r = d.detect(snap(
            contraction_count=None, volatility=None,
            volume_dryup=None, pivot_price=None,
            trend_quality=None, relative_strength=None,
        ))
        assert r.score == 0
        assert len(r.warnings) > 0

    def test_vcp_has_breakout_stop(self) -> None:
        d = VCPDetector()
        r = d.detect(snap(atr=2.0))
        assert r.breakout_price is not None
        assert r.stop_price is not None


# =========================================================
# Flat Base Detector
# =========================================================
class TestFlatBase:
    def test_tight_flat_base(self) -> None:
        d = FlatBaseDetector()
        r = d.detect(snap(
            highs=[100, 101, 100, 101, 100],
            lows=[98, 99, 98, 99, 98],
            high_52w=105,
            volatility=10,
        ))
        assert r.pattern_name == PatternType.FLAT_BASE
        assert r.score >= 50
        assert any("tight" in x.lower() for x in r.reasons)

    def test_wide_range_low_score(self) -> None:
        d = FlatBaseDetector()
        r = d.detect(snap(
            highs=[120, 125, 130],
            lows=[80, 75, 70],
            high_52w=130,
            volatility=30,
        ))
        assert r.score < 50

    def test_flat_base_missing_data(self) -> None:
        d = FlatBaseDetector()
        r = d.detect(snap(highs=[], lows=[], high_52w=None, volatility=None))
        assert r.score == 0


# =========================================================
# Ascending Triangle Detector
# =========================================================
class TestAscendingTriangle:
    def test_clear_triangle(self) -> None:
        d = AscendingTriangleDetector()
        r = d.detect(snap(
            highs=[100, 100, 100, 100],
            lows=[90, 92, 94, 95],
            volatility=10,
        ))
        assert r.pattern_name == PatternType.ASCENDING_TRIANGLE
        assert r.score >= 50

    def test_no_resistance(self) -> None:
        d = AscendingTriangleDetector()
        r = d.detect(snap(
            highs=[90, 95, 100, 105],
            lows=[85, 90, 95, 100],
            volatility=25,
        ))
        assert r.score < 50

    def test_triangle_missing_data(self) -> None:
        d = AscendingTriangleDetector()
        r = d.detect(snap(highs=[], lows=[], volatility=None))
        assert r.score == 0


# =========================================================
# Cup & Handle Detector
# =========================================================
class TestCupHandle:
    def test_good_cup(self) -> None:
        d = CupHandleDetector()
        r = d.detect(snap(
            closes=[100, 95, 90, 85, 88, 92, 98, 100],
            pivot_price=102,
            price=99,
            volume_dryup=0.4,
            atr=2.0,
        ))
        assert r.pattern_name == PatternType.CUP_HANDLE
        assert r.score >= 40

    def test_shallow_handle(self) -> None:
        d = CupHandleDetector()
        r = d.detect(snap(
            closes=[100, 95, 90, 85, 88, 92, 98, 100],
            pivot_price=102,
            price=100,
            volume_dryup=0.5,
        ))
        assert any("handle" in x.lower() for x in r.reasons)

    def test_cup_missing_data(self) -> None:
        d = CupHandleDetector()
        r = d.detect(snap(
            closes=[], pivot_price=None,
            volume_dryup=None, atr=None,
        ))
        assert r.score == 0


# =========================================================
# High Tight Flag Detector
# =========================================================
class TestHighTightFlag:
    def test_strong_flag(self) -> None:
        d = HighTightFlagDetector()
        r = d.detect(snap(
            closes=[60, 70, 80, 90, 100, 99, 100, 101],
            highs=[100, 101, 100, 101],
            lows=[98, 99, 98, 99],
            price=100,
        ))
        assert r.pattern_name == PatternType.HIGH_TIGHT_FLAG
        assert r.score >= 50

    def test_weak_advance(self) -> None:
        d = HighTightFlagDetector()
        r = d.detect(snap(
            closes=[95, 96, 97, 98, 100],
            highs=[100, 105, 110],
            lows=[90, 85, 80],
            price=100,
        ))
        assert r.score < 50

    def test_flag_missing_data(self) -> None:
        d = HighTightFlagDetector()
        r = d.detect(snap(closes=[], highs=[], lows=[]))
        assert r.score == 0


# =========================================================
# Engine
# =========================================================
class TestEngine:
    def test_selects_best_pattern(self, engine: PatternEngine) -> None:
        r = engine.evaluate(snap())
        assert r.pattern_name != PatternType.UNKNOWN
        assert r.score > 0

    def test_unknown_when_nothing(self, engine: PatternEngine) -> None:
        r = engine.evaluate(snap(
            highs=[], lows=[], closes=[],
            contraction_count=None, volatility=None,
            volume_dryup=None, pivot_price=None,
            trend_quality=None, relative_strength=None,
            high_52w=None, atr=None,
        ))
        assert r.pattern_name == PatternType.UNKNOWN
        assert r.score == 0

    def test_multiple_competing(self) -> None:
        data = snap(
            highs=[100, 101, 100, 101, 100],
            lows=[98, 99, 98, 99, 98],
            closes=[99, 100, 99, 100, 99],
            high_52w=105,
            volatility=10,
            pivot_price=101,
            price=100,
            contraction_count=4,
            volume_dryup=0.3,
            trend_quality=80,
            relative_strength=85,
        )
        engine = PatternEngine()
        r1 = engine.evaluate(data)
        # Run again to confirm deterministic
        r2 = engine.evaluate(data)
        assert r1.score == r2.score
        assert r1.pattern_name == r2.pattern_name

    def test_reasons_are_list(self, engine: PatternEngine) -> None:
        r = engine.evaluate(snap())
        assert isinstance(r.reasons, list)
        assert all(isinstance(x, str) for x in r.reasons)

    def test_warnings_are_list(self, engine: PatternEngine) -> None:
        r = engine.evaluate(snap())
        assert isinstance(r.warnings, list)
        assert all(isinstance(x, str) for x in r.warnings)

    def test_confidence_range(self, engine: PatternEngine) -> None:
        r = engine.evaluate(snap())
        assert 0 <= r.confidence <= 100

    def test_score_range(self, engine: PatternEngine) -> None:
        r = engine.evaluate(snap())
        assert 0 <= r.score <= 100

    def test_custom_detectors(self) -> None:
        engine = PatternEngine(detectors=[VCPDetector()])
        r = engine.evaluate(snap())
        assert r.pattern_name == PatternType.VCP


# =========================================================
# Regression: other engines unaffected
# =========================================================
class TestRegression:
    def test_trend_engine_still_works(self) -> None:
        from backend.trend.models import TrendSnapshot
        from backend.trend.trend_engine import TrendQualityEngine
        engine = TrendQualityEngine()
        r = engine.evaluate(TrendSnapshot(current_price=2500))
        assert r.overall_score >= 0

    def test_rs_engine_still_works(self) -> None:
        from backend.relative_strength.models import BenchmarkData, StockSnapshot
        from backend.relative_strength.rs_engine import analyze_relative_strength
        s = StockSnapshot(
            symbol="TEST",
            stock=BenchmarkData(name="S", returns_1y=25),
            market_benchmark=BenchmarkData(name="M", returns_1y=20),
        )
        r = analyze_relative_strength(s)
        assert r.overall_score >= 0
