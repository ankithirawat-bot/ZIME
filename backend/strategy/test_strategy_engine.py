"""
Tests for Strategy Infrastructure.

Validates pipeline execution, registry resolution, momentum strategy,
validation, unknown strategy, decision trace, evaluation context,
and regression.
"""

from __future__ import annotations

import pytest

from backend.composite.models import CompositeResult, InvestmentGrade, Recommendation
from backend.patterns.models import PatternResult, PatternSnapshot, PatternType
from backend.regime.models import (
    BreadthData,
    IndexData,
    MarketRegime,
    MarketSnapshot,
    Regime,
)
from backend.relative_strength.models import (
    BenchmarkData,
    Leadership,
    RelativeStrengthResult,
    StockSnapshot,
)
from backend.risk.models import RejectionReason, RiskManagementResult
from backend.strategy.models import (
    EvaluationContext,
    StrategyConfiguration,
    StrategyDecisionTrace,
    StrategyInput,
    StrategyResult,
    StrategySummary,
    StrategyType,
)
from backend.strategy.pipeline import EvaluationPipeline
from backend.strategy.strategies import (
    BreakoutStrategy,
    CustomStrategy,
    GrowthStrategy,
    MomentumStrategy,
    QualityStrategy,
    Strategy,
    TrendFollowingStrategy,
)
from backend.strategy.strategy_engine import StrategyEngine
from backend.strategy.strategy_registry import StrategyRegistry
from backend.trade.models import EntryType, ExecutionStatus, TradePlan, TradeQuality
from backend.trend.models import TrendQuality, TrendResult, TrendSnapshot, TrendStage
from backend.volume.models import VolumeQuality, VolumeResult, VolumeSnapshot

# ---------------------------------------------------------------------------
# Snapshot Helpers
# ---------------------------------------------------------------------------


def _bull_market_snapshot() -> MarketSnapshot:
    return MarketSnapshot(
        nifty50=IndexData(
            name="NIFTY50",
            current_price=22000.0,
            ema20=21800.0,
            ema50=21500.0,
            sma200=20000.0,
            rsi14=62.0,
            macd_bullish=True,
        ),
        nifty_midcap=IndexData(
            name="NIFTY_MIDCAP",
            current_price=45000.0,
            ema20=44500.0,
            ema50=44000.0,
            sma200=42000.0,
        ),
        nifty_smallcap=IndexData(
            name="NIFTY_SMALLCAP",
            current_price=15000.0,
            ema20=14800.0,
            ema50=14500.0,
            sma200=13000.0,
        ),
        breadth=BreadthData(
            percent_above_50dma=68.0,
            percent_above_200dma=58.0,
        ),
        india_vix=13.0,
    )


def _bear_market_snapshot() -> MarketSnapshot:
    return MarketSnapshot(
        nifty50=IndexData(
            name="NIFTY50",
            current_price=18000.0,
            ema20=18500.0,
            ema50=19000.0,
            sma200=20000.0,
            rsi14=35.0,
            macd_bullish=False,
        ),
        nifty_midcap=IndexData(
            name="NIFTY_MIDCAP",
            current_price=35000.0,
            ema20=36000.0,
            ema50=37000.0,
            sma200=38000.0,
        ),
        nifty_smallcap=IndexData(
            name="NIFTY_SMALLCAP",
            current_price=10000.0,
            ema20=10500.0,
            ema50=11000.0,
            sma200=12000.0,
        ),
        breadth=BreadthData(
            percent_above_50dma=25.0,
            percent_above_200dma=18.0,
        ),
        india_vix=28.0,
    )


def _strong_rs_snapshot() -> StockSnapshot:
    return StockSnapshot(
        symbol="RELIANCE",
        stock=BenchmarkData(
            name="RELIANCE",
            returns_1m=8.0,
            returns_3m=18.0,
            returns_6m=35.0,
            returns_1y=55.0,
        ),
        market_benchmark=BenchmarkData(
            name="NIFTY50",
            returns_1m=3.0,
            returns_3m=8.0,
            returns_6m=15.0,
            returns_1y=20.0,
        ),
        sector_benchmark=BenchmarkData(
            name="ENERGY",
            returns_1m=5.0,
            returns_3m=12.0,
            returns_6m=22.0,
            returns_1y=30.0,
        ),
        industry_benchmark=BenchmarkData(
            name="OIL_GAS",
            returns_1m=6.0,
            returns_3m=14.0,
            returns_6m=25.0,
            returns_1y=35.0,
        ),
        high_52w=2600.0,
        low_52w=2000.0,
        current_price=2550.0,
        history_length=252,
    )


def _trend_snapshot() -> TrendSnapshot:
    return TrendSnapshot(
        current_price=2550.0,
        ema20=2520.0,
        ema50=2450.0,
        sma150=2350.0,
        sma200=2250.0,
        high_52w=2600.0,
        low_52w=2000.0,
        slope_ema20=0.6,
        slope_ema50=0.4,
        slope_sma150=0.25,
        slope_sma200=0.15,
        higher_high_count=6,
        higher_low_count=5,
        trend_age=80,
        history_length=252,
    )


def _pattern_snapshot() -> PatternSnapshot:
    return PatternSnapshot(
        price=2550.0,
        volume=1_800_000.0,
        highs=[2400, 2450, 2500, 2550],
        lows=[2350, 2400, 2450, 2500],
        closes=[2380, 2430, 2500, 2550],
        pivot_price=2550.0,
        high_52w=2600.0,
        volatility=0.15,
        atr=40.0,
        contraction_count=4,
        volume_dryup=0.5,
        breakout_volume_ratio=2.5,
        trend_quality=85.0,
        relative_strength=80.0,
    )


def _volume_snapshot() -> VolumeSnapshot:
    return VolumeSnapshot(
        price=2550.0,
        volume=1_800_000.0,
        avg_volume_20=1_000_000.0,
        avg_volume_50=900_000.0,
        breakout_volume=2_500_000.0,
        consolidation_volume=500_000.0,
        rvol=1.8,
        accumulation_days=10,
        distribution_days=1,
        close_position_percent=80.0,
        trend_quality=85.0,
        atr=40.0,
    )


def _strategy_input(
    market: MarketSnapshot | None = None,
    rs: StockSnapshot | None = None,
    trend: TrendSnapshot | None = None,
    pattern: PatternSnapshot | None = None,
    volume: VolumeSnapshot | None = None,
    strategy_type: StrategyType = StrategyType.MOMENTUM,
    min_composite: float = 60.0,
    min_confidence: float = 60.0,
    allow_bear: bool = False,
    allow_extended: bool = True,
) -> StrategyInput:
    return StrategyInput(
        symbol="RELIANCE",
        market_snapshot=market or _bull_market_snapshot(),
        relative_strength_snapshot=rs or _strong_rs_snapshot(),
        trend_snapshot=trend or _trend_snapshot(),
        pattern_snapshot=pattern or _pattern_snapshot(),
        volume_snapshot=volume or _volume_snapshot(),
        configuration=StrategyConfiguration(
            strategy_type=strategy_type,
            minimum_composite_score=min_composite,
            minimum_confidence=min_confidence,
            allow_bear_market=allow_bear,
            allow_extended_trend=allow_extended,
        ),
    )


# ---------------------------------------------------------------------------
# Engine-Result Mock Helpers (for unit tests that bypass pipeline)
# ---------------------------------------------------------------------------


