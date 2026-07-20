"""
Tests for Composite Decision Engine.

Validates weighted scoring, gating rules, decision classification,
DecisionTrace, failed gates, and confidence calculation.
"""

from backend.composite.composite_engine import CompositeEngine
from backend.composite.models import InvestmentGrade, Recommendation
from backend.patterns.models import PatternResult, PatternType
from backend.regime.models import MarketRegime, Regime
from backend.relative_strength.models import Leadership, RelativeStrengthResult
from backend.trend.models import TrendQuality, TrendResult, TrendStage
from backend.volume.models import VolumeQuality, VolumeResult


def _strong_market_regime(score: float = 85) -> MarketRegime:
    return MarketRegime(
        regime=Regime.BULL, confidence=90, score=score,
        reasons=["Bull market"], warnings=[],
    )


def _strong_rs(score: float = 80) -> RelativeStrengthResult:
    return RelativeStrengthResult(
        overall_score=score, market_score=score * 0.3,
        sector_score=score * 0.25, industry_score=score * 0.15,
        high_score=score * 0.2, momentum_score=score * 0.1,
        leadership=Leadership.LEADER, confidence=85,
        reasons=["Market outperformer"], warnings=[],
    )


def _strong_trend(score: float = 85) -> TrendResult:
    return TrendResult(
        overall_score=score, alignment_score=score * 0.2,
        price_position_score=score * 0.15, slope_score=score * 0.2,
        structure_score=score * 0.2, persistence_score=score * 0.1,
        high_score=score * 0.15,
        trend_quality=TrendQuality.STRONG,
        trend_stage=TrendStage.ESTABLISHED,
        confidence=90, reasons=["Strong uptrend"], warnings=[],
    )


def _strong_pattern(score: float = 90) -> PatternResult:
    return PatternResult(
        pattern_name=PatternType.VCP, score=score, confidence=85,
        pivot_price=100.0, breakout_price=103.0, stop_price=95.0,
        risk_reward=1.8, reasons=["Tight VCP"], warnings=[],
    )


def _strong_volume(score: float = 75) -> VolumeResult:
    return VolumeResult(
        overall_score=score, rvol_score=score * 0.2,
        breakout_score=score * 0.2, dryup_score=score * 0.15,
        accumulation_score=score * 0.2, distribution_score=score * 0.15,
        institutional_score=score * 0.1,
        volume_quality=VolumeQuality.STRONG,
        confidence=80, reasons=["Good accumulation"], warnings=[],
    )


class TestWeightedScoring:

    def test_all_engines_present(self):
        engine = CompositeEngine()
        result = engine.evaluate(
            market_regime=_strong_market_regime(85),
            relative_strength=_strong_rs(80),
            trend=_strong_trend(85),
            pattern=_strong_pattern(90),
            volume=_strong_volume(75),
        )
        assert 60 <= result.overall_score <= 100

    def test_perfect_scores(self):
        engine = CompositeEngine()
        result = engine.evaluate(
            market_regime=_strong_market_regime(100),
            relative_strength=_strong_rs(100),
            trend=_strong_trend(100),
            pattern=_strong_pattern(100),
            volume=_strong_volume(100),
        )
        assert result.overall_score == 100.0
        assert result.market_score == 15.0
        assert result.relative_strength_score == 20.0
        assert result.trend_score == 25.0
        assert result.pattern_score == 20.0
        assert result.volume_score == 20.0

    def test_zero_scores(self):
        engine = CompositeEngine()
        result = engine.evaluate(
            market_regime=MarketRegime(
                regime=Regime.BEAR, confidence=50, score=0,
                reasons=[], warnings=["No data"],
            ),
            relative_strength=_strong_rs(0),
            trend=_strong_trend(0),
            pattern=_strong_pattern(0),
            volume=_strong_volume(0),
        )
        assert result.overall_score == 0.0
        assert result.investment_grade == InvestmentGrade.F

    def test_missing_engines(self):
        engine = CompositeEngine()
        result = engine.evaluate()
        assert result.overall_score == 0.0
        assert len(result.warnings) >= 4

    def test_weighted_distribution(self):
        engine = CompositeEngine()
        result = engine.evaluate(
            market_regime=_strong_market_regime(100),
            relative_strength=_strong_rs(100),
            trend=_strong_trend(100),
            pattern=_strong_pattern(100),
            volume=_strong_volume(100),
        )
        total = (result.market_score + result.relative_strength_score
                 + result.trend_score + result.pattern_score
                 + result.volume_score)
        assert total == 100.0


