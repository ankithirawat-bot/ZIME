"""
Flat Base Pattern Detector.

Detects tight price ranges near highs with low volatility.
"""

from __future__ import annotations

from backend.patterns.base import PatternDetector
from backend.patterns.models import PatternResult, PatternSnapshot, PatternType


class FlatBaseDetector(PatternDetector):
    """Detects Flat Base patterns."""

    pattern_type = PatternType.FLAT_BASE

    def detect(self, snapshot: PatternSnapshot) -> PatternResult:
        """Detect flat base pattern.

        Criteria:
        - Tight range (highs-lows < 15% of price)
        - Near 52-week highs
        - Low volatility
        """
        reasons: list[str] = []
        warnings: list[str] = []

        range_score = self._score_range(snapshot, reasons, warnings)
        proximity_score = self._score_proximity(snapshot, reasons, warnings)
        volatility_score = self._score_volatility(snapshot, reasons, warnings)

        score = range_score + proximity_score + volatility_score
        score = max(0.0, min(100.0, score))

        confidence = self._calc_confidence(reasons, warnings, range_score)

        return PatternResult(
            pattern_name=PatternType.FLAT_BASE,
            score=score,
            confidence=confidence,
            pivot_price=snapshot.pivot_price,
            reasons=reasons,
            warnings=warnings,
        )

    def _score_range(
        self,
        snap: PatternSnapshot,
        reasons: list[str],
        warnings: list[str],
    ) -> float:
        """Score tightness of price range (0-40)."""
        if not snap.highs or not snap.lows:
            warnings.append("Missing price range data")
            return 0

        high = max(snap.highs)
        low = min(snap.lows)
        if snap.price == 0:
            return 0

        range_pct = ((high - low) / snap.price) * 100

        if range_pct < 8:
            reasons.append("Tight price range")
            return 40
        elif range_pct < 15:
            reasons.append("Moderately tight range")
            return 25
        else:
            warnings.append("Wide price range")
            return 5

    def _score_proximity(
        self,
        snap: PatternSnapshot,
        reasons: list[str],
        warnings: list[str],
    ) -> float:
        """Score proximity to 52-week high (0-35)."""
        if snap.high_52w is None or snap.high_52w == 0:
            return 0

        distance = ((snap.high_52w - snap.price) / snap.high_52w) * 100

        if distance <= 5:
            reasons.append("Trading near 52-week high")
            return 35
        elif distance <= 10:
            reasons.append("Close to 52-week high")
            return 25
        elif distance <= 20:
            return 10
        else:
            warnings.append("Far from 52-week high")
            return 0

    def _score_volatility(
        self,
        snap: PatternSnapshot,
        reasons: list[str],
        warnings: list[str],
    ) -> float:
        """Score low volatility (0-25)."""
        if snap.volatility is None:
            return 0

        if snap.volatility < 12:
            reasons.append("Low volatility")
            return 25
        elif snap.volatility < 20:
            return 15
        else:
            warnings.append("High volatility")
            return 5

    def _calc_confidence(
        self,
        reasons: list[str],
        warnings: list[str],
        range_score: float,
    ) -> float:
        conf = 50.0
        if range_score >= 35:
            conf += 20
        elif range_score >= 20:
            conf += 10
        conf -= len(warnings) * 5.0
        return max(0.0, min(100.0, conf))
