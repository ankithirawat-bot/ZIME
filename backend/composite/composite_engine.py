"""
Composite Decision Engine.

Combines outputs of all analysis engines into a single
investment decision using weighted normalization and gating rules.
"""

from __future__ import annotations

from backend.composite.models import (
    CompositeResult,
    InvestmentGrade,
    Recommendation,
)
from backend.patterns.models import PatternResult
from backend.regime.models import MarketRegime, Regime
from backend.relative_strength.models import RelativeStrengthResult
from backend.trend.models import TrendQuality, TrendResult
from backend.volume.models import VolumeResult

# Engine weights
_W_MARKET = 15
_W_RS = 20
_W_TREND = 25
_W_PATTERN = 20
_W_VOLUME = 20
_MAX_WEIGHTED = 100

# Maximum reasons/warnings
_MAX_ITEMS = 15


class CompositeEngine:
    """Composite Decision Engine.

    Combines all engine outputs into a single investment decision.
    """

    def evaluate(
        self,
        market_regime: MarketRegime | None = None,
        relative_strength: RelativeStrengthResult | None = None,
        trend: TrendResult | None = None,
        pattern: PatternResult | None = None,
        volume: VolumeResult | None = None,
    ) -> CompositeResult:
        """Evaluate composite investment decision.

        Args:
            market_regime:   Market regime result.
            relative_strength: Relative strength result.
            trend:           Trend quality result.
            pattern:         Pattern detection result.
            volume:          Volume intelligence result.

        Returns:
            CompositeResult with weighted scores and decision.
        """
        reasons: list[str] = []
        warnings: list[str] = []

        # Extract raw scores (0-100)
        market_raw = self._extract_market_score(market_regime, warnings)
        rs_raw = self._extract_rs_score(relative_strength, warnings)
        trend_raw = self._extract_trend_score(trend, warnings)
        pattern_raw = self._extract_pattern_score(pattern, warnings)
        volume_raw = self._extract_volume_score(volume, warnings)

        # Normalize by weights
        market_score = market_raw * _W_MARKET / _MAX_WEIGHTED
        rs_score = rs_raw * _W_RS / _MAX_WEIGHTED
        trend_score = trend_raw * _W_TREND / _MAX_WEIGHTED
        pattern_score = pattern_raw * _W_PATTERN / _MAX_WEIGHTED
        volume_score = volume_raw * _W_VOLUME / _MAX_WEIGHTED

        overall_score = market_score + rs_score + trend_score + pattern_score + volume_score

        # Aggregate reasons and warnings from all engines
        self._collect_reasons(reasons, market_regime, relative_strength, trend, pattern, volume)
        self._collect_warnings(warnings, market_regime, relative_strength, trend, pattern, volume)

        # Apply gating rules
        recommendation = self._apply_gating(
            overall_score, market_regime, trend, pattern_raw, volume_raw, rs_raw,
        )

        # Cap recommendation
        recommendation = self._cap_recommendation(recommendation, overall_score)

        # Calculate position size
        position_size = self._calculate_position_size(overall_score, rs_raw)

        # Calculate confidence
        confidence = self._calculate_confidence(
            market_raw, rs_raw, trend_raw, pattern_raw, volume_raw, warnings,
        )

        # Classification
        investment_grade = self._classify_grade(overall_score)

        return CompositeResult(
            overall_score=round(overall_score, 2),
            market_score=round(market_score, 2),
            relative_strength_score=round(rs_score, 2),
            trend_score=round(trend_score, 2),
            pattern_score=round(pattern_score, 2),
            volume_score=round(volume_score, 2),
            investment_grade=investment_grade,
            recommendation=recommendation,
            confidence=round(confidence, 2),
            position_size=position_size,
            reasons=reasons[:_MAX_ITEMS],
            warnings=warnings[:_MAX_ITEMS],
        )

    def _extract_market_score(
        self,
        mr: MarketRegime | None,
        warnings: list[str],
    ) -> float:
        """Extract market regime score."""
        if mr is None:
            warnings.append("Missing market regime data")
            return 0
        return mr.score

    def _extract_rs_score(
        self,
        rs: RelativeStrengthResult | None,
        warnings: list[str],
    ) -> float:
        """Extract relative strength score."""
        if rs is None:
            warnings.append("Missing relative strength data")
            return 0
        return rs.overall_score

    def _extract_trend_score(
        self,
        trend: TrendResult | None,
        warnings: list[str],
    ) -> float:
        """Extract trend quality score."""
        if trend is None:
            warnings.append("Missing trend quality data")
            return 0
        return trend.overall_score

    def _extract_pattern_score(
        self,
        pattern: PatternResult | None,
        warnings: list[str],
    ) -> float:
        """Extract pattern score."""
        if pattern is None:
            warnings.append("Missing pattern data")
            return 0
        return pattern.score

    def _extract_volume_score(
        self,
        volume: VolumeResult | None,
        warnings: list[str],
    ) -> float:
        """Extract volume score."""
        if volume is None:
            warnings.append("Missing volume data")
            return 0
        return volume.overall_score

    def _apply_gating(
        self,
        score: float,
        mr: MarketRegime | None,
        trend: TrendResult | None,
        pattern_raw: float,
        volume_raw: float,
        rs_raw: float,
    ) -> Recommendation:
        """Apply gating rules and determine recommendation."""
        # Determine base recommendation from score
        if score >= 95:
            rec = Recommendation.STRONG_BUY
        elif score >= 85:
            rec = Recommendation.BUY
        elif score >= 75:
            rec = Recommendation.WATCHLIST
        elif score >= 60:
            rec = Recommendation.MONITOR
        else:
            rec = Recommendation.AVOID

        # Rule 1: Bear market caps at Monitor
        if mr is not None and mr.regime == Regime.BEAR:
            if rec in (Recommendation.STRONG_BUY, Recommendation.BUY, Recommendation.WATCHLIST):
                rec = Recommendation.MONITOR

        # Rule 2: Broken trend caps at Monitor
        if trend is not None and trend.trend_quality == TrendQuality.BROKEN:
            if rec in (Recommendation.STRONG_BUY, Recommendation.BUY, Recommendation.WATCHLIST):
                rec = Recommendation.MONITOR

        # Rule 3: Weak pattern cannot be Strong Buy
        if pattern_raw < 40 and rec == Recommendation.STRONG_BUY:
            rec = Recommendation.BUY

        return rec

    def _cap_recommendation(
        self,
        rec: Recommendation,
        score: float,
    ) -> Recommendation:
        """Ensure recommendation matches score band."""
        if score < 60 and rec not in (Recommendation.AVOID, Recommendation.MONITOR):
            return Recommendation.AVOID
        if score < 75 and rec in (Recommendation.STRONG_BUY, Recommendation.BUY):
            return Recommendation.WATCHLIST
        return rec

    def _calculate_position_size(
        self,
        score: float,
        rs_raw: float,
    ) -> float:
        """Calculate suggested position size."""
        # Base position size from score
        if score >= 95:
            size = 0.25
        elif score >= 90:
            size = 0.20
        elif score >= 85:
            size = 0.15
        elif score >= 75:
            size = 0.10
        elif score >= 60:
            size = 0.05
        else:
            size = 0.0

        # Rule 5: Weak RS caps at 10%
        if rs_raw < 50 and size > 0.10:
            size = 0.10

        return size

    def _calculate_confidence(
        self,
        market: float,
        rs: float,
        trend: float,
        pattern: float,
        volume: float,
        warnings: list[str],
    ) -> float:
        """Calculate confidence from signal agreement."""
        scores = [market, rs, trend, pattern, volume]
        present = [s for s in scores if s > 0]

        if not present:
            return 0.0

        avg = sum(present) / len(present)
        conf = avg

        # Bonus for agreement (low variance)
        if len(present) >= 3:
            variance = sum((s - avg) ** 2 for s in present) / len(present)
            if variance < 100:
                conf += 10
            elif variance > 400:
                conf -= 10

        # Penalty for weak components
        weak_count = sum(1 for s in scores if 0 < s < 40)
        conf -= weak_count * 5

        # Penalty for warnings
        conf -= len(warnings) * 2.0

        return max(0.0, min(100.0, conf))

    def _classify_grade(self, score: float) -> InvestmentGrade:
        """Classify investment grade from score."""
        if score >= 95:
            return InvestmentGrade.A_PLUS
        elif score >= 90:
            return InvestmentGrade.A
        elif score >= 85:
            return InvestmentGrade.A_MINUS
        elif score >= 80:
            return InvestmentGrade.B_PLUS
        elif score >= 75:
            return InvestmentGrade.B
        elif score >= 70:
            return InvestmentGrade.B_MINUS
        elif score >= 60:
            return InvestmentGrade.C
        elif score >= 50:
            return InvestmentGrade.D
        else:
            return InvestmentGrade.F

    def _collect_reasons(
        self,
        reasons: list[str],
        mr: MarketRegime | None,
        rs: RelativeStrengthResult | None,
        trend: TrendResult | None,
        pattern: PatternResult | None,
        volume: VolumeResult | None,
    ) -> None:
        """Aggregate reasons from all engines."""
        for result in [mr, rs, trend, pattern, volume]:
            if result is None:
                continue
            for r in result.reasons:
                if r not in reasons:
                    reasons.append(r)

    def _collect_warnings(
        self,
        warnings: list[str],
        mr: MarketRegime | None,
        rs: RelativeStrengthResult | None,
        trend: TrendResult | None,
        pattern: PatternResult | None,
        volume: VolumeResult | None,
    ) -> None:
        """Aggregate warnings from all engines."""
        for result in [mr, rs, trend, pattern, volume]:
            if result is None:
                continue
            for w in result.warnings:
                if w not in warnings:
                    warnings.append(w)