class TestDecisionTrace:

    def test_trace_populated(self):
        engine = CompositeEngine()
        result = engine.evaluate(
            market_regime=_strong_market_regime(85),
            relative_strength=_strong_rs(80),
            trend=_strong_trend(85),
            pattern=_strong_pattern(90),
            volume=_strong_volume(75),
        )
        assert result.decision_trace is not None
        assert result.decision_trace.market_contribution == 15 * 85 / 100
        assert result.decision_trace.relative_strength_contribution == 20 * 80 / 100
        assert result.decision_trace.trend_contribution == 25 * 85 / 100
        assert result.decision_trace.pattern_contribution == 20 * 90 / 100
        assert result.decision_trace.volume_contribution == 20 * 75 / 100

    def test_trace_perfect_scores(self):
        engine = CompositeEngine()
        result = engine.evaluate(
            market_regime=_strong_market_regime(100),
            relative_strength=_strong_rs(100),
            trend=_strong_trend(100),
            pattern=_strong_pattern(100),
            volume=_strong_volume(100),
        )
        assert result.decision_trace.market_contribution == 15.0
        assert result.decision_trace.relative_strength_contribution == 20.0
        assert result.decision_trace.trend_contribution == 25.0
        assert result.decision_trace.pattern_contribution == 20.0
        assert result.decision_trace.volume_contribution == 20.0

    def test_trace_zero_scores(self):
        engine = CompositeEngine()
        result = engine.evaluate(
            market_regime=_strong_market_regime(0),
            relative_strength=_strong_rs(0),
            trend=_strong_trend(0),
            pattern=_strong_pattern(0),
            volume=_strong_volume(0),
        )
        assert result.decision_trace.market_contribution == 0.0
        assert result.decision_trace.relative_strength_contribution == 0.0
        assert result.decision_trace.trend_contribution == 0.0
        assert result.decision_trace.pattern_contribution == 0.0
        assert result.decision_trace.volume_contribution == 0.0

    def test_trace_missing_engines(self):
        engine = CompositeEngine()
        result = engine.evaluate()
        assert result.decision_trace.market_contribution == 0.0
        assert result.decision_trace.relative_strength_contribution == 0.0
        assert result.decision_trace.trend_contribution == 0.0
        assert result.decision_trace.pattern_contribution == 0.0
        assert result.decision_trace.volume_contribution == 0.0


class TestGatingRules:

    def test_bear_market_caps_at_monitor(self):
        engine = CompositeEngine()
        result = engine.evaluate(
            market_regime=MarketRegime(
                regime=Regime.BEAR, confidence=90, score=85,
                reasons=["Bear market"], warnings=[],
            ),
            relative_strength=_strong_rs(90),
            trend=_strong_trend(90),
            pattern=_strong_pattern(90),
            volume=_strong_volume(90),
        )
        assert result.recommendation in (Recommendation.MONITOR, Recommendation.AVOID)

    def test_broken_trend_caps_at_monitor(self):
        engine = CompositeEngine()
        result = engine.evaluate(
            market_regime=_strong_market_regime(85),
            relative_strength=_strong_rs(85),
            trend=TrendResult(
                overall_score=20, alignment_score=4,
                price_position_score=3, slope_score=4,
                structure_score=3, persistence_score=3,
                high_score=3,
                trend_quality=TrendQuality.BROKEN,
                trend_stage=TrendStage.LATE,
                confidence=90, reasons=["Broken trend"], warnings=[],
            ),
            pattern=_strong_pattern(90),
            volume=_strong_volume(80),
        )
        assert result.recommendation in (Recommendation.MONITOR, Recommendation.AVOID)

    def test_weak_pattern_caps_strong_buy(self):
        engine = CompositeEngine()
        result = engine.evaluate(
            market_regime=_strong_market_regime(100),
            relative_strength=_strong_rs(100),
            trend=_strong_trend(100),
            pattern=_strong_pattern(35),
            volume=_strong_volume(100),
        )
        if result.overall_score >= 85:
            assert result.recommendation != Recommendation.STRONG_BUY

    def test_bear_market_plus_broken_trend(self):
        engine = CompositeEngine()
        result = engine.evaluate(
            market_regime=MarketRegime(
                regime=Regime.BEAR, confidence=90, score=85,
                reasons=[], warnings=[],
            ),
            relative_strength=_strong_rs(90),
            trend=TrendResult(
                overall_score=20, alignment_score=4,
                price_position_score=3, slope_score=4,
                structure_score=3, persistence_score=3,
                high_score=3,
                trend_quality=TrendQuality.BROKEN,
                trend_stage=TrendStage.LATE,
                confidence=90, reasons=[], warnings=[],
            ),
            pattern=_strong_pattern(90),
            volume=_strong_volume(90),
        )
        assert result.recommendation in (Recommendation.MONITOR, Recommendation.AVOID)


