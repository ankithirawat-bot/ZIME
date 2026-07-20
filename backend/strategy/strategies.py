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
from backend.trend.models import TrendQuality, TrendStage


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
            6. Composite recommendation must not be Avoid.
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
            approval_reason = f"Risk rejected: {risk.rejection_reason.value}"

        # Gate 6: Composite recommendation
        if composite.recommendation == Recommendation.AVOID:
            approved = False
            approval_reason = "Composite recommendation is Avoid"

        reasons.extend(_extract_reasons(context))

        summary = StrategySummary(
            strategy_type=StrategyType.MOMENTUM,
            overall_score=round(composite.overall_score, 2),
            confidence=round(composite.confidence, 2),
            approved=approved,
            approval_reason=approval_reason,
        )

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


class BreakoutStrategy(Strategy):
    """Breakout investment strategy.

    Focuses on strong pattern formation with volume confirmation.
    """

    _strategy_type = StrategyType.BREAKOUT

    def evaluate(
        self,
        context: EvaluationContext,
        configuration: StrategyConfiguration,
    ) -> StrategyResult:
        """Evaluate using breakout-specific criteria.

        Gating rules:
            1. Pattern score must meet minimum.
            2. Volume score must meet minimum.
            3. Composite score must meet minimum.
            4. Confidence must meet minimum.
            5. Risk engine must allow execution.
            6. Bear market rejected unless allowed.
        """
        validation_flags: list[str] = []
        reasons: list[str] = []
        warnings: list[str] = []

        composite = context.composite_result
        risk = context.risk_result
        market = context.market_result
        pattern = context.pattern_result
        volume = context.volume_result

        approved = True
        approval_reason = "All breakout criteria met"

        # Gate 1: Pattern score
        min_pattern = configuration.minimum_pattern_score
        if min_pattern > 0 and pattern.score < min_pattern:
            approved = False
            approval_reason = (
                f"Pattern score {pattern.score:.1f} below "
                f"minimum {min_pattern:.1f}"
            )

        # Gate 2: Volume score
        min_volume = configuration.minimum_volume_score
        if min_volume > 0 and volume.overall_score < min_volume:
            approved = False
            approval_reason = (
                f"Volume score {volume.overall_score:.1f} below "
                f"minimum {min_volume:.1f}"
            )

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
            approval_reason = f"Risk rejected: {risk.rejection_reason.value}"

        # Gate 6: Bear market
        if market.regime == Regime.BEAR and not configuration.allow_bear_market:
            approved = False
            approval_reason = "Bear market rejected"
            warnings.append("Bear market: execution not allowed by configuration")

        reasons.extend(_extract_reasons(context))

        summary = StrategySummary(
            strategy_type=StrategyType.BREAKOUT,
            overall_score=round(composite.overall_score, 2),
            confidence=round(composite.confidence, 2),
            approved=approved,
            approval_reason=approval_reason,
        )

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


class TrendFollowingStrategy(Strategy):
    """Trend following investment strategy.

    Focuses on strong trend with positive regime and relative strength.
    """

    _strategy_type = StrategyType.TREND_FOLLOWING

    def evaluate(
        self,
        context: EvaluationContext,
        configuration: StrategyConfiguration,
    ) -> StrategyResult:
        """Evaluate using trend-following criteria.

        Gating rules:
            1. Trend score must meet minimum.
            2. Regime must not be Bear (unless allowed).
            3. Relative strength must meet minimum.
            4. Composite score must meet minimum.
            5. Confidence must meet minimum.
            6. Risk engine must allow execution.
        """
        validation_flags: list[str] = []
        reasons: list[str] = []
        warnings: list[str] = []

        composite = context.composite_result
        risk = context.risk_result
        market = context.market_result
        trend = context.trend_result
        rs = context.relative_strength_result

        approved = True
        approval_reason = "All trend following criteria met"

        # Gate 1: Trend score
        min_trend = configuration.minimum_trend_score
        if min_trend > 0 and trend.overall_score < min_trend:
            approved = False
            approval_reason = (
                f"Trend score {trend.overall_score:.1f} below "
                f"minimum {min_trend:.1f}"
            )

        # Gate 2: Bear market
        if market.regime == Regime.BEAR and not configuration.allow_bear_market:
            approved = False
            approval_reason = "Bear market rejected"
            warnings.append("Bear market: execution not allowed by configuration")

        # Gate 3: Relative strength
        min_rs = configuration.minimum_rs_score
        if min_rs > 0 and rs.overall_score < min_rs:
            approved = False
            approval_reason = (
                f"RS score {rs.overall_score:.1f} below "
                f"minimum {min_rs:.1f}"
            )

        # Gate 4: Composite score
        if composite.overall_score < configuration.minimum_composite_score:
            approved = False
            approval_reason = (
                f"Composite score {composite.overall_score:.1f} below "
                f"minimum {configuration.minimum_composite_score:.1f}"
            )

        # Gate 5: Confidence
        if composite.confidence < configuration.minimum_confidence:
            approved = False
            approval_reason = (
                f"Confidence {composite.confidence:.1f} below "
                f"minimum {configuration.minimum_confidence:.1f}"
            )

        # Gate 6: Risk execution
        if not risk.execution_allowed:
            approved = False
            approval_reason = f"Risk rejected: {risk.rejection_reason.value}"

        reasons.extend(_extract_reasons(context))

        summary = StrategySummary(
            strategy_type=StrategyType.TREND_FOLLOWING,
            overall_score=round(composite.overall_score, 2),
            confidence=round(composite.confidence, 2),
            approved=approved,
            approval_reason=approval_reason,
        )

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