def _mock_evaluation_context(
    composite_score: float = 75.0,
    composite_confidence: float = 72.0,
    recommendation: Recommendation = Recommendation.BUY,
    market_regime: Regime = Regime.BULL,
    trend_stage: TrendStage = TrendStage.ESTABLISHED,
    execution_allowed: bool = True,
    rejection_reason: RejectionReason = RejectionReason.NONE,
) -> EvaluationContext:
    return EvaluationContext(
        market_result=MarketRegime(
            regime=market_regime,
            confidence=80.0,
            score=75.0,
            reasons=["Bull market"],
            warnings=[],
        ),
        relative_strength_result=RelativeStrengthResult(
            overall_score=70.0,
            market_score=75.0,
            sector_score=70.0,
            industry_score=65.0,
            high_score=80.0,
            momentum_score=75.0,
            leadership=Leadership.LEADER,
            confidence=75.0,
            reasons=["Strong RS"],
            warnings=[],
        ),
        trend_result=TrendResult(
            overall_score=80.0,
            alignment_score=85.0,
            price_position_score=75.0,
            slope_score=80.0,
            structure_score=75.0,
            persistence_score=80.0,
            high_score=85.0,
            trend_quality=TrendQuality.STRONG,
            trend_stage=trend_stage,
            confidence=80.0,
            reasons=["Strong trend"],
            warnings=[],
        ),
        pattern_result=PatternResult(
            pattern_name=PatternType.VCP,
            score=65.0,
            confidence=70.0,
            reasons=["VCP detected"],
            warnings=[],
        ),
        volume_result=VolumeResult(
            overall_score=70.0,
            rvol_score=75.0,
            breakout_score=70.0,
            dryup_score=65.0,
            accumulation_score=70.0,
            distribution_score=60.0,
            institutional_score=70.0,
            volume_quality=VolumeQuality.STRONG,
            confidence=72.0,
            reasons=["Good volume"],
            warnings=[],
        ),
        composite_result=CompositeResult(
            overall_score=composite_score,
            market_score=80.0,
            relative_strength_score=70.0,
            trend_score=80.0,
            pattern_score=65.0,
            volume_score=70.0,
            investment_grade=InvestmentGrade.B,
            recommendation=recommendation,
            confidence=composite_confidence,
            position_size=15.0,
            reasons=["Strong composite"],
            warnings=[],
            decision_trace=None,  # type: ignore[arg-type]
            failed_gates=[],
        ),
        trade_result=TradePlan(
            entry_price=2500.0,
            entry_type=EntryType.BREAKOUT,
            stop_loss=2400.0,
            stop_distance=100.0,
            risk_percent=4.0,
            target_1=2700.0,
            target_2=2900.0,
            target_3=3100.0,
            risk_reward_ratio=2.0,
            position_size=15_000.0,
            trade_quality=TradeQuality.A,
            execution_status=ExecutionStatus.READY,
            execution_checklist=["Stop defined", "Volume confirms"],
            confidence=75.0,
            reasons=["Strong setup"],
            warnings=[],
            decision_trace=None,  # type: ignore[arg-type]
            validation_flags=["VALID_ENTRY", "VALID_STOP"],
        ),
        risk_result=RiskManagementResult(
            max_risk_percent=1.0,
            recommended_position_size=15_000.0,
            capital_at_risk=150.0,
            risk_per_share=1.0,
            maximum_loss=150.0,
            shares_to_buy=60,
            portfolio_exposure=15.0,
            exposure_status="Normal",
            trade_risk_grade="Low",
            portfolio_risk_grade="Low",
            execution_allowed=execution_allowed,
            rejection_reason=rejection_reason,
            decision_trace=None,  # type: ignore[arg-type]
            validation_flags=["VALID_RISK"],
            confidence=80.0,
            reasons=["Risk acceptable"],
            warnings=[],
        ),
    )


# ---------------------------------------------------------------------------
# Tests: Strategy ABC
# ---------------------------------------------------------------------------


class TestStrategyABC:

    def test_cannot_instantiate(self):
        """Strategy ABC cannot be instantiated directly."""
        with pytest.raises(TypeError):
            Strategy()  # type: ignore[abstract]

    def test_momentum_strategy_type(self):
        """MomentumStrategy declares MOMENTUM type."""
        strategy = MomentumStrategy()
        assert strategy.strategy_type == StrategyType.MOMENTUM


# ---------------------------------------------------------------------------
# Tests: Models
# ---------------------------------------------------------------------------


class TestModels:

    def test_strategy_type_enum(self):
        """StrategyType should have all required types."""
        assert StrategyType.MOMENTUM.value == "Momentum"
        assert StrategyType.BREAKOUT.value == "Breakout"
        assert StrategyType.TREND_FOLLOWING.value == "Trend Following"
        assert StrategyType.GROWTH.value == "Growth"
        assert StrategyType.QUALITY.value == "Quality"
        assert StrategyType.CUSTOM.value == "Custom"

    def test_configuration_defaults(self):
        """StrategyConfiguration should have sensible defaults."""
        config = StrategyConfiguration(strategy_type=StrategyType.MOMENTUM)
        assert config.minimum_composite_score == 60.0
        assert config.minimum_confidence == 60.0
        assert config.allow_bear_market is False
        assert config.allow_extended_trend is True
        assert config.minimum_pattern_score == 0.0
        assert config.minimum_volume_score == 0.0
        assert config.minimum_trend_score == 0.0
        assert config.minimum_rs_score == 0.0
        assert config.require_strong_trend is False
        assert config.require_strong_pattern is False
        assert config.ignore_pattern is False

    def test_configuration_custom(self):
        """StrategyConfiguration should accept custom values."""
        config = StrategyConfiguration(
            strategy_type=StrategyType.MOMENTUM,
            minimum_composite_score=80.0,
            minimum_confidence=90.0,
            allow_bear_market=True,
            allow_extended_trend=False,
        )
        assert config.minimum_composite_score == 80.0
        assert config.allow_bear_market is True

    def test_summary_fields(self):
        """StrategySummary should be frozen."""
        summary = StrategySummary(
            strategy_type=StrategyType.MOMENTUM,
            overall_score=75.0,
            confidence=72.0,
            approved=True,
            approval_reason="Test",
        )
        assert summary.approved is True
        with pytest.raises(AttributeError):
            summary.approved = False  # type: ignore[misc]

    def test_decision_trace_fields(self):
        """StrategyDecisionTrace should be frozen."""
        trace = StrategyDecisionTrace(
            pipeline_source="pipeline",
            strategy_source="MomentumStrategy",
            approval_source="strategy.evaluate",
        )
        assert trace.pipeline_source == "pipeline"
        assert trace.strategy_source == "MomentumStrategy"

    def test_result_fields(self):
        """StrategyResult should be frozen."""
        ctx = _mock_evaluation_context()
        summary = StrategySummary(
            strategy_type=StrategyType.MOMENTUM,
            overall_score=75.0,
            confidence=72.0,
            approved=True,
            approval_reason="Strong setup",
        )
        result = StrategyResult(
            summary=summary,
            context=ctx,
            decision_trace=StrategyDecisionTrace(
                pipeline_source="pipeline",
                strategy_source="MomentumStrategy",
                approval_source="strategy.evaluate",
            ),
            validation_flags=("VALID",),
            reasons=("Strong setup",),
            warnings=(),
        )
        assert result.summary.approved is True
        assert len(result.reasons) == 1
        assert result.validation_flags == ("VALID",)

    def test_result_defaults(self):
        """StrategyResult should have default empty tuples."""
        ctx = _mock_evaluation_context()
        summary = StrategySummary(
            strategy_type=StrategyType.MOMENTUM,
            overall_score=75.0,
            confidence=72.0,
            approved=True,
            approval_reason="Test",
        )
        result = StrategyResult(
            summary=summary,
            context=ctx,
            decision_trace=StrategyDecisionTrace(
                pipeline_source="p",
                strategy_source="s",
                approval_source="a",
            ),
        )
        assert result.validation_flags == ()
        assert result.reasons == ()
        assert result.warnings == ()


