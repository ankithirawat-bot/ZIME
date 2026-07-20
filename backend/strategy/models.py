"""
Strategy Infrastructure models.

Frozen dataclasses for strategy evaluation, configuration, and results.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from enum import Enum

from backend.composite.models import CompositeResult
from backend.patterns.models import PatternResult, PatternSnapshot
from backend.regime.models import MarketRegime, MarketSnapshot
from backend.relative_strength.models import RelativeStrengthResult, StockSnapshot
from backend.risk.models import RiskManagementResult
from backend.trade.models import TradePlan
from backend.trend.models import TrendResult, TrendSnapshot
from backend.volume.models import VolumeResult, VolumeSnapshot


class StrategyType(Enum):
    """Supported investment strategies."""

    MOMENTUM = "Momentum"


@dataclass(frozen=True)
class StrategyConfiguration:
    """Configuration for a strategy evaluation.

    Attributes:
        strategy_type:            Strategy to execute.
        minimum_composite_score:  Minimum composite score to approve.
        minimum_confidence:       Minimum confidence to approve.
        allow_bear_market:        Allow execution in bear markets.
        allow_extended_trend:     Allow execution in extended trends.
    """

    strategy_type: StrategyType
    minimum_composite_score: float = 60.0
    minimum_confidence: float = 60.0
    allow_bear_market: bool = False
    allow_extended_trend: bool = True


@dataclass(frozen=True)
class StrategyInput:
    """Input to the strategy engine.

    Attributes:
        symbol:                      Ticker symbol.
        market_snapshot:             Market regime data.
        relative_strength_snapshot:  Relative strength data.
        trend_snapshot:              Trend data.
        pattern_snapshot:            Pattern data.
        volume_snapshot:             Volume data.
        configuration:               Strategy configuration.
    """

    symbol: str
    market_snapshot: MarketSnapshot
    relative_strength_snapshot: StockSnapshot
    trend_snapshot: TrendSnapshot
    pattern_snapshot: PatternSnapshot
    volume_snapshot: VolumeSnapshot
    configuration: StrategyConfiguration


@dataclass(frozen=True)
class EvaluationContext:
    """Immutable container for all engine outputs.

    Populated by the EvaluationPipeline. No strategy-specific logic.

    Attributes:
        market_result:            Market regime result.
        relative_strength_result: Relative strength result.
        trend_result:             Trend quality result.
        pattern_result:           Pattern recognition result.
        volume_result:            Volume intelligence result.
        composite_result:         Composite decision result.
        trade_result:             Trade planning result.
        risk_result:              Risk management result.
    """

    market_result: MarketRegime
    relative_strength_result: RelativeStrengthResult
    trend_result: TrendResult
    pattern_result: PatternResult
    volume_result: VolumeResult
    composite_result: CompositeResult
    trade_result: TradePlan
    risk_result: RiskManagementResult


@dataclass(frozen=True)
class StrategySummary:
    """High-level strategy evaluation summary.

    Attributes:
        strategy_type:     Strategy that was evaluated.
        overall_score:     Final score from the strategy.
        confidence:        Confidence in the recommendation.
        approved:          Whether the strategy approves the trade.
        approval_reason:   Human-readable approval reason.
    """

    strategy_type: StrategyType
    overall_score: float
    confidence: float
    approved: bool
    approval_reason: str


@dataclass(frozen=True)
class StrategyDecisionTrace:
    """Trace of strategy evaluation decisions.

    Attributes:
        pipeline_source:  How the evaluation context was built.
        strategy_source:  Which strategy evaluated the context.
        approval_source:  How the approval decision was made.
    """

    pipeline_source: str
    strategy_source: str
    approval_source: str


@dataclass(frozen=True)
class StrategyResult:
    """Complete strategy evaluation result.

    Attributes:
        summary:           Strategy summary.
        context:           Evaluation context with all engine outputs.
        decision_trace:    Trace of evaluation decisions.
        validation_flags:  Validation outcomes.
        reasons:           Aggregated explanations.
        warnings:          Aggregated warnings.
    """

    summary: StrategySummary
    context: EvaluationContext
    decision_trace: StrategyDecisionTrace
    validation_flags: tuple[str, ...] = field(default_factory=tuple)
    reasons: tuple[str, ...] = field(default_factory=tuple)
    warnings: tuple[str, ...] = field(default_factory=tuple)
