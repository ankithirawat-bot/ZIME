"""
VCP (Volatility Contraction Pattern) Detector.

Detects tightening price ranges with declining volume,
signaling potential breakout.

Scoring:
- Volatility contraction: 35
- Volume dry-up: 20
- Breakout level: 20
- Trend quality: 15
- Relative strength: 10
"""

from __future__ import annotations

from typing import Optional

from backend.patterns.base import PatternDetector
from backend.patterns.models import PatternResult, PatternSnapshot, PatternType

_MAX_CONTRACTION = 35
_MAX_VOLUME = 20
_MAX_BREAKOUT = 20
_MAX_TREND = 15
_MAX_RS = 10


class VCPDetector(PatternDetector):
    """Detects Volatility Contraction Patterns."""

    pattern_type = PatternType.VCP

    def detect(self, snapshot: PatternSnapshot) -> PatternResult:
        """Detect VCP pattern.

        Args:
            snapshot: Market data.

        Returns:
            PatternResult with VCP analysis.
        """
        reasons: list[str] = []
        warnings: list[str] = []

        contraction_score = self._score_contraction(snapshot, reasons, warnings)
        volume_score = self._score_volume(snapshot, reasons, warnings)
        breakout_score = self._score_breakout(snapshot, reasons, warnings)
        trend_score = self._score_trend(snapshot, reasons, warnings)
        rs_score = self._score_rs(snapshot, reasons, warnings)

        score = (
            contraction_score + volume_score + breakout_score
            + trend_score + rs_score
        )
        score = max(0.0, min(100.0, score))

        confidence = self._calculate_confidence(
            snapshot, reasons, warnings,
            contraction_score, volume_score, breakout_score,
        )

        breakout_price = self._calc_breakout(snapshot)
        stop_price = self._calc_stop(snapshot)
        risk_reward = self._calc_rr(snapshot.price, breakout_price, stop_price)

        return PatternResult(
            pattern_name=PatternType.VCP,
            score=score,
            confidence=confidence,
            pivot_price=snapshot.pivot_price,
            breakout_price=breakout_price,
            stop_price=stop_price,
            risk_reward=risk_reward,
            reasons=reasons,
            warnings=warnings,
        )

    def _score_contraction(
        self,
        snap: PatternSnapshot,
        reasons: list[str],
        warnings: list[str],
    ) -> float:
        """Score volatility contraction (0-35).

        More contractions and lower volatility = higher score.
        """
        cc = snap.contraction_count
        vol = snap.volatility

        if cc is None and vol is None:
            warnings.append("Missing contraction data")
            return 0

        score = 0.0

        if cc is not None:
            if cc >= 4:
                score += _MAX_CONTRACTION
                reasons.append("Strong volatility contraction")
            elif cc >= 2:
                score += _MAX_CONTRACTION * 0.6
                reasons.append("Moderate volatility contraction")
            else:
                score += _MAX_CONTRACTION * 0.2
                warnings.append("Pattern immature")

        if vol is not None:
            if vol < 15:
                score = min(_MAX_CONTRACTION, score + 10)
            elif vol > 30:
                score = max(0, score - 5)
                warnings.append("High volatility")

        return min(float(_MAX_CONTRACTION), score)

    def _score_volume(
        self,
        snap: PatternSnapshot,
        reasons: list[str],
        warnings: list[str],
    ) -> float:
        """Score volume dry-up (0-20)."""
        vd = snap.volume_dryup

        if vd is None:
            warnings.append("Missing volume dry-up data")
            return 0

        if vd < 0.5:
            reasons.append("Volume dried during consolidation")
            return _MAX_VOLUME
        elif vd < 0.7:
            reasons.append("Volume declining")
            return _MAX_VOLUME * 0.7
        else:
            warnings.append("Weak volume dry-up")
            return _MAX_VOLUME * 0.3

    def _score_breakout(
        self,
        snap: PatternSnapshot,
        reasons: list[str],
        warnings: list[str],
    ) -> float:
        """Score breakout level proximity (0-20)."""
        pivot = snap.pivot_price
        if pivot is None or pivot == 0:
            warnings.append("Missing pivot price")
            return 0

        distance = ((pivot - snap.price) / pivot) * 100

        if distance <= 2:
            reasons.append("Trading near pivot")
            return _MAX_BREAKOUT
        elif distance <= 5:
            reasons.append("Close to pivot")
            return _MAX_BREAKOUT * 0.7
        elif distance <= 10:
            return _MAX_BREAKOUT * 0.4
        else:
            warnings.append("Far from pivot")
            return 0

    def _score_trend(
        self,
        snap: PatternSnapshot,
        reasons: list[str],
        warnings: list[str],
    ) -> float:
        """Score trend quality (0-15)."""
        tq = snap.trend_quality
        if tq is None:
            return 0

        if tq >= 70:
            reasons.append("Trend quality supportive")
            return _MAX_TREND
        elif tq >= 50:
            return _MAX_TREND * 0.6
        else:
            warnings.append("Poor trend quality")
            return 0

    def _score_rs(
        self,
        snap: PatternSnapshot,
        reasons: list[str],
        warnings: list[str],
    ) -> float:
        """Score relative strength (0-10)."""
        rs = snap.relative_strength
        if rs is None:
            return 0

        if rs >= 70:
            reasons.append("Relative strength supportive")
            return _MAX_RS
        elif rs >= 50:
            return _MAX_RS * 0.5
        else:
            return 0

    def _calculate_confidence(
        self,
        snap: PatternSnapshot,
        reasons: list[str],
        warnings: list[str],
        contraction: float,
        volume: float,
        breakout: float,
    ) -> float:
        """Calculate confidence from signal agreement."""
        conf = 50.0

        if contraction >= _MAX_CONTRACTION * 0.8:
            conf += 15
        if volume >= _MAX_VOLUME * 0.7:
            conf += 10
        if breakout >= _MAX_BREAKOUT * 0.7:
            conf += 10
        if snap.trend_quality is not None and snap.trend_quality >= 70:
            conf += 10
        if snap.relative_strength is not None and snap.relative_strength >= 70:
            conf += 5

        conf -= len(warnings) * 5.0

        return max(0.0, min(100.0, conf))

    def _calc_breakout(self, snap: PatternSnapshot) -> Optional[float]:
        pivot = snap.pivot_price
        if pivot is None:
            return None
        atr = snap.atr if snap.atr is not None else 0
        return pivot + atr * 0.1

    def _calc_stop(self, snap: PatternSnapshot) -> Optional[float]:
        pivot = snap.pivot_price
        if pivot is None:
            return None
        atr = snap.atr if snap.atr is not None else 0
        return pivot - atr * 1.5

    def _calc_rr(
        self,
        price: float,
        breakout: Optional[float],
        stop: Optional[float],
    ) -> Optional[float]:
        if breakout is None or stop is None or stop == 0:
            return None
        entry = max(price, breakout)
        risk = entry - stop
        reward = breakout - entry + (breakout - price)
        if risk <= 0:
            return None
        return round(reward / risk, 2)