# ---------------------------------------------------------------------------
# Tests: Registry
# ---------------------------------------------------------------------------


class TestRegistry:

    def test_register_and_resolve(self):
        """Registry should resolve registered strategies."""
        registry = StrategyRegistry()
        strategy = MomentumStrategy()
        registry.register(StrategyType.MOMENTUM, strategy)
        assert registry.resolve(StrategyType.MOMENTUM) is strategy

    def test_resolve_unknown(self):
        """Registry should return None for unknown strategy."""
        registry = StrategyRegistry()
        assert registry.resolve(StrategyType.MOMENTUM) is None

    def test_has(self):
        """Registry should report registered strategies."""
        registry = StrategyRegistry()
        assert registry.has(StrategyType.MOMENTUM) is False
        registry.register(StrategyType.MOMENTUM, MomentumStrategy())
        assert registry.has(StrategyType.MOMENTUM) is True

    def test_has_not_registered(self):
        """Registry should return False for unregistered types."""
        registry = StrategyRegistry()
        assert registry.has(StrategyType.MOMENTUM) is False

    def test_registered_types(self):
        """Registry should return registered types."""
        registry = StrategyRegistry()
        registry.register(StrategyType.MOMENTUM, MomentumStrategy())
        types = registry.registered_types()
        assert StrategyType.MOMENTUM in types

    def test_registered_types_empty(self):
        """Registry should return empty tuple when empty."""
        registry = StrategyRegistry()
        assert registry.registered_types() == ()

    def test_overwrite_registration(self):
        """Registry should allow overwriting registration."""
        registry = StrategyRegistry()
        s1 = MomentumStrategy()
        s2 = MomentumStrategy()
        registry.register(StrategyType.MOMENTUM, s1)
        registry.register(StrategyType.MOMENTUM, s2)
        assert registry.resolve(StrategyType.MOMENTUM) is s2

    def test_all_strategy_types_registered(self):
        """Engine should register all built-in strategies."""
        engine = StrategyEngine()
        for st in StrategyType:
            assert engine._registry.has(st), f"{st} not registered"


# ---------------------------------------------------------------------------
# Tests: Pipeline
# ---------------------------------------------------------------------------


class TestPipeline:

    def test_pipeline_returns_context(self):
        """Pipeline should return EvaluationContext."""
        pipeline = EvaluationPipeline()
        ctx = pipeline.run(_strategy_input())
        assert isinstance(ctx, EvaluationContext)

    def test_pipeline_market_result(self):
        """Pipeline should produce market result."""
        pipeline = EvaluationPipeline()
        ctx = pipeline.run(_strategy_input())
        assert ctx.market_result is not None
        assert ctx.market_result.regime is not None

    def test_pipeline_rs_result(self):
        """Pipeline should produce RS result."""
        pipeline = EvaluationPipeline()
        ctx = pipeline.run(_strategy_input())
        assert 0 <= ctx.relative_strength_result.overall_score <= 100

    def test_pipeline_trend_result(self):
        """Pipeline should produce trend result."""
        pipeline = EvaluationPipeline()
        ctx = pipeline.run(_strategy_input())
        assert ctx.trend_result.trend_quality is not None

    def test_pipeline_pattern_result(self):
        """Pipeline should produce pattern result."""
        pipeline = EvaluationPipeline()
        ctx = pipeline.run(_strategy_input())
        assert ctx.pattern_result.pattern_name is not None

    def test_pipeline_volume_result(self):
        """Pipeline should produce volume result."""
        pipeline = EvaluationPipeline()
        ctx = pipeline.run(_strategy_input())
        assert ctx.volume_result.volume_quality is not None

    def test_pipeline_composite_result(self):
        """Pipeline should produce composite result."""
        pipeline = EvaluationPipeline()
        ctx = pipeline.run(_strategy_input())
        assert 0 <= ctx.composite_result.overall_score <= 100

    def test_pipeline_trade_result(self):
        """Pipeline should produce trade result."""
        pipeline = EvaluationPipeline()
        ctx = pipeline.run(_strategy_input())
        assert ctx.trade_result is not None

    def test_pipeline_risk_result(self):
        """Pipeline should produce risk result."""
        pipeline = EvaluationPipeline()
        ctx = pipeline.run(_strategy_input())
        assert ctx.risk_result is not None

    def test_pipeline_is_deterministic(self):
        """Pipeline should be deterministic."""
        pipeline = EvaluationPipeline()
        ctx1 = pipeline.run(_strategy_input())
        ctx2 = pipeline.run(_strategy_input())
        assert ctx1.composite_result.overall_score == ctx2.composite_result.overall_score

    def test_pipeline_bear_market(self):
        """Pipeline should handle bear market input."""
        pipeline = EvaluationPipeline()
        ctx = pipeline.run(_strategy_input(market=_bear_market_snapshot()))
        assert ctx.market_result.regime == Regime.BEAR

    def test_pipeline_context_immutable(self):
        """Pipeline context should be frozen."""
        pipeline = EvaluationPipeline()
        ctx = pipeline.run(_strategy_input())
        with pytest.raises(AttributeError):
            ctx.market_result = None  # type: ignore[misc]


# ---------------------------------------------------------------------------
# Tests: MomentumStrategy (unit tests using mock context)
# ---------------------------------------------------------------------------