class GrowthStrategy(Strategy):
    """Growth investment strategy.

    Focuses on composite strength and confidence.
    Pattern can be ignored if configured.
    """

    _strategy_type = StrategyType.GROWTH

    def evaluate(
        self,
        context: EvaluationContext,
        configuration: StrategyConfiguration,
    ) -> StrategyResult:
        """Evaluate using growth-specific criteria.

        Gating rules:
            1. Composite score must meet minimum.
            2. Confidence must meet minimum.
            3. Pattern gate (unless ignore_pattern).
            4. Risk engine must allow execution.
            5. Bear market rejected unless allowed.
        """
        validation_flags: list[str] = []
        reasons: list[str] = []
        warnings: list[str] = []

        composite = context.composite_result
        risk = context.risk_result
        market = context.market_result
        pattern = context.pattern_result

        approved = True
        approval_reason = "All growth criteria met"

        # Gate 1: Composite score
        if composite.overall_score < configuration.minimum_composite_score:
            approved = False
            approval_reason = (
                f"Composite score {composite.overall_score:.1f} below "
                f"minimum {configuration.minimum_composite_score:.1f}"
            )

        # Gate 2: Confidence
        if composite.confidence < configuration.minimum_confidence:
            approved = False
            approval_reason = (
                f"Confidence {composite.confidence:.1f} below "
                f"minimum {configuration.minimum_confidence:.1f}"
            )

        # Gate 3: Pattern (unless ignored)
        if not configuration.ignore_pattern:
            if configuration.require_strong_pattern and pattern.score == 0:
                approved = False
                approval_reason = "No pattern detected (required)"

        # Gate 4: Risk execution
        if not risk.execution_allowed:
            approved = False
            approval_reason = f"Risk rejected: {risk.rejection_reason.value}"

        # Gate 5: Bear market
        if market.regime == Regime.BEAR and not configuration.allow_bear_market:
            approved = False
            approval_reason = "Bear market rejected"
            warnings.append("Bear market: execution not allowed by configuration")

        reasons.extend(_extract_reasons(context))

        summary = StrategySummary(
            strategy_type=StrategyType.GROWTH,
            overall_score=round(composite.overall_score, 2),
            confidence=round(composite.confidence, 2),
            approved=approved,
            approval_reason=approval_reason,
        )

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


class QualityStrategy(Strategy):
    """Quality investment strategy.

    Requires higher confidence, lower risk tolerance,
    and strong market regime.
    """

    _strategy_type = StrategyType.QUALITY

    def evaluate(
        self,
        context: EvaluationContext,
        configuration: StrategyConfiguration,
    ) -> StrategyResult:
        """Evaluate using quality-specific criteria.

        Gating rules:
            1. Regime must not be Bear or Weak.
            2. Composite score must meet minimum.
            3. Confidence must meet minimum.
            4. Risk grade must not be High or Very High.
            5. Risk engine must allow execution.
        """
        validation_flags: list[str] = []
        reasons: list[str] = []
        warnings: list[str] = []

        composite = context.composite_result
        risk = context.risk_result
        market = context.market_result

        approved = True
        approval_reason = "All quality criteria met"

        # Gate 1: Strong regime required
        if market.regime in (Regime.BEAR, Regime.WEAK):
            approved = False
            approval_reason = f"Weak regime rejected: {market.regime.value}"
            warnings.append(f"Market regime {market.regime.value}: not suitable for quality")

        # Gate 2: Composite score
        if composite.overall_score < configuration.minimum_composite_score:
            approved = False
            approval_reason = (
                f"Composite score {composite.overall_score:.1f} below "
                f"minimum {configuration.minimum_composite_score:.1f}"
            )

        # Gate 3: Confidence (quality demands higher confidence)
        if composite.confidence < configuration.minimum_confidence:
            approved = False
            approval_reason = (
                f"Confidence {composite.confidence:.1f} below "
                f"minimum {configuration.minimum_confidence:.1f}"
            )

        # Gate 4: Risk grade tolerance
        high_risk_grades = {"High", "Very High", "Reject"}
        if risk.trade_risk_grade in high_risk_grades:
            approved = False
            approval_reason = f"Risk grade too high: {risk.trade_risk_grade}"
            warnings.append(f"Trade risk grade {risk.trade_risk_grade}: exceeds quality tolerance")

        # Gate 5: Risk execution
        if not risk.execution_allowed:
            approved = False
            approval_reason = f"Risk rejected: {risk.rejection_reason.value}"

        reasons.extend(_extract_reasons(context))

        summary = StrategySummary(
            strategy_type=StrategyType.QUALITY,
            overall_score=round(composite.overall_score, 2),
            confidence=round(composite.confidence, 2),
            approved=approved,
            approval_reason=approval_reason,
        )

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