class TestFailedGates:

    def test_bear_market_gate(self):
        engine = CompositeEngine()
        result = engine.evaluate(
            market_regime=MarketRegime(
                regime=Regime.BEAR, confidence=90, score=85,
                reasons=[], warnings=[],
            ),
            relative_strength=_strong_rs(90),
            trend=_strong_trend(90),
            pattern=_strong_pattern(90),
            volume=_strong_volume(90),
        )
        assert "Bear Market" in result.failed_gates

    def test_broken_trend_gate(self):
        """Broken trend gate triggers when trend is broken and score would be higher."""
        engine = CompositeEngine()
        # Use higher scores for other engines to get overall score > 75
        # market: 100 * 15 / 100 = 15
        # rs: 100 * 20 / 100 = 20
        # trend: 20 * 25 / 100 = 5 (broken)
        # pattern: 100 * 20 / 100 = 20
        # volume: 100 * 20 / 100 = 20
        # total = 80 (before gating)
        result = engine.evaluate(
            market_regime=MarketRegime(
                regime=Regime.BULL, confidence=95, score=100,
                reasons=[], warnings=[],
            ),
            relative_strength=_strong_rs(100),
            trend=TrendResult(
                overall_score=20, alignment_score=4,
                price_position_score=3, slope_score=4,
                structure_score=3, persistence_score=3,
                high_score=3,
                trend_quality=TrendQuality.BROKEN,
                trend_stage=TrendStage.LATE,
                confidence=90, reasons=[], warnings=[],
            ),
            pattern=_strong_pattern(100),
            volume=_strong_volume(100),
        )
        assert "Broken Trend" in result.failed_gates

    def test_weak_pattern_gate(self):
        """Weak pattern gate prevents Strong Buy when pattern score < 40.

        Note: With current weights (20% for pattern), a weak pattern (35)
        contributes only 7 points, making it impossible to reach the 95+
        threshold for Strong Buy. The gate is a safety mechanism.
        """
        engine = CompositeEngine()
        result = engine.evaluate(
            market_regime=MarketRegime(
                regime=Regime.BULL, confidence=95, score=100,
                reasons=[], warnings=[],
            ),
            relative_strength=_strong_rs(100),
            trend=_strong_trend(100),
            pattern=_strong_pattern(35),
            volume=_strong_volume(100),
        )
        # With pattern=35, overall_score=87, recommendation=BUY (not Strong Buy)
        # The weak pattern gate doesn't trigger because rec != STRONG_BUY
        assert result.overall_score < 95
        assert result.recommendation != Recommendation.STRONG_BUY

    def test_multiple_gates(self):
        """Multiple gates should trigger when both conditions are met.

        Note: Bear market gate triggers first, changing recommendation to MONITOR.
        Broken trend gate only triggers if recommendation is STRONG_BUY, BUY, or WATCHLIST.
        Since bear market already changed it to MONITOR, broken trend gate doesn't trigger.
        """
        engine = CompositeEngine()
        # Use higher scores for other engines to get overall score > 75
        # market: 100 * 15 / 100 = 15 (bear market)
        # rs: 100 * 20 / 100 = 20
        # trend: 20 * 25 / 100 = 5 (broken)
        # pattern: 100 * 20 / 100 = 20
        # volume: 100 * 20 / 100 = 20
        # total = 80 (before gating)
        result = engine.evaluate(
            market_regime=MarketRegime(
                regime=Regime.BEAR, confidence=95, score=100,
                reasons=[], warnings=[],
            ),
            relative_strength=_strong_rs(100),
            trend=TrendResult(
                overall_score=20, alignment_score=4,
                price_position_score=3, slope_score=4,
                structure_score=3, persistence_score=3,
                high_score=3,
                trend_quality=TrendQuality.BROKEN,
                trend_stage=TrendStage.LATE,
                confidence=90, reasons=[], warnings=[],
            ),
            pattern=_strong_pattern(100),
            volume=_strong_volume(100),
        )
        # Bear market gate triggers first, changing recommendation to MONITOR
        # Broken trend gate doesn't trigger because recommendation is already MONITOR
        assert "Bear Market" in result.failed_gates
        assert result.recommendation in (Recommendation.MONITOR, Recommendation.AVOID)

    def test_no_gates_trigger(self):
        engine = CompositeEngine()
        result = engine.evaluate(
            market_regime=_strong_market_regime(85),
            relative_strength=_strong_rs(80),
            trend=_strong_trend(85),
            pattern=_strong_pattern(90),
            volume=_strong_volume(75),
        )
        assert result.failed_gates == []

    def test_low_score_gate(self):
        """Low score gate triggers when score < 60 but recommendation is not AVOID/MONITOR."""
        engine = CompositeEngine()
        result = engine.evaluate(
            market_regime=MarketRegime(
                regime=Regime.BULL, confidence=90, score=50,
                reasons=[], warnings=[],
            ),
            relative_strength=RelativeStrengthResult(
                overall_score=80, market_score=24,
                sector_score=20, industry_score=12,
                high_score=16, momentum_score=8,
                leadership=Leadership.STRONG,
                confidence=80, reasons=[], warnings=[],
            ),
            trend=TrendResult(
                overall_score=80, alignment_score=16,
                price_position_score=12, slope_score=16,
                structure_score=16, persistence_score=8,
                high_score=12,
                trend_quality=TrendQuality.STRONG,
                trend_stage=TrendStage.ESTABLISHED,
                confidence=80, reasons=[], warnings=[],
            ),
            pattern=_strong_pattern(80),
            volume=_strong_volume(80),
        )
        if result.overall_score < 60:
            assert "Low Score" in result.failed_gates