class TestMomentumStrategy:

    def test_approves_strong_setup(self):
        """MomentumStrategy should approve when all criteria met."""
        strategy = MomentumStrategy()
        ctx = _mock_evaluation_context()
        config = StrategyConfiguration(strategy_type=StrategyType.MOMENTUM)
        result = strategy.evaluate(ctx, config)
        assert result.summary.approved is True
        assert result.summary.strategy_type == StrategyType.MOMENTUM
        assert "APPROVED" in result.validation_flags

    def test_rejects_low_composite_score(self):
        """MomentumStrategy should reject low composite score."""
        strategy = MomentumStrategy()
        ctx = _mock_evaluation_context(composite_score=50.0)
        config = StrategyConfiguration(
            strategy_type=StrategyType.MOMENTUM,
            minimum_composite_score=60.0,
        )
        result = strategy.evaluate(ctx, config)
        assert result.summary.approved is False
        assert "below" in result.summary.approval_reason.lower()

    def test_rejects_low_confidence(self):
        """MomentumStrategy should reject low confidence."""
        strategy = MomentumStrategy()
        ctx = _mock_evaluation_context(composite_confidence=40.0)
        config = StrategyConfiguration(
            strategy_type=StrategyType.MOMENTUM,
            minimum_confidence=60.0,
        )
        result = strategy.evaluate(ctx, config)
        assert result.summary.approved is False
        assert "confidence" in result.summary.approval_reason.lower()

    def test_rejects_bear_market_by_default(self):
        """MomentumStrategy should reject bear market by default."""
        strategy = MomentumStrategy()
        ctx = _mock_evaluation_context(market_regime=Regime.BEAR)
        config = StrategyConfiguration(
            strategy_type=StrategyType.MOMENTUM,
            allow_bear_market=False,
        )
        result = strategy.evaluate(ctx, config)
        assert result.summary.approved is False
        assert "bear" in result.summary.approval_reason.lower()

    def test_allows_bear_market_when_configured(self):
        """MomentumStrategy should allow bear market when configured."""
        strategy = MomentumStrategy()
        ctx = _mock_evaluation_context(market_regime=Regime.BEAR)
        config = StrategyConfiguration(
            strategy_type=StrategyType.MOMENTUM,
            allow_bear_market=True,
            minimum_composite_score=0,
            minimum_confidence=0,
        )
        result = strategy.evaluate(ctx, config)
        assert result.summary.approved is True

    def test_rejects_risk_rejection(self):
        """MomentumStrategy should reject when risk rejects."""
        strategy = MomentumStrategy()
        ctx = _mock_evaluation_context(
            execution_allowed=False,
            rejection_reason=RejectionReason.HIGH_EXPOSURE,
        )
        config = StrategyConfiguration(strategy_type=StrategyType.MOMENTUM)
        result = strategy.evaluate(ctx, config)
        assert result.summary.approved is False
        assert "risk" in result.summary.approval_reason.lower()

    def test_rejects_avoid_recommendation(self):
        """MomentumStrategy should reject Avoid recommendation."""
        strategy = MomentumStrategy()
        ctx = _mock_evaluation_context(recommendation=Recommendation.AVOID)
        config = StrategyConfiguration(strategy_type=StrategyType.MOMENTUM)
        result = strategy.evaluate(ctx, config)
        assert result.summary.approved is False
        assert "avoid" in result.summary.approval_reason.lower()

    def test_overall_score_from_composite(self):
        """MomentumStrategy overall score should match composite."""
        strategy = MomentumStrategy()
        ctx = _mock_evaluation_context(composite_score=82.5)
        config = StrategyConfiguration(strategy_type=StrategyType.MOMENTUM)
        result = strategy.evaluate(ctx, config)
        assert result.summary.overall_score == 82.5

    def test_confidence_from_composite(self):
        """MomentumStrategy confidence should match composite."""
        strategy = MomentumStrategy()
        ctx = _mock_evaluation_context(composite_confidence=85.0)
        config = StrategyConfiguration(strategy_type=StrategyType.MOMENTUM)
        result = strategy.evaluate(ctx, config)
        assert result.summary.confidence == 85.0

    def test_reasons_populated(self):
        """MomentumStrategy should collect reasons from engines."""
        strategy = MomentumStrategy()
        ctx = _mock_evaluation_context()
        config = StrategyConfiguration(strategy_type=StrategyType.MOMENTUM)
        result = strategy.evaluate(ctx, config)
        assert len(result.reasons) > 0

    def test_validation_flags_present(self):
        """MomentumStrategy should produce validation flags."""
        strategy = MomentumStrategy()
        ctx = _mock_evaluation_context()
        config = StrategyConfiguration(strategy_type=StrategyType.MOMENTUM)
        result = strategy.evaluate(ctx, config)
        assert "VALID_STRATEGY_INPUT" in result.validation_flags

    def test_rejected_flag_set(self):
        """MomentumStrategy should set REJECTED flag when rejected."""
        strategy = MomentumStrategy()
        ctx = _mock_evaluation_context(composite_score=30.0)
        config = StrategyConfiguration(
            strategy_type=StrategyType.MOMENTUM,
            minimum_composite_score=60.0,
        )
        result = strategy.evaluate(ctx, config)
        assert "REJECTED" in result.validation_flags

    def test_is_deterministic(self):
        """MomentumStrategy should be deterministic."""
        strategy = MomentumStrategy()
        ctx = _mock_evaluation_context()
        config = StrategyConfiguration(strategy_type=StrategyType.MOMENTUM)
        r1 = strategy.evaluate(ctx, config)
        r2 = strategy.evaluate(ctx, config)
        assert r1.summary.overall_score == r2.summary.overall_score
        assert r1.summary.approved == r2.summary.approved

    def test_context_preserved(self):
        """MomentumStrategy should preserve context in result."""
        strategy = MomentumStrategy()
        ctx = _mock_evaluation_context()
        config = StrategyConfiguration(strategy_type=StrategyType.MOMENTUM)
        result = strategy.evaluate(ctx, config)
        assert result.context is ctx

    def test_reasons_capped_at_20(self):
        """MomentumStrategy should cap reasons at 20."""
        strategy = MomentumStrategy()
        ctx = _mock_evaluation_context()
        config = StrategyConfiguration(strategy_type=StrategyType.MOMENTUM)
        result = strategy.evaluate(ctx, config)
        assert len(result.reasons) <= 20

    def test_warnings_capped_at_20(self):
        """MomentumStrategy should cap warnings at 20."""
        strategy = MomentumStrategy()
        ctx = _mock_evaluation_context()
        config = StrategyConfiguration(strategy_type=StrategyType.MOMENTUM)
        result = strategy.evaluate(ctx, config)
        assert len(result.warnings) <= 20


# ---------------------------------------------------------------------------
# Tests: BreakoutStrategy
# ---------------------------------------------------------------------------


class TestBreakoutStrategy:

    def test_approves_strong_setup(self):
        """BreakoutStrategy should approve when all criteria met."""
        strategy = BreakoutStrategy()
        ctx = _mock_evaluation_context()
        config = StrategyConfiguration(
            strategy_type=StrategyType.BREAKOUT,
            minimum_pattern_score=50.0,
            minimum_volume_score=50.0,
        )
        result = strategy.evaluate(ctx, config)
        assert result.summary.approved is True
        assert result.summary.strategy_type == StrategyType.BREAKOUT

    def test_rejects_low_pattern_score(self):
        """BreakoutStrategy should reject low pattern score."""
        strategy = BreakoutStrategy()
        ctx = _mock_evaluation_context()
        config = StrategyConfiguration(
            strategy_type=StrategyType.BREAKOUT,
            minimum_pattern_score=80.0,
        )
        result = strategy.evaluate(ctx, config)
        assert result.summary.approved is False
        assert "pattern" in result.summary.approval_reason.lower()

    def test_rejects_low_volume_score(self):
        """BreakoutStrategy should reject low volume score."""
        strategy = BreakoutStrategy()
        ctx = _mock_evaluation_context()
        config = StrategyConfiguration(
            strategy_type=StrategyType.BREAKOUT,
            minimum_volume_score=90.0,
        )
        result = strategy.evaluate(ctx, config)
        assert result.summary.approved is False
        assert "volume" in result.summary.approval_reason.lower()

    def test_rejects_low_composite(self):
        """BreakoutStrategy should reject low composite score."""
        strategy = BreakoutStrategy()
        ctx = _mock_evaluation_context(composite_score=40.0)
        config = StrategyConfiguration(
            strategy_type=StrategyType.BREAKOUT,
            minimum_composite_score=60.0,
        )
        result = strategy.evaluate(ctx, config)
        assert result.summary.approved is False

    def test_rejects_bear_market(self):
        """BreakoutStrategy should reject bear market by default."""
        strategy = BreakoutStrategy()
        ctx = _mock_evaluation_context(market_regime=Regime.BEAR)
        config = StrategyConfiguration(strategy_type=StrategyType.BREAKOUT)
        result = strategy.evaluate(ctx, config)
        assert result.summary.approved is False
        assert "bear" in result.summary.approval_reason.lower()

    def test_is_deterministic(self):
        """BreakoutStrategy should be deterministic."""
        strategy = BreakoutStrategy()
        ctx = _mock_evaluation_context()
        config = StrategyConfiguration(strategy_type=StrategyType.BREAKOUT)
        r1 = strategy.evaluate(ctx, config)
        r2 = strategy.evaluate(ctx, config)
        assert r1.summary.overall_score == r2.summary.overall_score
        assert r1.summary.approved == r2.summary.approved

    def test_context_preserved(self):
        """BreakoutStrategy should preserve context."""
        strategy = BreakoutStrategy()
        ctx = _mock_evaluation_context()
        config = StrategyConfiguration(strategy_type=StrategyType.BREAKOUT)
        result = strategy.evaluate(ctx, config)
        assert result.context is ctx

    def test_zero_threshold_skips_gate(self):
        """BreakoutStrategy should skip gate when threshold is 0."""
        strategy = BreakoutStrategy()
        ctx = _mock_evaluation_context()
        config = StrategyConfiguration(
            strategy_type=StrategyType.BREAKOUT,
            minimum_pattern_score=0.0,
            minimum_volume_score=0.0,
        )
        result = strategy.evaluate(ctx, config)
        assert result.summary.approved is True


