"""
VCP Detector — Detailed Verification Suite.
"""

from __future__ import annotations

import pytest

from backend.patterns.detectors.vcp import VCPDetector
from backend.patterns.models import PatternSnapshot, PatternType


@pytest.fixture
def detector() -> VCPDetector:
    return VCPDetector()


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


class TestVCPDetection:
    def test_returns_correct_type(self, detector: VCPDetector) -> None:
        r = detector.detect(snap())
        assert r.pattern_name == PatternType.VCP

    def test_score_bounded(self, detector: VCPDetector) -> None:
        r = detector.detect(snap())
        assert 0 <= r.score <= 100

    def test_confidence_bounded(self, detector: VCPDetector) -> None:
        r = detector.detect(snap())
        assert 0 <= r.confidence <= 100


class TestContractionScoring:
    def test_strong_contraction(self, detector: VCPDetector) -> None:
        r = detector.detect(snap(contraction_count=5, volatility=10))
        assert any("strong" in x.lower() for x in r.reasons)

    def test_moderate_contraction(self, detector: VCPDetector) -> None:
        r = detector.detect(snap(contraction_count=2, volatility=15))
        assert any("moderate" in x.lower() for x in r.reasons)

    def test_immature_pattern(self, detector: VCPDetector) -> None:
        r = detector.detect(snap(contraction_count=1, volatility=20))
        assert any("immature" in w.lower() for w in r.warnings)

    def test_high_volatility_penalty(self, detector: VCPDetector) -> None:
        r = detector.detect(snap(contraction_count=3, volatility=35))
        assert any("volatility" in w.lower() for w in r.warnings)

    def test_missing_contraction_data(self, detector: VCPDetector) -> None:
        r = detector.detect(snap(contraction_count=None, volatility=None))
        assert any("missing" in w.lower() for w in r.warnings)


class TestVolumeScoring:
    def test_dry_volume(self, detector: VCPDetector) -> None:
        r = detector.detect(snap(volume_dryup=0.3))
        assert any("dried" in x.lower() for x in r.reasons)

    def test_declining_volume(self, detector: VCPDetector) -> None:
        r = detector.detect(snap(volume_dryup=0.65))
        assert any("declining" in x.lower() for x in r.reasons)

    def test_weak_volume(self, detector: VCPDetector) -> None:
        r = detector.detect(snap(volume_dryup=0.9))
        assert any("weak" in w.lower() for w in r.warnings)

    def test_missing_volume_data(self, detector: VCPDetector) -> None:
        r = detector.detect(snap(volume_dryup=None))
        assert any("missing" in w.lower() for w in r.warnings)


class TestBreakoutScoring:
    def test_near_pivot(self, detector: VCPDetector) -> None:
        r = detector.detect(snap(pivot_price=101, price=100))
        assert any("near pivot" in x.lower() for x in r.reasons)

    def test_close_to_pivot(self, detector: VCPDetector) -> None:
        r = detector.detect(snap(pivot_price=104, price=100))
        assert any("close" in x.lower() for x in r.reasons)

    def test_far_from_pivot(self, detector: VCPDetector) -> None:
        r = detector.detect(snap(pivot_price=120, price=100))
        assert any("far" in w.lower() for w in r.warnings)

    def test_missing_pivot(self, detector: VCPDetector) -> None:
        r = detector.detect(snap(pivot_price=None))
        assert any("missing" in w.lower() for w in r.warnings)


class TestTrendAndRS:
    def test_strong_trend(self, detector: VCPDetector) -> None:
        r = detector.detect(snap(trend_quality=80))
        assert any("trend" in x.lower() for x in r.reasons)

    def test_weak_trend(self, detector: VCPDetector) -> None:
        r = detector.detect(snap(trend_quality=30))
        assert any("poor" in w.lower() for w in r.warnings)

    def test_strong_rs(self, detector: VCPDetector) -> None:
        r = detector.detect(snap(relative_strength=80))
        assert any("relative strength" in x.lower() for x in r.reasons)


class TestBreakoutStop:
    def test_has_breakout_stop(self, detector: VCPDetector) -> None:
        r = detector.detect(snap(atr=2.0))
        assert r.breakout_price is not None
        assert r.stop_price is not None
        assert r.breakout_price > r.stop_price
