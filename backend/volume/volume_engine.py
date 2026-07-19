"""
Volume Intelligence Engine.

Evaluates whether price action is supported by
institutional-quality volume using deterministic scoring.
"""

from __future__ import annotations

from backend.volume.models import (
    VolumeQuality,
    VolumeResult,
    VolumeSnapshot,
)

# Scoring weights
_MAX_RVOL = 20
_MAX_BREAKOUT = 20
_MAX_DRYUP = 15
_MAX_ACCUM = 20
_MAX_DISTRIB = 15
_MAX_INSTITUTIONAL = 10

# RVOL thresholds
_RVOL_STRONG = 2.0
_RVOL_ELEVATED = 1.5
_RVOL_ABOVE = 1.2
_RVOL_NORMAL = 1.0


class VolumeEngine:
    """Volume Intelligence Engine.

    Evaluates institutional-quality volume support for price action.
    """

    def evaluate(self, snapshot: VolumeSnapshot) -> VolumeResult:
        """Evaluate volume quality from a snapshot.

        Args:
            snapshot: Volume and price data.

        Returns:
            VolumeResult with scores and classification.
        """
        reasons: list[str] = []
        warnings: list[str] = []

        rvol_score = self._score_rvol(snapshot, reasons, warnings)
        breakout_score = self._score_breakout(snapshot, reasons, warnings)
        dryup_score = self._score_dryup(snapshot, reasons, warnings)
        accum_score = self._score_accumulation(snapshot, reasons, warnings)
        distrib_score = self._score_distribution(snapshot, reasons, warnings)
        inst_score = self._score_institutional(
            snapshot, rvol_score, breakout_score, dryup_score,
            accum_score, distrib_score,
        )

        # Distribution is a penalty — subtract from total
        penalty = distrib_score
        raw_score = (
            rvol_score + breakout_score + dryup_score
            + accum_score + inst_score - penalty
        )
        overall_score = max(0.0, min(100.0, raw_score))

        volume_quality = self._classify_quality(overall_score)
        confidence = self._calculate_confidence(
            snapshot, reasons, warnings,
            rvol_score, breakout_score, accum_score,
        )

        return VolumeResult(
            overall_score=overall_score,
            rvol_score=rvol_score,
            breakout_score=breakout_score,
            dryup_score=dryup_score,
            accumulation_score=accum_score,
            distribution_score=distrib_score,
            institutional_score=inst_score,
            volume_quality=volume_quality,
            confidence=confidence,
            reasons=reasons,
            warnings=warnings,
        )

    def _score_rvol(
        self,
        snap: VolumeSnapshot,
        reasons: list[str],
        warnings: list[str],
    ) -> float:
        """Score relative volume (0-20).

        RVOL > 2.0 = 20, 1.5-2.0 = 16, 1.2-1.5 = 12,
        1.0-1.2 = 8, <1.0 = 4.
        """
        rvol = snap.rvol

        if rvol is None:
            # Estimate from volume / avg_volume_20
            if snap.volume > 0 and snap.avg_volume_20 is not None and snap.avg_volume_20 > 0:
                rvol = snap.volume / snap.avg_volume_20
            else:
                warnings.append("Missing volume history")
                return 0

        if rvol >= _RVOL_STRONG:
            reasons.append("Strong relative volume")
            return _MAX_RVOL
        elif rvol >= _RVOL_ELEVATED:
            reasons.append("Elevated relative volume")
            return 16
        elif rvol >= _RVOL_ABOVE:
            reasons.append("Above-average volume")
            return 12
        elif rvol >= _RVOL_NORMAL:
            return 8
        else:
            reasons.append("Below-average volume")
            return 4

    def _score_breakout(
        self,
        snap: VolumeSnapshot,
        reasons: list[str],
        warnings: list[str],
    ) -> float:
        """Score breakout confirmation (0-20).

        Evaluates breakout volume, close position, and trend agreement.
        """
        score = 0.0
        signals = 0

        # Breakout volume component (0-10)
        bv = snap.breakout_volume
        if bv is not None and bv > 0:
            avg = snap.avg_volume_20
            if avg is not None and avg > 0:
                ratio = bv / avg
                if ratio >= 2.0:
                    score += 10
                    reasons.append("Strong breakout volume")
                    signals += 1
                elif ratio >= 1.5:
                    score += 7
                    reasons.append("Moderate breakout volume")
                    signals += 1
                else:
                    score += 3
                    warnings.append("Weak breakout volume")
            else:
                score += 5
                signals += 1

        # Close position component (0-5)
        cp = snap.close_position_percent
        if cp is not None:
            if cp >= 70:
                score += 5
                reasons.append("Close near highs")
                signals += 1
            elif cp >= 50:
                score += 3
            else:
                score += 0
                warnings.append("Weak closing prices")

        # Trend quality agreement (0-5)
        tq = snap.trend_quality
        if tq is not None:
            if tq >= 70:
                score += 5
                reasons.append("Trend quality confirms breakout")
                signals += 1
            elif tq >= 50:
                score += 3
            else:
                warnings.append("Poor trend quality")

        if signals == 0 and bv is None and cp is None:
            warnings.append("Breakout lacks confirmation")

        return min(float(_MAX_BREAKOUT), score)

    def _score_dryup(
        self,
        snap: VolumeSnapshot,
        reasons: list[str],
        warnings: list[str],
    ) -> float:
        """Score volume dry-up during consolidation (0-15)."""
        cv = snap.consolidation_volume
        avg20 = snap.avg_volume_20

        if cv is None or avg20 is None or avg20 == 0:
            return 0

        ratio = cv / avg20

        if ratio < 0.5:
            reasons.append("Volume contracted during consolidation")
            return _MAX_DRYUP
        elif ratio < 0.7:
            reasons.append("Volume declining in consolidation")
            return 10
        elif ratio < 0.9:
            return 5
        else:
            return 0

    def _score_accumulation(
        self,
        snap: VolumeSnapshot,
        reasons: list[str],
        warnings: list[str],
    ) -> float:
        """Score accumulation days (0-20).

        More accumulation days + strong closes = higher score.
        """
        acc = snap.accumulation_days

        if acc is None:
            return 0

        # Base score from accumulation days (0-12)
        if acc >= 6:
            day_score = 12
            reasons.append("Healthy accumulation")
        elif acc >= 3:
            day_score = 8
            reasons.append("Moderate accumulation")
        elif acc >= 1:
            day_score = 4
        else:
            day_score = 0
            warnings.append("No accumulation detected")

        # Close position bonus (0-4)
        cp = snap.close_position_percent
        close_bonus = 0
        if cp is not None:
            if cp >= 70:
                close_bonus = 4
            elif cp >= 50:
                close_bonus = 2

        # Volume confirmation bonus (0-4)
        vol_bonus = 0
        if snap.volume > 0 and snap.avg_volume_20 is not None and snap.avg_volume_20 > 0:
            if snap.volume > snap.avg_volume_20:
                vol_bonus = 4
            elif snap.volume > snap.avg_volume_20 * 0.8:
                vol_bonus = 2

        return min(float(_MAX_ACCUM), day_score + close_bonus + vol_bonus)

    def _score_distribution(
        self,
        snap: VolumeSnapshot,
        reasons: list[str],
        warnings: list[str],
    ) -> float:
        """Score distribution penalty (0-15).

        Higher distribution = more penalty.
        """
        dist = snap.distribution_days

        if dist is None:
            return 0

        if dist >= 4:
            reasons.append("Multiple distribution days")
            return _MAX_DISTRIB
        elif dist >= 2:
            reasons.append("Distribution detected")
            return 10
        elif dist >= 1:
            return 5
        else:
            return 0

    def _score_institutional(
        self,
        snap: VolumeSnapshot,
        rvol: float,
        breakout: float,
        dryup: float,
        accum: float,
        distrib: float,
    ) -> float:
        """Estimate institutional participation (0-10).

        Derived from agreement of other signals.
        """
        signals = 0
        total = 0

        if rvol >= 12:
            signals += 1
        total += 1

        if breakout >= 14:
            signals += 1
        total += 1

        if dryup >= 10:
            signals += 1
        total += 1

        if accum >= 12:
            signals += 1
        total += 1

        if distrib <= 5:
            signals += 1
        total += 1

        if total == 0:
            return 0

        ratio = signals / total
        return min(float(_MAX_INSTITUTIONAL), _MAX_INSTITUTIONAL * ratio)

    def _classify_quality(self, score: float) -> VolumeQuality:
        """Classify volume quality based on score."""
        if score >= 90:
            return VolumeQuality.EXCEPTIONAL
        elif score >= 75:
            return VolumeQuality.STRONG
        elif score >= 55:
            return VolumeQuality.HEALTHY
        elif score >= 35:
            return VolumeQuality.WEAK
        else:
            return VolumeQuality.POOR

    def _calculate_confidence(
        self,
        snap: VolumeSnapshot,
        reasons: list[str],
        warnings: list[str],
        rvol: float,
        breakout: float,
        accum: float,
    ) -> float:
        """Calculate confidence based on signal agreement."""
        conf = 50.0

        # Strong signals boost confidence
        if rvol >= 16:
            conf += 10
        elif rvol >= 12:
            conf += 5

        if breakout >= 14:
            conf += 10
        elif breakout >= 10:
            conf += 5

        if accum >= 12:
            conf += 10
        elif accum >= 8:
            conf += 5

        # Reduce for warnings
        conf -= len(warnings) * 4.0

        # Reduce for conflicting signals
        has_accum = accum >= 8
        has_distrib = snap.distribution_days is not None and snap.distribution_days >= 2
        if has_accum and has_distrib:
            conf -= 10

        return max(0.0, min(100.0, conf))