# ---------------------------------------------------------------------------
# Tests: TrendFollowingStrategy
# ---------------------------------------------------------------------------


class TestTrendFollowingStrategy:

    def test_approves_strong_setup(self):
        """TrendFollowingStrategy should approve when all criteria met."""
        strategy = TrendFollowingStrategy()
        ctx = _mock_evaluation_context()
        config = StrategyConfiguration(
            strategy_type=StrategyType.TREND_FOLLOWING,
            minimum_trend_score=60.0,
            minimum_rs_score=50.0,
        )
        result = strategy.evaluate(ctx, config)
        assert result.summary.approved is True
        assert result.summary.strategy_type == StrategyType.TREND_FOLLOWING

    def test_rejects_low_trend_score(self):
        """TrendFollowingStrategy should reject low trend score."""
        strategy = TrendFollowingStrategy()
        ctx = _mock_evaluation_context()
        config = StrategyConfiguration(
            strategy_type=StrategyType.TREND_FOLLOWING,
            minimum_trend_score=90.0,
        )
        result = strategy.evaluate(ctx, config)
        assert result.summary.approved is False
        assert "trend" in result.summary.approval_reason.lower()

    def test_rejects_low_rs_score(self):
        """TrendFollowingStrategy should reject low RS score."""
        strategy = TrendFollowingStrategy()
        ctx = _mock_evaluation_context()
        config = StrategyConfiguration(
            strategy_type=StrategyType.TREND_FOLLOWING,
            minimum_rs_score=90.0,
        )
        result = strategy.evaluate(ctx, config)
        assert result.summary.approved is False
        assert "rs" in result.summary.approval_reason.lower()

    def test_rejects_bear_market(self):
        """TrendFollowingStrategy should reject bear market."""
        strategy = TrendFollowingStrategy()
        ctx = _mock_evaluation_context(market_regime=Regime.BEAR)
        config = StrategyConfiguration(strategy_type=StrategyType.TREND_FOLLOWING)
        result = strategy.evaluate(ctx, config)
        assert result.summary.approved is False

    def test_rejects_low_composite(self):
        """TrendFollowingStrategy should reject low composite."""
        strategy = TrendFollowingStrategy()
        ctx = _mock_evaluation_context(composite_score=30.0)
        config = StrategyConfiguration(
            strategy_type=StrategyType.TREND_FOLLOWING,
            minimum_composite_score=60.0,
        )
        result = strategy.evaluate(ctx, config)
        assert result.summary.approved is False

    def test_is_deterministic(self):
        """TrendFollowingStrategy should be deterministic."""
        strategy = TrendFollowingStrategy()
        ctx = _mock_evaluation_context()
        config = StrategyConfiguration(strategy_type=StrategyType.TREND_FOLLOWING)
        r1 = strategy.evaluate(ctx, config)
        r2 = strategy.evaluate(ctx, config)
        assert r1.summary.overall_score == r2.summary.overall_score

    def test_context_preserved(self):
        """TrendFollowingStrategy should preserve context."""
        strategy = TrendFollowingStrategy()
        ctx = _mock_evaluation_context()
        config = StrategyConfiguration(strategy_type=StrategyType.TREND_FOLLOWING)
        result = strategy.evaluate(ctx, config)
        assert result.context is ctx

    def test_zero_threshold_skips_gate(self):
        """TrendFollowingStrategy should skip gate when threshold is 0."""
        strategy = TrendFollowingStrategy()
        ctx = _mock_evaluation_context()
        config = StrategyConfiguration(
            strategy_type=StrategyType.TREND_FOLLOWING,
            minimum_trend_score=0.0,
            minimum_rs_score=0.0,
        )
        result = strategy.evaluate(ctx, config)
        assert result.summary.approved is True


# ---------------------------------------------------------------------------
# Tests: GrowthStrategy
# ---------------------------------------------------------------------------


class TestGrowthStrategy:

    def test_approves_strong_setup(self):
        """GrowthStrategy should approve when all criteria met."""
        strategy = GrowthStrategy()
        ctx = _mock_evaluation_context()
        config = StrategyConfiguration(strategy_type=StrategyType.GROWTH)
        result = strategy.evaluate(ctx, config)
        assert result.summary.approved is True
        assert result.summary.strategy_type == StrategyType.GROWTH

    def test_rejects_low_composite(self):
        """GrowthStrategy should reject low composite."""
        strategy = GrowthStrategy()
        ctx = _mock_evaluation_context(composite_score=40.0)
        config = StrategyConfiguration(
            strategy_type=StrategyType.GROWTH,
            minimum_composite_score=60.0,
        )
        result = strategy.evaluate(ctx, config)
        assert result.summary.approved is False

    def test_rejects_low_confidence(self):
        """GrowthStrategy should reject low confidence."""
        strategy = GrowthStrategy()
        ctx = _mock_evaluation_context(composite_confidence=30.0)
        config = StrategyConfiguration(
            strategy_type=StrategyType.GROWTH,
            minimum_confidence=60.0,
        )
        result = strategy.evaluate(ctx, config)
        assert result.summary.approved is False

    def test_rejects_no_pattern_when_required(self):
        """GrowthStrategy should reject when pattern required but missing."""
        strategy = GrowthStrategy()
        ctx = _mock_evaluation_context()
        # Override pattern to have score 0
        ctx = EvaluationContext(
            market_result=ctx.market_result,
            relative_strength_result=ctx.relative_strength_result,
            trend_result=ctx.trend_result,
            pattern_result=PatternResult(
                pattern_name=PatternType.UNKNOWN,
                score=0.0,
                confidence=0.0,
            ),
            volume_result=ctx.volume_result,
            composite_result=ctx.composite_result,
            trade_result=ctx.trade_result,
            risk_result=ctx.risk_result,
        )
        config = StrategyConfiguration(
            strategy_type=StrategyType.GROWTH,
            require_strong_pattern=True,
            ignore_pattern=False,
        )
        result = strategy.evaluate(ctx, config)
        assert result.summary.approved is False
        assert "pattern" in result.summary.approval_reason.lower()

    def test_allows_no_pattern_when_ignored(self):
        """GrowthStrategy should allow when pattern ignored."""
        strategy = GrowthStrategy()
        ctx = _mock_evaluation_context()
        ctx = EvaluationContext(
            market_result=ctx.market_result,
            relative_strength_result=ctx.relative_strength_result,
            trend_result=ctx.trend_result,
            pattern_result=PatternResult(
                pattern_name=PatternType.UNKNOWN,
                score=0.0,
                confidence=0.0,
            ),
            volume_result=ctx.volume_result,
            composite_result=ctx.composite_result,
            trade_result=ctx.trade_result,
            risk_result=ctx.risk_result,
        )
        config = StrategyConfiguration(
            strategy_type=StrategyType.GROWTH,
            require_strong_pattern=True,
            ignore_pattern=True,
        )
        result = strategy.evaluate(ctx, config)
        assert result.summary.approved is True

    def test_rejects_bear_market(self):
        """GrowthStrategy should reject bear market."""
        strategy = GrowthStrategy()
        ctx = _mock_evaluation_context(market_regime=Regime.BEAR)
        config = StrategyConfiguration(strategy_type=StrategyType.GROWTH)
        result = strategy.evaluate(ctx, config)
        assert result.summary.approved is False

    def test_is_deterministic(self):
        """GrowthStrategy should be deterministic."""
        strategy = GrowthStrategy()
        ctx = _mock_evaluation_context()
        config = StrategyConfiguration(strategy_type=StrategyType.GROWTH)
        r1 = strategy.evaluate(ctx, config)
        r2 = strategy.evaluate(ctx, config)
        assert r1.summary.overall_score == r2.summary.overall_score


