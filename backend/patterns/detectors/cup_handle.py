"""
Cup & Handle Pattern Detector.

Detects rounded recovery followed by shallow pullback.
"""

from __future__ import annotations

from typing import Optional

from backend.patterns.base import PatternDetector
from backend.patterns.models import PatternResult, PatternSnapshot, PatternType


class CupHandleDetector(PatternDetector):
    """Detects Cup & Handle patterns."""

    pattern_type = PatternType.CUP_HANDLE

    def detect(self, snapshot: PatternSnapshot) -> PatternResult:
        """Detect cup and handle.

        Criteria:
        - Rounded bottom (low in middle, recovery on sides)
        - Shallow handle pullback (<10% from rim)
        - Volume decline during handle
        """
        reasons: list[str] = []
        warnings: list[str] = []

        cup_score = self._score_cup(snapshot, reasons, warnings)
        handle_score = self._score_handle(snapshot, reasons, warnings)
        volume_score = self._score_handle_volume(snapshot, reasons, warnings)

        score = cup_score + handle_score + volume_score
        score = max(0.0, min(100.0, score))

        confidence = 50.0
        if cup_score >= 30:
            confidence += 15
        if handle_score >= 20:
            confidence += 10
        confidence -= len(warnings) * 5.0
        confidence = max(0.0, min(100.0, confidence))

        breakout_price = self._calc_breakout(snapshot)
        stop_price = self._calc_stop(snapshot)

        return PatternResult(
            pattern_name=PatternType.CUP_HANDLE,
            score=score,
            confidence=confidence,
            pivot_price=snapshot.pivot_price,
            breakout_price=breakout_price,
            stop_price=stop_price,
            reasons=reasons,
            warnings=warnings,
        )

    def _score_cup(
        self,
        snap: PatternSnapshot,
        reasons: list[str],
        warnings: list[str],
    ) -> float:
        """Score cup formation (0-40)."""
        closes = snap.closes
        if not closes or len(closes) < 5:
            warnings.append("Insufficient data for cup")
            return 0

        n = len(closes)
        mid = n // 2
        first = closes[:mid]
        last = closes[mid:]

        avg_first = sum(first) / len(first) if first else 0
        avg_last = sum(last) / len(last) if last else 0
        min_close = min(closes)

        rim_diff = abs(avg_first - avg_last) / avg_first * 100 if avg_first else 999
        depth = (avg_first - min_close) / avg_first * 100 if avg_first else 0

        if rim_diff < 5 and 10 < depth < 35:
            reasons.append("Rounded cup formation")
            return 40
        elif rim_diff < 10 and depth < 40:
            reasons.append("Cup formation developing")
            return 25
        else:
            warnings.append("Weak cup formation")
            return 5

    def _score_handle(
        self,
        snap: PatternSnapshot,
        reasons: list[str],
        warnings: list[str],
    ) -> float:
        """Score handle pullback (0-35)."""
        if snap.pivot_price is None or snap.price == 0:
            return 0

        pullback = ((snap.pivot_price - snap.price) / snap.pivot_price) * 100

        if 0 < pullback < 10:
            reasons.append("Shallow handle pullback")
            return 35
        elif pullback < 15:
            reasons.append("Moderate handle pullback")
            return 20
        elif pullback < 25:
            warnings.append("Deep handle pullback")
            return 5
        else:
            warnings.append("Handle too deep")
            return 0

    def _score_handle_volume(
        self,
        snap: PatternSnapshot,
        reasons: list[str],
        warnings: list[str],
    ) -> float:
        """Score volume during handle (0-25)."""
        vd = snap.volume_dryup
        if vd is None:
            return 0

        if vd < 0.6:
            reasons.append("Volume dried in handle")
            return 25
        elif vd < 0.8:
            return 15
        else:
            warnings.append("Weak volume decline in handle")
            return 5

    def _calc_breakout(self, snap: PatternSnapshot) -> Optional[float]:
        if snap.pivot_price is None:
            return None
        return snap.pivot_price * 1.01

    def _calc_stop(self, snap: PatternSnapshot) -> Optional[float]:
        if snap.pivot_price is None:
            return None
        atr = snap.atr if snap.atr is not None else 0
        return snap.pivot_price - atr * 1.5