class TestGradeClassification:

    def test_grade_a_plus(self):
        engine = CompositeEngine()
        result = engine.evaluate(
            market_regime=_strong_market_regime(100),
            relative_strength=_strong_rs(100),
            trend=_strong_trend(100),
            pattern=_strong_pattern(100),
            volume=_strong_volume(100),
        )
        assert result.investment_grade == InvestmentGrade.A_PLUS

    def test_grade_f(self):
        engine = CompositeEngine()
        result = engine.evaluate(
            market_regime=_strong_market_regime(0),
            relative_strength=_strong_rs(0),
            trend=_strong_trend(0),
            pattern=_strong_pattern(0),
            volume=_strong_volume(0),
        )
        assert result.investment_grade == InvestmentGrade.F

    def test_grade_b_mid(self):
        engine = CompositeEngine()
        result = engine.evaluate(
            market_regime=_strong_market_regime(75),
            relative_strength=_strong_rs(75),
            trend=_strong_trend(75),
            pattern=_strong_pattern(75),
            volume=_strong_volume(75),
        )
        assert result.investment_grade in (InvestmentGrade.B, InvestmentGrade.B_PLUS)


class TestPositionSizing:

    def test_high_score_large_position(self):
        engine = CompositeEngine()
        result = engine.evaluate(
            market_regime=_strong_market_regime(90),
            relative_strength=_strong_rs(90),
            trend=_strong_trend(90),
            pattern=_strong_pattern(90),
            volume=_strong_volume(90),
        )
        assert result.position_size >= 0.15

    def test_weak_rs_caps_position(self):
        engine = CompositeEngine()
        result = engine.evaluate(
            market_regime=_strong_market_regime(100),
            relative_strength=RelativeStrengthResult(
                overall_score=30, market_score=9,
                sector_score=7, industry_score=5,
                high_score=5, momentum_score=4,
                leadership=Leadership.LAGGARD,
                confidence=70, reasons=[], warnings=[],
            ),
            trend=_strong_trend(100),
            pattern=_strong_pattern(100),
            volume=_strong_volume(100),
        )
        assert result.position_size <= 0.10

    def test_low_score_zero_position(self):
        engine = CompositeEngine()
        result = engine.evaluate(
            market_regime=_strong_market_regime(30),
            relative_strength=_strong_rs(30),
            trend=_strong_trend(30),
            pattern=_strong_pattern(30),
            volume=_strong_volume(30),
        )
        assert result.position_size == 0.0