# ---------------------------------------------------------------------------
# Tests: QualityStrategy
# ---------------------------------------------------------------------------


class TestQualityStrategy:

    def test_approves_strong_setup(self):
        """QualityStrategy should approve when all criteria met."""
        strategy = QualityStrategy()
        ctx = _mock_evaluation_context()
        config = StrategyConfiguration(strategy_type=StrategyType.QUALITY)
        result = strategy.evaluate(ctx, config)
        assert result.summary.approved is True
        assert result.summary.strategy_type == StrategyType.QUALITY

    def test_rejects_bear_market(self):
        """QualityStrategy should reject bear market."""
        strategy = QualityStrategy()
        ctx = _mock_evaluation_context(market_regime=Regime.BEAR)
        config = StrategyConfiguration(strategy_type=StrategyType.QUALITY)
        result = strategy.evaluate(ctx, config)
        assert result.summary.approved is False
        assert "weak regime" in result.summary.approval_reason.lower()

    def test_rejects_weak_market(self):
        """QualityStrategy should reject weak market."""
        strategy = QualityStrategy()
        ctx = _mock_evaluation_context(market_regime=Regime.WEAK)
        config = StrategyConfiguration(strategy_type=StrategyType.QUALITY)
        result = strategy.evaluate(ctx, config)
        assert result.summary.approved is False
        assert "weak regime" in result.summary.approval_reason.lower()

    def test_rejects_high_risk_grade(self):
        """QualityStrategy should reject high risk grade."""
        strategy = QualityStrategy()
        ctx = _mock_evaluation_context()
        # Override risk result with high grade
        ctx = EvaluationContext(
            market_result=ctx.market_result,
            relative_strength_result=ctx.relative_strength_result,
            trend_result=ctx.trend_result,
            pattern_result=ctx.pattern_result,
            volume_result=ctx.volume_result,
            composite_result=ctx.composite_result,
            trade_result=ctx.trade_result,
            risk_result=RiskManagementResult(
                max_risk_percent=1.0,
                recommended_position_size=15_000.0,
                capital_at_risk=150.0,
                risk_per_share=1.0,
                maximum_loss=150.0,
                shares_to_buy=60,
                portfolio_exposure=15.0,
                exposure_status="Normal",
                trade_risk_grade="High",
                portfolio_risk_grade="Low",
                execution_allowed=True,
                rejection_reason=RejectionReason.NONE,
                decision_trace=None,  # type: ignore[arg-type]
                validation_flags=["VALID_RISK"],
                confidence=80.0,
                reasons=["Risk acceptable"],
                warnings=[],
            ),
        )
        config = StrategyConfiguration(strategy_type=StrategyType.QUALITY)
        result = strategy.evaluate(ctx, config)
        assert result.summary.approved is False
        assert "risk grade" in result.summary.approval_reason.lower()

    def test_rejects_low_composite(self):
        """QualityStrategy should reject low composite."""
        strategy = QualityStrategy()
        ctx = _mock_evaluation_context(composite_score=40.0)
        config = StrategyConfiguration(
            strategy_type=StrategyType.QUALITY,
            minimum_composite_score=60.0,
        )
        result = strategy.evaluate(ctx, config)
        assert result.summary.approved is False

    def test_is_deterministic(self):
        """QualityStrategy should be deterministic."""
        strategy = QualityStrategy()
        ctx = _mock_evaluation_context()
        config = StrategyConfiguration(strategy_type=StrategyType.QUALITY)
        r1 = strategy.evaluate(ctx, config)
        r2 = strategy.evaluate(ctx, config)
        assert r1.summary.overall_score == r2.summary.overall_score

    def test_context_preserved(self):
        """QualityStrategy should preserve context."""
        strategy = QualityStrategy()
        ctx = _mock_evaluation_context()
        config = StrategyConfiguration(strategy_type=StrategyType.QUALITY)
        result = strategy.evaluate(ctx, config)
        assert result.context is ctx

    def test_allows_bull_market(self):
        """QualityStrategy should allow bull market."""
        strategy = QualityStrategy()
        ctx = _mock_evaluation_context(market_regime=Regime.BULL)
        config = StrategyConfiguration(strategy_type=StrategyType.QUALITY)
        result = strategy.evaluate(ctx, config)
        # Should not be rejected for regime
        assert "weak regime" not in result.summary.approval_reason.lower()


# ---------------------------------------------------------------------------
# Tests: CustomStrategy
# ---------------------------------------------------------------------------


