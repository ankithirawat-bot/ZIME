"""
Ascending Triangle Pattern Detector.

Detects horizontal resistance with rising lows.
"""

from __future__ import annotations

from backend.patterns.base import PatternDetector
from backend.patterns.models import PatternResult, PatternSnapshot, PatternType


class AscendingTriangleDetector(PatternDetector):
    """Detects Ascending Triangle patterns."""

    pattern_type = PatternType.ASCENDING_TRIANGLE

    def detect(self, snapshot: PatternSnapshot) -> PatternResult:
        """Detect ascending triangle.

        Criteria:
        - Horizontal resistance (multiple touches)
        - Higher lows forming
        - Decreasing volatility toward apex
        """
        reasons: list[str] = []
        warnings: list[str] = []

        resistance_score = self._score_resistance(snapshot, reasons, warnings)
        lows_score = self._score_higher_lows(snapshot, reasons, warnings)
        volatility_score = self._score_convergence(snapshot, reasons, warnings)

        score = resistance_score + lows_score + volatility_score
        score = max(0.0, min(100.0, score))

        confidence = 50.0
        if resistance_score >= 30:
            confidence += 15
        if lows_score >= 25:
            confidence += 15
        confidence -= len(warnings) * 5.0
        confidence = max(0.0, min(100.0, confidence))

        return PatternResult(
            pattern_name=PatternType.ASCENDING_TRIANGLE,
            score=score,
            confidence=confidence,
            pivot_price=snapshot.pivot_price,
            reasons=reasons,
            warnings=warnings,
        )

    def _score_resistance(
        self,
        snap: PatternSnapshot,
        reasons: list[str],
        warnings: list[str],
    ) -> float:
        """Score horizontal resistance (0-40)."""
        if not snap.highs or len(snap.highs) < 3:
            warnings.append("Insufficient data for resistance")
            return 0

        highs = snap.highs
        max_h = max(highs)
        touches = sum(1 for h in highs if abs(h - max_h) / max_h < 0.02)

        if touches >= 3:
            reasons.append("Clear horizontal resistance")
            return 40
        elif touches >= 2:
            reasons.append("Resistance forming")
            return 25
        else:
            warnings.append("No clear resistance")
            return 5

    def _score_higher_lows(
        self,
        snap: PatternSnapshot,
        reasons: list[str],
        warnings: list[str],
    ) -> float:
        """Score higher lows pattern (0-35)."""
        if not snap.lows or len(snap.lows) < 3:
            warnings.append("Insufficient data for lows")
            return 0

        lows = snap.lows
        n = len(lows)
        first_half = lows[:n // 2]
        second_half = lows[n // 2:]

        avg_first = sum(first_half) / len(first_half)
        avg_second = sum(second_half) / len(second_half)

        if avg_second > avg_first:
            reasons.append("Higher lows confirmed")
            return 35
        elif avg_second >= avg_first:
            reasons.append("Lows stabilizing")
            return 20
        else:
            warnings.append("Lower lows detected")
            return 0

    def _score_convergence(
        self,
        snap: PatternSnapshot,
        reasons: list[str],
        warnings: list[str],
    ) -> float:
        """Score decreasing volatility toward apex (0-25)."""
        if snap.volatility is None:
            return 0

        if snap.volatility < 15:
            reasons.append("Decreasing volatility toward apex")
            return 25
        elif snap.volatility < 25:
            return 15
        else:
            warnings.append("High volatility")
            return 5