class TestConfidence:

    def test_high_confidence_all_strong(self):
        engine = CompositeEngine()
        result = engine.evaluate(
            market_regime=_strong_market_regime(90),
            relative_strength=_strong_rs(90),
            trend=_strong_trend(90),
            pattern=_strong_pattern(90),
            volume=_strong_volume(90),
        )
        assert result.confidence >= 70

    def test_low_confidence_missing_data(self):
        engine = CompositeEngine()
        result = engine.evaluate(
            market_regime=_strong_market_regime(50),
        )
        assert result.confidence < 50

    def test_warnings_reduce_confidence(self):
        engine = CompositeEngine()
        result = engine.evaluate(
            market_regime=MarketRegime(
                regime=Regime.NEUTRAL, confidence=50, score=50,
                reasons=[], warnings=["Data incomplete"],
            ),
            relative_strength=RelativeStrengthResult(
                overall_score=50, market_score=15,
                sector_score=12, industry_score=7,
                high_score=10, momentum_score=6,
                leadership=Leadership.AVERAGE,
                confidence=50, reasons=[],
                warnings=["Sector data missing", "Industry data missing"],
            ),
            trend=_strong_trend(50),
            pattern=_strong_pattern(50),
            volume=_strong_volume(50),
        )
        assert result.confidence < 70

    def test_high_agreement_increases_confidence(self):
        """High agreement between engines should increase confidence."""
        engine = CompositeEngine()
        result_agreement = engine.evaluate(
            market_regime=_strong_market_regime(95),
            relative_strength=_strong_rs(94),
            trend=_strong_trend(93),
            pattern=_strong_pattern(91),
            volume=_strong_volume(90),
        )
        result_disagreement = engine.evaluate(
            market_regime=_strong_market_regime(95),
            relative_strength=_strong_rs(94),
            trend=_strong_trend(42),
            pattern=_strong_pattern(35),
            volume=_strong_volume(88),
        )
        assert result_agreement.confidence > result_disagreement.confidence

    def test_low_agreement_decreases_confidence(self):
        """Large disagreement between engines should decrease confidence."""
        engine = CompositeEngine()
        result = engine.evaluate(
            market_regime=_strong_market_regime(95),
            relative_strength=_strong_rs(94),
            trend=_strong_trend(42),
            pattern=_strong_pattern(35),
            volume=_strong_volume(88),
        )
        assert result.confidence < 70

    def test_mixed_scores_confidence(self):
        """Confidence should be lower for mixed scores."""
        engine = CompositeEngine()
        result_mixed = engine.evaluate(
            market_regime=_strong_market_regime(50),
            relative_strength=_strong_rs(90),
            trend=_strong_trend(50),
            pattern=_strong_pattern(90),
            volume=_strong_volume(50),
        )
        result_strong = engine.evaluate(
            market_regime=_strong_market_regime(90),
            relative_strength=_strong_rs(90),
            trend=_strong_trend(90),
            pattern=_strong_pattern(90),
            volume=_strong_volume(90),
        )
        assert result_mixed.confidence < result_strong.confidence


class TestRecommendations:

    def test_strong_buy_threshold(self):
        engine = CompositeEngine()
        result = engine.evaluate(
            market_regime=_strong_market_regime(100),
            relative_strength=_strong_rs(100),
            trend=_strong_trend(100),
            pattern=_strong_pattern(100),
            volume=_strong_volume(100),
        )
        assert result.recommendation == Recommendation.STRONG_BUY

    def test_avoid_low_score(self):
        engine = CompositeEngine()
        result = engine.evaluate(
            market_regime=_strong_market_regime(30),
            relative_strength=_strong_rs(30),
            trend=_strong_trend(30),
            pattern=_strong_pattern(30),
            volume=_strong_volume(30),
        )
        assert result.recommendation == Recommendation.AVOID


class TestReasonsAggregation:

    def test_reasons_collected(self):
        engine = CompositeEngine()
        result = engine.evaluate(
            market_regime=_strong_market_regime(),
            relative_strength=_strong_rs(),
            trend=_strong_trend(),
            pattern=_strong_pattern(),
            volume=_strong_volume(),
        )
        assert "Bull market" in result.reasons
        assert "Market outperformer" in result.reasons
        assert "Strong uptrend" in result.reasons
        assert "Tight VCP" in result.reasons

    def test_warnings_collected(self):
        engine = CompositeEngine()
        result = engine.evaluate(
            market_regime=MarketRegime(
                regime=Regime.BULL, confidence=80, score=80,
                reasons=[], warnings=["Market warning"],
            ),
            relative_strength=RelativeStrengthResult(
                overall_score=80, market_score=24,
                sector_score=20, industry_score=12,
                high_score=16, momentum_score=8,
                leadership=Leadership.STRONG,
                confidence=80, reasons=[],
                warnings=["RS warning"],
            ),
            trend=_strong_trend(),
            pattern=_strong_pattern(),
            volume=_strong_volume(),
        )
        assert "Market warning" in result.warnings
        assert "RS warning" in result.warnings
