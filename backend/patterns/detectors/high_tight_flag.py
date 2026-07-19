"""
High Tight Flag Pattern Detector.

Detects rapid advance followed by tight consolidation.
"""

from __future__ import annotations

from backend.patterns.base import PatternDetector
from backend.patterns.models import PatternResult, PatternSnapshot, PatternType


class HighTightFlagDetector(PatternDetector):
    """Detects High Tight Flag patterns."""

    pattern_type = PatternType.HIGH_TIGHT_FLAG

    def detect(self, snapshot: PatternSnapshot) -> PatternResult:
        """Detect high tight flag.

        Criteria:
        - Rapid advance (30%+ in short time)
        - Tight flag consolidation
        - Low retracement (<10% from peak)
        """
        reasons: list[str] = []
        warnings: list[str] = []

        advance_score = self._score_advance(snapshot, reasons, warnings)
        flag_score = self._score_flag(snapshot, reasons, warnings)
        retrace_score = self._score_retracement(snapshot, reasons, warnings)

        score = advance_score + flag_score + retrace_score
        score = max(0.0, min(100.0, score))

        confidence = 50.0
        if advance_score >= 30:
            confidence += 15
        if flag_score >= 20:
            confidence += 10
        confidence -= len(warnings) * 5.0
        confidence = max(0.0, min(100.0, confidence))

        return PatternResult(
            pattern_name=PatternType.HIGH_TIGHT_FLAG,
            score=score,
            confidence=confidence,
            pivot_price=snapshot.pivot_price,
            reasons=reasons,
            warnings=warnings,
        )

    def _score_advance(
        self,
        snap: PatternSnapshot,
        reasons: list[str],
        warnings: list[str],
    ) -> float:
        """Score rapid prior advance (0-40)."""
        closes = snap.closes
        if not closes or len(closes) < 5:
            warnings.append("Insufficient data for advance")
            return 0

        start = closes[0]
        peak = max(closes)

        if start == 0:
            return 0

        advance_pct = ((peak - start) / start) * 100

        if advance_pct >= 30:
            reasons.append(f"Rapid advance ({advance_pct:.0f}%)")
            return 40
        elif advance_pct >= 20:
            reasons.append(f"Strong advance ({advance_pct:.0f}%)")
            return 25
        else:
            warnings.append("Weak prior advance")
            return 5

    def _score_flag(
        self,
        snap: PatternSnapshot,
        reasons: list[str],
        warnings: list[str],
    ) -> float:
        """Score tight flag consolidation (0-35)."""
        if not snap.highs or not snap.lows:
            warnings.append("Missing flag range data")
            return 0

        high = max(snap.highs)
        low = min(snap.lows)

        if snap.price == 0:
            return 0

        range_pct = ((high - low) / snap.price) * 100

        if range_pct < 8:
            reasons.append("Tight flag consolidation")
            return 35
        elif range_pct < 15:
            reasons.append("Moderately tight flag")
            return 20
        else:
            warnings.append("Loose flag pattern")
            return 5

    def _score_retracement(
        self,
        snap: PatternSnapshot,
        reasons: list[str],
        warnings: list[str],
    ) -> float:
        """Score low retracement from peak (0-25)."""
        if not snap.closes:
            return 0

        peak = max(snap.closes)
        current = snap.price

        if peak == 0:
            return 0

        retrace = ((peak - current) / peak) * 100

        if retrace < 10:
            reasons.append("Low retracement from peak")
            return 25
        elif retrace < 20:
            return 15
        else:
            warnings.append("Deep retracement")
            return 5
