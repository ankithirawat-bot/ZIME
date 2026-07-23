"""Strategy models.

Frozen dataclasses for strategy definitions, rules, signals, results,
and institutional strategy evaluation types.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from datetime import datetime
from enum import StrEnum
from typing import Any

from backend.composite.models import CompositeResult
from backend.patterns.models import PatternResult, PatternSnapshot
from backend.regime.models import MarketRegime, MarketSnapshot
from backend.relative_strength.models import RelativeStrengthResult, StockSnapshot
from backend.risk.models import RiskManagementResult
from backend.strategy.signals import SignalType
from backend.trade.models import TradePlan
from backend.trend.models import TrendResult, TrendSnapshot
from backend.volume.models import VolumeResult, VolumeSnapshot


class RuleCategory(StrEnum):
    """Categories of strategy rules."""

    SCREEN = "screen"
    RANKING = "ranking"
    TECHNICAL = "technical"
    FUNDAMENTAL = "fundamental"
    PORTFOLIO = "portfolio"
    RISK = "risk"
    CUSTOM = "custom"


class LogicalOperator(StrEnum):
    """Logical operators for combining conditions."""

    AND = "AND"
    OR = "OR"
    NOT = "NOT"


class ComparisonOperator(StrEnum):
    """Comparison operators for conditions."""

    EQ = "=="
    NEQ = "!="
    GT = ">"
    GTE = ">="
    LT = "<"
    LTE = "<="
    IN = "IN"
    NOT_IN = "NOT_IN"
    BETWEEN = "BETWEEN"


class StrategyType(StrEnum):
    """Supported investment strategies."""

    MOMENTUM = "Momentum"
    BREAKOUT = "Breakout"
    TREND_FOLLOWING = "Trend Following"
    GROWTH = "Growth"
    QUALITY = "Quality"
    CUSTOM = "Custom"


@dataclass(frozen=True)
class StrategyMetadata:
    """Metadata for a strategy definition.

    Attributes:
        name:        Strategy name.
        description: Strategy description.
        version:     Schema version.
        author:      Strategy author.
        created_at:  Creation timestamp.
        tags:        Searchable tags.
    """

    name: str
    description: str = ""
    version: str = "1.0"
    author: str = ""
    created_at: datetime = field(default_factory=lambda: datetime.now().astimezone())
    tags: tuple[str, ...] = field(default_factory=tuple)


@dataclass(frozen=True)
class Condition:
    """A single comparison condition.

    Attributes:
        field:    Data field path (e.g. "fundamentals.roe").
        operator: Comparison operator.
        value:    Comparison value(s).
    """

    field: str
    operator: ComparisonOperator
    value: Any


@dataclass(frozen=True)
class ConditionGroup:
    """A group of conditions combined with logical operators.

    Attributes:
        operator:   Logical operator.
        conditions: Individual conditions.
        groups:     Nested condition groups.
        negate:     Whether to negate the group result.
    """

    operator: LogicalOperator = LogicalOperator.AND
    conditions: tuple[Condition, ...] = field(default_factory=tuple)
    groups: tuple[ConditionGroup, ...] = field(default_factory=tuple)
    negate: bool = False


@dataclass(frozen=True)
class StrategyRule:
    """A strategy rule with conditions and signal.

    Attributes:
        name:        Rule name.
        description: Rule description.
        conditions:  Condition group to evaluate.
        signal:      Signal to emit if conditions match.
        weight:      Rule weight (0.0 to 1.0).
        category:    Rule category.
    """

    name: str
    description: str = ""
    conditions: ConditionGroup = field(default_factory=ConditionGroup)
    signal: SignalType = SignalType.HOLD
    weight: float = 1.0
    category: RuleCategory = RuleCategory.CUSTOM


@dataclass(frozen=True)
class MatchedRule:
    """A rule that was evaluated.

    Attributes:
        rule_name:  Rule name.
        matched:    Whether the rule matched.
        signal:     Signal from the rule.
        description: Rule description.
    """

    rule_name: str
    matched: bool
    signal: SignalType
    description: str = ""


@dataclass(frozen=True)
class StrategySignal:
    """Signal generated for a symbol.

    Attributes:
        symbol:       Ticker symbol.
        signal:       Signal type.
        confidence:   Confidence score (0-100).
        matched_rules: Rules that matched.
        failed_rules:  Rules that failed.
        total_rules:   Total rules evaluated.
    """

    symbol: str
    signal: SignalType
    confidence: float = 0.0
    matched_rules: tuple[MatchedRule, ...] = field(default_factory=tuple)
    failed_rules: tuple[MatchedRule, ...] = field(default_factory=tuple)
    total_rules: int = 0


@dataclass(frozen=True)
class StrategyStatistics:
    """Statistics for a strategy evaluation run.

    Attributes:
        total_symbols:    Total symbols evaluated.
        total_rules:      Total rules evaluated.
        elapsed_seconds:  Evaluation time.
        signals_by_type:  Count of each signal type.
        mean_confidence:  Mean confidence score.
    """

    total_symbols: int = 0
    total_rules: int = 0
    elapsed_seconds: float = 0.0
    signals_by_type: dict[str, int] = field(default_factory=dict)
    mean_confidence: float = 0.0


@dataclass(frozen=True)
class StrategyDefinition:
    """Complete strategy definition.

    Attributes:
        metadata: Strategy metadata.
        rules:    Strategy rules.
    """

    metadata: StrategyMetadata
    rules: tuple[StrategyRule, ...] = field(default_factory=tuple)


# ---------------------------------------------------------------------------
# Institutional strategy evaluation types
# ---------------------------------------------------------------------------


@dataclass(frozen=True)
class StrategyConfiguration:
    """Configuration for a strategy evaluation.

    Attributes:
        strategy_type:            Strategy to execute.
        minimum_composite_score:  Minimum composite score to approve.
        minimum_confidence:       Minimum confidence to approve.
        allow_bear_market:        Allow execution in bear markets.
        allow_extended_trend:     Allow execution in extended trends.
        minimum_pattern_score:    Minimum pattern score (0 = no gate).
        minimum_volume_score:     Minimum volume score (0 = no gate).
        minimum_trend_score:      Minimum trend score (0 = no gate).
        minimum_rs_score:         Minimum relative strength score (0 = no gate).
        require_strong_trend:     Require trend quality >= Strong.
        require_strong_pattern:   Require pattern score > 0.
        ignore_pattern:           Skip pattern gate entirely.
    """

    strategy_type: StrategyType
    minimum_composite_score: float = 60.0
    minimum_confidence: float = 60.0
    allow_bear_market: bool = False
    allow_extended_trend: bool = True
    minimum_pattern_score: float = 0.0
    minimum_volume_score: float = 0.0
    minimum_trend_score: float = 0.0
    minimum_rs_score: float = 0.0
    require_strong_trend: bool = False
    require_strong_pattern: bool = False
    ignore_pattern: bool = False


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
    """Result of a strategy evaluation.

    Attributes:
        strategy_name:     Name of the strategy used.
        signals:           Signals for each symbol.
        statistics:        Evaluation statistics.
        evaluated_at:      When the evaluation was performed.
        summary:           Strategy summary.
        context:           Evaluation context with all engine outputs.
        decision_trace:    Trace of evaluation decisions.
        validation_flags:  Validation outcomes.
        reasons:           Aggregated explanations.
        warnings:          Aggregated warnings.
    """

    strategy_name: str = ""
    signals: tuple[StrategySignal, ...] = field(default_factory=tuple)
    statistics: StrategyStatistics = field(default_factory=StrategyStatistics)
    evaluated_at: datetime = field(default_factory=lambda: datetime.now().astimezone())
    summary: StrategySummary | None = None
    context: EvaluationContext | None = None
    decision_trace: StrategyDecisionTrace | None = None
    validation_flags: tuple[str, ...] = field(default_factory=tuple)
    reasons: tuple[str, ...] = field(default_factory=tuple)
    warnings: tuple[str, ...] = field(default_factory=tuple)


