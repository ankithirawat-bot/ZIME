"""
Strategy interface and concrete strategies.

All strategies inherit from Strategy ABC.
"""

from __future__ import annotations

from abc import ABC, abstractmethod

from backend.composite.models import Recommendation
from backend.regime.models import Regime
from backend.strategy.models import (
    EvaluationContext,
    StrategyConfiguration,
    StrategyResult,
    StrategySummary,
    StrategyType,
)
from backend.trend.models import TrendStage


class Strategy(ABC):
    """Abstract base class for investment strategies.

    All strategies must implement :meth:`evaluate`.
    """

    @property
    def strategy_type(self) -> StrategyType:
        """Return the strategy type this strategy implements."""
        return self._strategy_type

    @property
    def _strategy_type(self) -> StrategyType:
        """Override in subclass to declare strategy type."""
        raise NotImplementedError

    @abstractmethod
    def evaluate(
        self,
        context: EvaluationContext,
        configuration: StrategyConfiguration,
    ) -> StrategyResult:
        """Evaluate the context and produce a strategy result.

        Args:
            context:       Immutable engine outputs.
            configuration: Strategy-specific configuration.

        Returns:
            StrategyResult with approval decision.
        """


class MomentumStrategy(Strategy):
    """Momentum investment strategy.

    Evaluates composite context with momentum-specific gating.
    Does NOT perform technical analysis directly.
    Consumes engine outputs only.
    """

    _strategy_type = StrategyType.MOMENTUM

    def evaluate(
        self,
        context: EvaluationContext,
        configuration: StrategyConfiguration,
    ) -> StrategyResult:
        """Evaluate using momentum-specific criteria.

        Gating rules:
            1. Bear market rejected unless allow_bear_market.
            2. Extended trend rejected unless allow_extended_trend.
            3. Composite score must meet minimum.
            4. Confidence must meet minimum.
            5. Risk engine must allow execution.

        Args:
            context:       Immutable engine outputs.
            configuration: Momentum strategy configuration.

        Returns:
            StrategyResult with approval decision.
        """
        validation_flags: list[str] = []
        reasons: list[str] = []
        warnings: list[str] = []

        composite = context.composite_result
        risk = context.risk_result
        market = context.market_result
        trend = context.trend_result

        approved = True
        approval_reason = "All momentum criteria met"

        # Gate 1: Bear market
        if market.regime == Regime.BEAR and not configuration.allow_bear_market:
            approved = False
            approval_reason = "Bear market rejected"
            warnings.append("Bear market: execution not allowed by configuration")

        # Gate 2: Extended trend
        if (trend.trend_stage == TrendStage.EXTENDED
                and not configuration.allow_extended_trend):
            approved = False
            approval_reason = "Extended trend rejected"
            warnings.append("Extended trend: execution not allowed by configuration")

        # Gate 3: Composite score
        if composite.overall_score < configuration.minimum_composite_score:
            approved = False
            approval_reason = (
                f"Composite score {composite.overall_score:.1f} below "
                f"minimum {configuration.minimum_composite_score:.1f}"
            )

        # Gate 4: Confidence
        if composite.confidence < configuration.minimum_confidence:
            approved = False
            approval_reason = (
                f"Confidence {composite.confidence:.1f} below "
                f"minimum {configuration.minimum_confidence:.1f}"
            )

        # Gate 5: Risk execution
        if not risk.execution_allowed:
            approved = False
            approval_reason = (
                f"Risk rejected: {risk.rejection_reason.value}"
            )

        # Gate 6: Composite recommendation
        if composite.recommendation == Recommendation.AVOID:
            approved = False
            approval_reason = "Composite recommendation is Avoid"

        # Collect reasons from all engines
        reasons.extend(_extract_reasons(context))

        # Overall score: weighted from composite
        overall_score = composite.overall_score
        confidence = composite.confidence

        # Build summary
        summary = StrategySummary(
            strategy_type=StrategyType.MOMENTUM,
            overall_score=round(overall_score, 2),
            confidence=round(confidence, 2),
            approved=approved,
            approval_reason=approval_reason,
        )

        # Validation flags
        validation_flags.append("VALID_STRATEGY_INPUT")
        if approved:
            validation_flags.append("APPROVED")
        else:
            validation_flags.append("REJECTED")

        return StrategyResult(
            summary=summary,
            context=context,
            decision_trace=None,  # type: ignore[arg-type]
            validation_flags=tuple(validation_flags),
            reasons=tuple(reasons[:20]),
            warnings=tuple(warnings[:20]),
        )


def _extract_reasons(context: EvaluationContext) -> list[str]:
    """Extract top reasons from all engine outputs."""
    reasons: list[str] = []

    market = context.market_result
    if market.reasons:
        reasons.append(f"Market: {market.reasons[0]}")

    rs = context.relative_strength_result
    if rs.reasons:
        reasons.append(f"RS: {rs.reasons[0]}")

    trend = context.trend_result
    if trend.reasons:
        reasons.append(f"Trend: {trend.reasons[0]}")

    pattern = context.pattern_result
    if pattern.reasons:
        reasons.append(f"Pattern: {pattern.reasons[0]}")

    volume = context.volume_result
    if volume.reasons:
        reasons.append(f"Volume: {volume.reasons[0]}")

    composite = context.composite_result
    if composite.reasons:
        reasons.append(f"Composite: {composite.reasons[0]}")

    trade = context.trade_result
    if trade.reasons:
        reasons.append(f"Trade: {trade.reasons[0]}")

    risk = context.risk_result
    if risk.reasons:
        reasons.append(f"Risk: {risk.reasons[0]}")

    return reasons