class TestCustomStrategy:

    def test_approves_strong_setup(self):
        """CustomStrategy should approve when all criteria met."""
        strategy = CustomStrategy()
        ctx = _mock_evaluation_context()
        config = StrategyConfiguration(strategy_type=StrategyType.CUSTOM)
        result = strategy.evaluate(ctx, config)
        assert result.summary.approved is True
        assert result.summary.strategy_type == StrategyType.CUSTOM

    def test_rejects_low_composite(self):
        """CustomStrategy should reject low composite."""
        strategy = CustomStrategy()
        ctx = _mock_evaluation_context(composite_score=40.0)
        config = StrategyConfiguration(
            strategy_type=StrategyType.CUSTOM,
            minimum_composite_score=60.0,
        )
        result = strategy.evaluate(ctx, config)
        assert result.summary.approved is False

    def test_rejects_low_pattern(self):
        """CustomStrategy should reject low pattern score."""
        strategy = CustomStrategy()
        ctx = _mock_evaluation_context()
        config = StrategyConfiguration(
            strategy_type=StrategyType.CUSTOM,
            minimum_pattern_score=80.0,
        )
        result = strategy.evaluate(ctx, config)
        assert result.summary.approved is False
        assert "pattern" in result.summary.approval_reason.lower()

    def test_rejects_low_volume(self):
        """CustomStrategy should reject low volume score."""
        strategy = CustomStrategy()
        ctx = _mock_evaluation_context()
        config = StrategyConfiguration(
            strategy_type=StrategyType.CUSTOM,
            minimum_volume_score=90.0,
        )
        result = strategy.evaluate(ctx, config)
        assert result.summary.approved is False
        assert "volume" in result.summary.approval_reason.lower()

    def test_rejects_low_trend(self):
        """CustomStrategy should reject low trend score."""
        strategy = CustomStrategy()
        ctx = _mock_evaluation_context()
        config = StrategyConfiguration(
            strategy_type=StrategyType.CUSTOM,
            minimum_trend_score=90.0,
        )
        result = strategy.evaluate(ctx, config)
        assert result.summary.approved is False
        assert "trend" in result.summary.approval_reason.lower()

    def test_rejects_low_rs(self):
        """CustomStrategy should reject low RS score."""
        strategy = CustomStrategy()
        ctx = _mock_evaluation_context()
        config = StrategyConfiguration(
            strategy_type=StrategyType.CUSTOM,
            minimum_rs_score=90.0,
        )
        result = strategy.evaluate(ctx, config)
        assert result.summary.approved is False
        assert "rs" in result.summary.approval_reason.lower()

    def test_rejects_weak_trend_when_required(self):
        """CustomStrategy should reject weak trend when required."""
        strategy = CustomStrategy()
        ctx = _mock_evaluation_context()
        ctx = EvaluationContext(
            market_result=ctx.market_result,
            relative_strength_result=ctx.relative_strength_result,
            trend_result=TrendResult(
                overall_score=60.0,
                alignment_score=60.0,
                price_position_score=60.0,
                slope_score=60.0,
                structure_score=60.0,
                persistence_score=60.0,
                high_score=60.0,
                trend_quality=TrendQuality.WEAK,
                trend_stage=TrendStage.EARLY,
                confidence=60.0,
                reasons=[],
                warnings=[],
            ),
            pattern_result=ctx.pattern_result,
            volume_result=ctx.volume_result,
            composite_result=ctx.composite_result,
            trade_result=ctx.trade_result,
            risk_result=ctx.risk_result,
        )
        config = StrategyConfiguration(
            strategy_type=StrategyType.CUSTOM,
            require_strong_trend=True,
        )
        result = strategy.evaluate(ctx, config)
        assert result.summary.approved is False
        assert "trend quality" in result.summary.approval_reason.lower()

    def test_rejects_bear_market(self):
        """CustomStrategy should reject bear market."""
        strategy = CustomStrategy()
        ctx = _mock_evaluation_context(market_regime=Regime.BEAR)
        config = StrategyConfiguration(strategy_type=StrategyType.CUSTOM)
        result = strategy.evaluate(ctx, config)
        assert result.summary.approved is False

    def test_zero_thresholds_skip_all_gates(self):
        """CustomStrategy should skip all gates when thresholds are 0."""
        strategy = CustomStrategy()
        ctx = _mock_evaluation_context()
        config = StrategyConfiguration(
            strategy_type=StrategyType.CUSTOM,
            minimum_composite_score=0.0,
            minimum_confidence=0.0,
            minimum_pattern_score=0.0,
            minimum_volume_score=0.0,
            minimum_trend_score=0.0,
            minimum_rs_score=0.0,
        )
        result = strategy.evaluate(ctx, config)
        assert result.summary.approved is True

    def test_is_deterministic(self):
        """CustomStrategy should be deterministic."""
        strategy = CustomStrategy()
        ctx = _mock_evaluation_context()
        config = StrategyConfiguration(strategy_type=StrategyType.CUSTOM)
        r1 = strategy.evaluate(ctx, config)
        r2 = strategy.evaluate(ctx, config)
        assert r1.summary.overall_score == r2.summary.overall_score

    def test_context_preserved(self):
        """CustomStrategy should preserve context."""
        strategy = CustomStrategy()
        ctx = _mock_evaluation_context()
        config = StrategyConfiguration(strategy_type=StrategyType.CUSTOM)
        result = strategy.evaluate(ctx, config)
        assert result.context is ctx

    def test_validation_flags_present(self):
        """CustomStrategy should produce validation flags."""
        strategy = CustomStrategy()
        ctx = _mock_evaluation_context()
        config = StrategyConfiguration(strategy_type=StrategyType.CUSTOM)
        result = strategy.evaluate(ctx, config)
        assert "VALID_STRATEGY_INPUT" in result.validation_flags


# ---------------------------------------------------------------------------
# Tests: StrategyEngine
# ---------------------------------------------------------------------------


class TestStrategyEngine:

    def test_single_public_api(self):
        """StrategyEngine should have single public API."""
        engine = StrategyEngine()
        result = engine.evaluate(_strategy_input())
        assert isinstance(result, StrategyResult)

    def test_decision_trace_populated(self):
        """StrategyEngine should populate decision trace."""
        engine = StrategyEngine()
        result = engine.evaluate(_strategy_input())
        assert result.decision_trace is not None
        assert result.decision_trace.pipeline_source == "EvaluationPipeline"
        assert result.decision_trace.strategy_source == "MomentumStrategy"
        assert result.decision_trace.approval_source == "strategy.evaluate"

    def test_unknown_strategy_raises(self):
        """StrategyEngine should raise ValueError for unknown strategy."""
        engine = StrategyEngine()
        bad_config = StrategyConfiguration(
            strategy_type="Unknown",  # type: ignore[arg-type]
        )
        bad_input = StrategyInput(
            symbol="TEST",
            market_snapshot=_bull_market_snapshot(),
            relative_strength_snapshot=_strong_rs_snapshot(),
            trend_snapshot=_trend_snapshot(),
            pattern_snapshot=_pattern_snapshot(),
            volume_snapshot=_volume_snapshot(),
            configuration=bad_config,
        )
        with pytest.raises(ValueError, match="Unknown strategy"):
            engine.evaluate(bad_input)

    def test_negative_composite_score_rejected(self):
        """StrategyEngine should reject negative composite score."""
        engine = StrategyEngine()
        config = StrategyConfiguration(
            strategy_type=StrategyType.MOMENTUM,
            minimum_composite_score=-10.0,
        )
        bad_input = StrategyInput(
            symbol="TEST",
            market_snapshot=_bull_market_snapshot(),
            relative_strength_snapshot=_strong_rs_snapshot(),
            trend_snapshot=_trend_snapshot(),
            pattern_snapshot=_pattern_snapshot(),
            volume_snapshot=_volume_snapshot(),
            configuration=config,
        )
        with pytest.raises(ValueError, match="non-negative"):
            engine.evaluate(bad_input)

    def test_confidence_above_100_rejected(self):
        """StrategyEngine should reject confidence > 100."""
        engine = StrategyEngine()
        config = StrategyConfiguration(
            strategy_type=StrategyType.MOMENTUM,
            minimum_confidence=110.0,
        )
        bad_input = StrategyInput(
            symbol="TEST",
            market_snapshot=_bull_market_snapshot(),
            relative_strength_snapshot=_strong_rs_snapshot(),
            trend_snapshot=_trend_snapshot(),
            pattern_snapshot=_pattern_snapshot(),
            volume_snapshot=_volume_snapshot(),
            configuration=config,
        )
        with pytest.raises(ValueError, match="between 0 and 100"):
            engine.evaluate(bad_input)

    def test_negative_confidence_rejected(self):
        """StrategyEngine should reject negative confidence."""
        engine = StrategyEngine()
        config = StrategyConfiguration(
            strategy_type=StrategyType.MOMENTUM,
            minimum_confidence=-5.0,
        )
        bad_input = StrategyInput(
            symbol="TEST",
            market_snapshot=_bull_market_snapshot(),
            relative_strength_snapshot=_strong_rs_snapshot(),
            trend_snapshot=_trend_snapshot(),
            pattern_snapshot=_pattern_snapshot(),
            volume_snapshot=_volume_snapshot(),
            configuration=config,
        )
        with pytest.raises(ValueError, match="between 0 and 100"):
            engine.evaluate(bad_input)

    def test_valid_configuration_accepted(self):
        """StrategyEngine should accept valid configuration."""
        engine = StrategyEngine()
        result = engine.evaluate(_strategy_input())
        assert isinstance(result, StrategyResult)

    def test_engine_is_stateless(self):
        """StrategyEngine should be stateless."""
        engine1 = StrategyEngine()
        engine2 = StrategyEngine()
        r1 = engine1.evaluate(_strategy_input())
        r2 = engine2.evaluate(_strategy_input())
        assert r1.summary.overall_score == r2.summary.overall_score


