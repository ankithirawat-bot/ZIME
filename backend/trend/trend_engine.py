"""
Trend Quality Engine.

Evaluates structural trend health using moving average alignment,
price position, slope direction, trend structure, persistence,
and 52-week proximity.
"""

from __future__ import annotations

from typing import Optional

from backend.trend.models import TrendQuality, TrendResult, TrendSnapshot, TrendStage

# Scoring weights
_MAX_ALIGNMENT = 20
_MAX_PRICE_POSITION = 15
_MAX_SLOPES = 20
_MAX_STRUCTURE = 20
_MAX_PERSISTENCE = 10
_MAX_HIGH_PROXIMITY = 15

# Persistence thresholds
_PERSIST_LATE = 120
_PERSIST_ESTABLISHED = 60
_PERSIST_YOUNG = 20

# High proximity thresholds (distance from 52w high)
_HIGH_NEAR = 5
_HIGH_CLOSE = 10
_HIGH_MID = 20
_HIGH_EXTENDED = 35


class TrendQualityEngine:
    """Production Trend Quality Engine.

    Evaluates whether a trend is healthy, persistent, and investable.
    """

    def evaluate(self, snapshot: TrendSnapshot) -> TrendResult:
        """Evaluate trend quality from a snapshot.

        Args:
            snapshot: Complete trend snapshot.

        Returns:
            A TrendResult with scores and classification.
        """
        alignment_score, alignment_reasons, alignment_warnings = (
            self._score_alignment(snapshot)
        )
        price_score, price_reasons, price_warnings = (
            self._score_price_position(snapshot)
        )
        slope_score, slope_reasons, slope_warnings = self._score_slopes(snapshot)
        struct_score, struct_reasons, struct_warnings = self._score_structure(snapshot)
        persist_score, persist_reasons = self._score_persistence(snapshot)
        high_score, high_reasons = self._score_high_proximity(
            snapshot.current_price, snapshot.high_52w
        )

        all_warnings = alignment_warnings + price_warnings + slope_warnings + struct_warnings
        ext_warnings = self._check_price_extension(snapshot)
        all_warnings.extend(ext_warnings)

        if snapshot.history_length is not None and snapshot.history_length < 100:
            all_warnings.append(
                f"Insufficient history: only {snapshot.history_length} data points"
            )

        overall_score = (
            alignment_score + price_score + slope_score
            + struct_score + persist_score + high_score
        )
        overall_score = max(0.0, min(100.0, overall_score))

        trend_quality = self._classify_quality(overall_score)
        trend_stage = self._classify_stage(snapshot, trend_quality)

        reasons = self._build_reasons([
            alignment_reasons, price_reasons, slope_reasons,
            struct_reasons, persist_reasons, high_reasons,
        ])

        confidence = self._calculate_confidence(
            snapshot, all_warnings, alignment_score, slope_score,
            struct_score, persist_score,
        )

        return TrendResult(
            overall_score=overall_score,
            alignment_score=alignment_score,
            price_position_score=price_score,
            slope_score=slope_score,
            structure_score=struct_score,
            persistence_score=persist_score,
            high_score=high_score,
            trend_quality=trend_quality,
            trend_stage=trend_stage,
            confidence=confidence,
            reasons=reasons,
            warnings=all_warnings,
        )

    def _score_alignment(
        self, snapshot: TrendSnapshot
    ) -> tuple[float, list[str], list[str]]:
        """Score moving average alignment.

        Perfect: EMA20 > EMA50 > SMA150 > SMA200 = 20 pts.

        Returns:
            Tuple of (score, reasons, warnings).
        """
        avails = [
            ("EMA20", snapshot.ema20),
            ("EMA50", snapshot.ema50),
            ("SMA150", snapshot.sma150),
            ("SMA200", snapshot.sma200),
        ]
        present = [(n, v) for n, v in avails if v is not None]

        if len(present) < 2:
            return 0, [], ["Missing averages: insufficient data for alignment"]

        values = [v for _, v in present]
        aligned = sum(
            1 for i in range(len(values) - 1) if values[i] > values[i + 1]
        )
        total = len(values) - 1

        if aligned == total and len(present) == 4:
            return _MAX_ALIGNMENT, ["Moving averages perfectly aligned"], []
        elif aligned > 0:
            score = _MAX_ALIGNMENT * (aligned / total)
            return score, [
                f"Moving averages partially aligned ({aligned}/{total})"
            ], []
        else:
            return 0, ["Moving averages not aligned"], []

    def _score_price_position(
        self, snapshot: TrendSnapshot
    ) -> tuple[float, list[str], list[str]]:
        """Score price position relative to moving averages.

        Each average above = 3.75 pts (max 15).

        Returns:
            Tuple of (score, reasons, warnings).
        """
        avails = [
            ("EMA20", snapshot.ema20),
            ("EMA50", snapshot.ema50),
            ("SMA150", snapshot.sma150),
            ("SMA200", snapshot.sma200),
        ]
        present = [(n, v) for n, v in avails if v is not None]

        if not present:
            return 0, [], ["Missing averages: no price position data"]

        above = sum(1 for _, v in present if snapshot.current_price > v)

        if above == len(present):
            return _MAX_PRICE_POSITION, ["Price above all averages"], []
        elif above > 0:
            score = _MAX_PRICE_POSITION * (above / len(present))
            return score, [f"Price above {above}/{len(present)} averages"], []
        else:
            return 0, ["Price below all major averages"], []

    def _score_slopes(
        self, snapshot: TrendSnapshot
    ) -> tuple[float, list[str], list[str]]:
        """Score moving average slope directions.

        Each rising slope = 5 pts (max 20).

        Returns:
            Tuple of (score, reasons, warnings).
        """
        slopes = [
            ("EMA20", snapshot.slope_ema20),
            ("EMA50", snapshot.slope_ema50),
            ("SMA150", snapshot.slope_sma150),
            ("SMA200", snapshot.slope_sma200),
        ]
        present = [(n, v) for n, v in slopes if v is not None]

        if not present:
            return 0, [], ["Missing slopes: no trend direction data"]

        rising = sum(1 for _, v in present if v > 0)

        extra_warnings: list[str] = []
        if snapshot.slope_sma200 is not None and snapshot.slope_sma200 < 0:
            extra_warnings.append("Falling SMA200")

        if rising == len(present):
            return _MAX_SLOPES, ["Long-term averages rising"], extra_warnings
        elif rising > 0:
            score = _MAX_SLOPES * (rising / len(present))
            return score, [f"{rising}/{len(present)} slopes rising"], extra_warnings
        else:
            return 0, ["All slopes declining"], extra_warnings

    def _score_structure(
        self, snapshot: TrendSnapshot
    ) -> tuple[float, list[str], list[str]]:
        """Score trend structure using higher high/low counts.

        Score = (hh + hl) * 4, max 20.

        Returns:
            Tuple of (score, reasons, warnings).
        """
        hh = snapshot.higher_high_count
        hl = snapshot.higher_low_count

        if hh is None and hl is None:
            return 0, [], ["Missing structure data: no higher highs/lows info"]

        hh_val = hh if hh is not None else 0
        hl_val = hl if hl is not None else 0
        raw = (hh_val + hl_val) * 4
        score = min(float(_MAX_STRUCTURE), float(raw))

        reasons: list[str] = []
        warnings: list[str] = []

        if hh is not None and hh > 0:
            reasons.append(f"Strong higher-high structure ({hh})")
        elif hh is not None and hh == 0:
            warnings.append("No higher highs detected")

        if hl is not None and hl > 0:
            reasons.append(f"Strong higher-low structure ({hl})")
        elif hl is not None and hl == 0:
            warnings.append("Lower lows detected")

        return score, reasons, warnings

    def _score_persistence(
        self, snapshot: TrendSnapshot
    ) -> tuple[float, list[str]]:
        """Score trend persistence based on age.

        Thresholds: 0→0, <20→2, 20-60→5, 60-120→8, 120+→10.

        Returns:
            Tuple of (score, reasons).
        """
        age = snapshot.trend_age

        if age is None:
            return 0, []

        if age >= _PERSIST_LATE:
            return _MAX_PERSISTENCE, [f"Trend persisted for {age} bars"]
        elif age >= _PERSIST_ESTABLISHED:
            return 8, [f"Trend persisted for {age} bars"]
        elif age >= _PERSIST_YOUNG:
            return 5, [f"Trend persisted for {age} bars"]
        elif age > 0:
            return 2, [f"Trend persisted for {age} bars"]
        else:
            return 0, []

    def _score_high_proximity(
        self,
        current_price: float,
        high_52w: Optional[float],
    ) -> tuple[float, list[str]]:
        """Score based on distance from 52-week high.

        0-5% = 15, 5-10% = 12, 10-20% = 8, 20-35% = 4, >35% = 0.

        Returns:
            Tuple of (score, reasons).
        """
        if high_52w is None or high_52w == 0:
            return 0, []

        distance = ((high_52w - current_price) / high_52w) * 100

        if distance <= _HIGH_NEAR:
            return _MAX_HIGH_PROXIMITY, [
                f"Trading within {distance:.1f}% of 52-week high"
            ]
        elif distance <= _HIGH_CLOSE:
            return 12, [f"Trading {distance:.1f}% below 52-week high"]
        elif distance <= _HIGH_MID:
            return 8, [f"Trading {distance:.1f}% below 52-week high"]
        elif distance <= _HIGH_EXTENDED:
            return 4, [f"Trading {distance:.1f}% below 52-week high"]
        else:
            return 0, [f"Trading {distance:.1f}% below 52-week high"]

    def _classify_quality(self, score: float) -> TrendQuality:
        """Classify trend quality based on score.

        90+: Exceptional, 75-89: Strong, 55-74: Healthy,
        35-54: Weak, <35: Broken.
        """
        if score >= 90:
            return TrendQuality.EXCEPTIONAL
        elif score >= 75:
            return TrendQuality.STRONG
        elif score >= 55:
            return TrendQuality.HEALTHY
        elif score >= 35:
            return TrendQuality.WEAK
        else:
            return TrendQuality.BROKEN

    def _classify_stage(
        self, snapshot: TrendSnapshot, quality: TrendQuality
    ) -> TrendStage:
        """Classify trend lifecycle stage.

        Uses alignment, trend age, structure, and price extension.
        """
        if quality == TrendQuality.BROKEN:
            return TrendStage.BROKEN

        age = snapshot.trend_age
        if age is None:
            return TrendStage.ESTABLISHED

        if age < _PERSIST_YOUNG:
            return TrendStage.EARLY
        elif age <= _PERSIST_LATE:
            return TrendStage.ESTABLISHED
        else:
            if snapshot.ema20 is not None and snapshot.ema20 > 0:
                ext = ((snapshot.current_price - snapshot.ema20) / snapshot.ema20) * 100
                if ext > 20:
                    return TrendStage.EXTENDED
            return TrendStage.LATE

    def _calculate_confidence(
        self,
        snapshot: TrendSnapshot,
        warnings: list[str],
        alignment_score: float,
        slope_score: float,
        struct_score: float,
        persist_score: float,
    ) -> float:
        """Calculate confidence based on data quality and completeness.

        Increases with strong signals, reduces with missing data.
        """
        confidence = 50.0

        # Strong alignment boosts confidence
        if alignment_score == _MAX_ALIGNMENT:
            confidence += 15
        elif alignment_score > 0:
            confidence += 5

        # Positive slopes boost confidence
        if slope_score == _MAX_SLOPES:
            confidence += 15
        elif slope_score > 0:
            confidence += 5

        # Strong structure boosts confidence
        if struct_score >= 16:
            confidence += 10
        elif struct_score > 0:
            confidence += 3

        # Sufficient persistence boosts confidence
        if persist_score >= 8:
            confidence += 10
        elif persist_score > 0:
            confidence += 3

        # Reduce for warnings
        confidence -= len(warnings) * 4.0

        # Reduce for insufficient history
        if snapshot.history_length is not None and snapshot.history_length < 200:
            confidence -= 5.0

        return max(0.0, min(100.0, confidence))

    def _check_price_extension(self, snapshot: TrendSnapshot) -> list[str]:
        """Check if price is extended above EMA20."""
        if snapshot.ema20 is None or snapshot.ema20 == 0:
            return []

        extension = ((snapshot.current_price - snapshot.ema20) / snapshot.ema20) * 100
        if extension > 20:
            return [f"Price extended: {extension:.1f}% above EMA20"]
        return []

    def _build_reasons(self, reason_groups: list[list[str]]) -> list[str]:
        """Flatten and deduplicate reason lists."""
        seen: set[str] = set()
        result: list[str] = []
        for group in reason_groups:
            for reason in group:
                if reason not in seen:
                    seen.add(reason)
                    result.append(reason)
        return result