class CustomStrategy(Strategy):
    """Custom investment strategy.

    Configuration-driven. No hardcoded methodology.
    Checks all configured thresholds.
    """

    _strategy_type = StrategyType.CUSTOM

    def evaluate(
        self,
        context: EvaluationContext,
        configuration: StrategyConfiguration,
    ) -> StrategyResult:
        """Evaluate using configuration-driven criteria.

        Checks every configured threshold. A threshold of 0 means
        that particular gate is disabled.
        """
        validation_flags: list[str] = []
        reasons: list[str] = []
        warnings: list[str] = []

        composite = context.composite_result
        risk = context.risk_result
        market = context.market_result
        trend = context.trend_result
        pattern = context.pattern_result
        volume = context.volume_result
        rs = context.relative_strength_result

        approved = True
        approval_reason = "All custom criteria met"

        # Gate: Bear market
        if market.regime == Regime.BEAR and not configuration.allow_bear_market:
            approved = False
            approval_reason = "Bear market rejected"
            warnings.append("Bear market: execution not allowed by configuration")

        # Gate: Extended trend
        if (trend.trend_stage == TrendStage.EXTENDED
                and not configuration.allow_extended_trend):
            approved = False
            approval_reason = "Extended trend rejected"
            warnings.append("Extended trend: execution not allowed by configuration")

        # Gate: Composite score
        if composite.overall_score < configuration.minimum_composite_score:
            approved = False
            approval_reason = (
                f"Composite score {composite.overall_score:.1f} below "
                f"minimum {configuration.minimum_composite_score:.1f}"
            )

        # Gate: Confidence
        if composite.confidence < configuration.minimum_confidence:
            approved = False
            approval_reason = (
                f"Confidence {composite.confidence:.1f} below "
                f"minimum {configuration.minimum_confidence:.1f}"
            )

        # Gate: Pattern score
        min_pattern = configuration.minimum_pattern_score
        if min_pattern > 0 and pattern.score < min_pattern:
            approved = False
            approval_reason = (
                f"Pattern score {pattern.score:.1f} below "
                f"minimum {min_pattern:.1f}"
            )

        # Gate: Volume score
        min_volume = configuration.minimum_volume_score
        if min_volume > 0 and volume.overall_score < min_volume:
            approved = False
            approval_reason = (
                f"Volume score {volume.overall_score:.1f} below "
                f"minimum {min_volume:.1f}"
            )

        # Gate: Trend score
        min_trend = configuration.minimum_trend_score
        if min_trend > 0 and trend.overall_score < min_trend:
            approved = False
            approval_reason = (
                f"Trend score {trend.overall_score:.1f} below "
                f"minimum {min_trend:.1f}"
            )

        # Gate: RS score
        min_rs = configuration.minimum_rs_score
        if min_rs > 0 and rs.overall_score < min_rs:
            approved = False
            approval_reason = (
                f"RS score {rs.overall_score:.1f} below "
                f"minimum {min_rs:.1f}"
            )

        # Gate: Strong trend required
        if configuration.require_strong_trend:
            if trend.trend_quality not in (TrendQuality.STRONG, TrendQuality.EXCEPTIONAL):
                approved = False
                approval_reason = (
                    f"Trend quality {trend.trend_quality.value} below Strong"
                )

        # Gate: Risk execution
        if not risk.execution_allowed:
            approved = False
            approval_reason = f"Risk rejected: {risk.rejection_reason.value}"

        reasons.extend(_extract_reasons(context))

        summary = StrategySummary(
            strategy_type=StrategyType.CUSTOM,
            overall_score=round(composite.overall_score, 2),
            confidence=round(composite.confidence, 2),
            approved=approved,
            approval_reason=approval_reason,
        )

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