# ---------------------------------------------------------------------------
# Tests: All Strategy Types (end-to-end through engine)
# ---------------------------------------------------------------------------


class TestAllStrategyTypes:

    def test_momentum_e2e(self):
        """Momentum strategy should work end-to-end."""
        engine = StrategyEngine()
        result = engine.evaluate(_strategy_input(strategy_type=StrategyType.MOMENTUM))
        assert result.summary.strategy_type == StrategyType.MOMENTUM
        assert result.decision_trace.strategy_source == "MomentumStrategy"

    def test_breakout_e2e(self):
        """Breakout strategy should work end-to-end."""
        engine = StrategyEngine()
        result = engine.evaluate(_strategy_input(strategy_type=StrategyType.BREAKOUT))
        assert result.summary.strategy_type == StrategyType.BREAKOUT
        assert result.decision_trace.strategy_source == "BreakoutStrategy"

    def test_trend_following_e2e(self):
        """Trend Following strategy should work end-to-end."""
        engine = StrategyEngine()
        result = engine.evaluate(_strategy_input(strategy_type=StrategyType.TREND_FOLLOWING))
        assert result.summary.strategy_type == StrategyType.TREND_FOLLOWING
        assert result.decision_trace.strategy_source == "TrendFollowingStrategy"

    def test_growth_e2e(self):
        """Growth strategy should work end-to-end."""
        engine = StrategyEngine()
        result = engine.evaluate(_strategy_input(strategy_type=StrategyType.GROWTH))
        assert result.summary.strategy_type == StrategyType.GROWTH
        assert result.decision_trace.strategy_source == "GrowthStrategy"

    def test_quality_e2e(self):
        """Quality strategy should work end-to-end."""
        engine = StrategyEngine()
        result = engine.evaluate(_strategy_input(strategy_type=StrategyType.QUALITY))
        assert result.summary.strategy_type == StrategyType.QUALITY
        assert result.decision_trace.strategy_source == "QualityStrategy"

    def test_custom_e2e(self):
        """Custom strategy should work end-to-end."""
        engine = StrategyEngine()
        result = engine.evaluate(_strategy_input(strategy_type=StrategyType.CUSTOM))
        assert result.summary.strategy_type == StrategyType.CUSTOM
        assert result.decision_trace.strategy_source == "CustomStrategy"

    def test_all_types_produce_results(self):
        """All strategy types should produce valid results."""
        engine = StrategyEngine()
        for st in StrategyType:
            result = engine.evaluate(_strategy_input(strategy_type=st))
            assert isinstance(result, StrategyResult), f"Failed for {st}"
            assert result.summary.strategy_type == st, f"Wrong type for {st}"
            assert result.decision_trace is not None, f"Missing trace for {st}"

    def test_all_types_deterministic(self):
        """All strategy types should be deterministic."""
        engine = StrategyEngine()
        for st in StrategyType:
            r1 = engine.evaluate(_strategy_input(strategy_type=st))
            r2 = engine.evaluate(_strategy_input(strategy_type=st))
            assert r1.summary.overall_score == r2.summary.overall_score, f"Non-deterministic {st}"
            assert r1.summary.approved == r2.summary.approved, f"Non-deterministic approval {st}"

    def test_all_types_preserve_context(self):
        """All strategy types should preserve context."""
        engine = StrategyEngine()
        for st in StrategyType:
            result = engine.evaluate(_strategy_input(strategy_type=st))
            assert result.context is not None, f"Missing context for {st}"

    def test_all_types_have_validation_flags(self):
        """All strategy types should produce validation flags."""
        engine = StrategyEngine()
        for st in StrategyType:
            result = engine.evaluate(_strategy_input(strategy_type=st))
            assert "VALID_STRATEGY_INPUT" in result.validation_flags, f"Missing flag for {st}"


# ---------------------------------------------------------------------------
# Tests: Evaluation Context
# ---------------------------------------------------------------------------


class TestEvaluationContext:

    def test_context_immutable(self):
        """EvaluationContext should be frozen."""
        ctx = _mock_evaluation_context()
        with pytest.raises(AttributeError):
            ctx.market_result = None  # type: ignore[misc]

    def test_context_has_all_results(self):
        """EvaluationContext should have all engine results."""
        ctx = _mock_evaluation_context()
        assert ctx.market_result is not None
        assert ctx.relative_strength_result is not None
        assert ctx.trend_result is not None
        assert ctx.pattern_result is not None
        assert ctx.volume_result is not None
        assert ctx.composite_result is not None
        assert ctx.trade_result is not None
        assert ctx.risk_result is not None

    def test_context_from_pipeline(self):
        """EvaluationContext from pipeline should have all results."""
        pipeline = EvaluationPipeline()
        ctx = pipeline.run(_strategy_input())
        assert ctx.market_result is not None
        assert ctx.composite_result is not None
        assert ctx.risk_result is not None


# ---------------------------------------------------------------------------
# Tests: Regression (end-to-end through StrategyEngine)
# ---------------------------------------------------------------------------


class TestRegression:

    def test_end_to_end(self):
        """Full end-to-end strategy evaluation should work."""
        engine = StrategyEngine()
        result = engine.evaluate(_strategy_input())

        # Summary
        assert result.summary.strategy_type == StrategyType.MOMENTUM
        assert isinstance(result.summary.overall_score, float)
        assert isinstance(result.summary.confidence, float)
        assert isinstance(result.summary.approved, bool)
        assert result.summary.approval_reason is not None

        # Context
        assert result.context is not None
        assert result.context.composite_result is not None

        # Decision trace
        assert result.decision_trace is not None
        assert result.decision_trace.pipeline_source == "EvaluationPipeline"

        # Validation
        assert "VALID_STRATEGY_INPUT" in result.validation_flags

        # Reasons
        assert len(result.reasons) > 0

    def test_all_engines_called(self):
        """Pipeline should call all engines."""
        pipeline = EvaluationPipeline()
        ctx = pipeline.run(_strategy_input())
        assert 0 <= ctx.composite_result.overall_score <= 100
        assert ctx.trade_result is not None
        assert ctx.risk_result is not None

    def test_bear_market_end_to_end(self):
        """End-to-end with bear market should reject."""
        engine = StrategyEngine()
        result = engine.evaluate(_strategy_input(market=_bear_market_snapshot()))
        # Bear market should produce warnings about market conditions
        assert result.context.market_result.regime == Regime.BEAR
        assert result.summary.approved is False

    def test_pipeline_deterministic(self):
        """Pipeline should produce same results on repeated runs."""
        pipeline = EvaluationPipeline()
        ctx1 = pipeline.run(_strategy_input())
        ctx2 = pipeline.run(_strategy_input())
        assert ctx1.composite_result.overall_score == ctx2.composite_result.overall_score
        assert ctx1.risk_result.execution_allowed == ctx2.risk_result.execution_allowed
