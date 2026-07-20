"""
Flat Base Detector — Detailed Verification Suite.
"""

from __future__ import annotations

import pytest

from backend.patterns.detectors.flat_base import FlatBaseDetector
from backend.patterns.models import PatternSnapshot, PatternType


@pytest.fixture
def detector() -> FlatBaseDetector:
    return FlatBaseDetector()


def snap(**kwargs) -> PatternSnapshot:
    defaults = dict(
        price=100.0,
        volume=1_000_000.0,
        highs=[100, 101, 100, 101, 100],
        lows=[98, 99, 98, 99, 98],
        closes=[99, 100, 99, 100, 99],
        pivot_price=103.0,
        high_52w=105.0,
        volatility=10.0,
        atr=2.0,
    )
    defaults.update(kwargs)
    return PatternSnapshot(**defaults)


class TestFlatBaseDetection:
    def test_returns_correct_type(self, detector: FlatBaseDetector) -> None:
        r = detector.detect(snap())
        assert r.pattern_name == PatternType.FLAT_BASE

    def test_tight_range(self, detector: FlatBaseDetector) -> None:
        r = detector.detect(snap(
            highs=[100, 101, 100, 101, 100],
            lows=[99, 100, 99, 100, 99],
        ))
        assert any("tight" in x.lower() for x in r.reasons)

    def test_near_high(self, detector: FlatBaseDetector) -> None:
        r = detector.detect(snap(high_52w=102))
        assert any("near" in x.lower() for x in r.reasons)

    def test_low_volatility(self, detector: FlatBaseDetector) -> None:
        r = detector.detect(snap(volatility=8))
        assert any("low volatility" in x.lower() for x in r.reasons)

    def test_wide_range_penalty(self, detector: FlatBaseDetector) -> None:
        r = detector.detect(snap(
            highs=[120, 130, 140],
            lows=[80, 70, 60],
        ))
        assert any("wide" in w.lower() for w in r.warnings)

    def test_far_from_high_penalty(self, detector: FlatBaseDetector) -> None:
        r = detector.detect(snap(high_52w=200))
        assert any("far" in w.lower() for w in r.warnings)

    def test_high_volatility_penalty(self, detector: FlatBaseDetector) -> None:
        r = detector.detect(snap(volatility=35))
        assert any("volatility" in w.lower() for w in r.warnings)

    def test_missing_data(self, detector: FlatBaseDetector) -> None:
        r = detector.detect(snap(highs=[], lows=[], high_52w=None, volatility=None))
        assert r.score == 0
        assert len(r.warnings) > 0
