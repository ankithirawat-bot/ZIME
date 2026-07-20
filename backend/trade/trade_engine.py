"""
Trade Planning Engine.

Converts Composite Decision into an executable trade plan.
"""

from __future__ import annotations

from backend.composite.models import CompositeResult, Recommendation
from backend.core.constants import MAX_ITEMS
from backend.core.validation import validate_price_relationship
from backend.patterns.models import PatternResult
from backend.trade.models import (
    EntryType,
    ExecutionStatus,
    TradeDecisionTrace,
    TradePlan,
    TradeQuality,
)

# Risk/reward thresholds
_RR_STRONG_BUY = 3.0
_RR_BUY = 2.5
_RR_WATCHLIST = 2.0

# Pattern quality thresholds
_PATTERN_ACCEPTABLE = 50


class TradeEngine:
    """Trade Planning Engine.

    Converts Composite Decision into an executable trade plan.
    """

    def evaluate(
        self,
        composite: CompositeResult,
        pattern: PatternResult | None = None,
    ) -> TradePlan:
        """Evaluate and generate a trade plan.

        Args:
            composite: Composite decision result.
            pattern:   Pattern detection result (optional).

        Returns:
            TradePlan with entry, exit, and execution details.
        """
        reasons: list[str] = []
        warnings: list[str] = []
        validation_flags: list[str] = []

        # Extract entry price from pattern
        entry_price, entry_type, entry_source = self._determine_entry(pattern, warnings)

        # Determine stop loss
        stop_loss, stop_source = self._determine_stop(pattern, entry_price, warnings)

        # Validate stop < entry
        if entry_price is not None and stop_loss is not None:
            if validate_price_relationship(entry_price, stop_loss):
                validation_flags.append("VALID_STOP")
            else:
                validation_flags.append("INVALID_STOP")
                warnings.append("Stop loss above entry price, trade rejected")
                stop_loss = None
        else:
            validation_flags.append("INVALID_STOP")

        # Calculate risk metrics
        stop_distance, risk_percent = self._calculate_risk(entry_price, stop_loss)

        # Calculate targets using risk multiple
        target_1, target_2, target_3, target_source = self._calculate_targets(
            entry_price, stop_loss,
        )

        # Calculate risk/reward ratio
        risk_reward_ratio = self._calculate_risk_reward(entry_price, stop_loss, target_1)

        # Determine position size
        position_size = composite.position_size

        # Build decision trace
        decision_trace = TradeDecisionTrace(
            entry_source=entry_source,
            stop_source=stop_source,
            target_source=target_source,
            position_size_source="composite",
            recommendation_source="composite",
        )

        # Determine trade quality
        trade_quality = self._classify_quality(composite, risk_reward_ratio, pattern)

        # Build execution checklist
        execution_checklist = self._build_checklist(
            composite, pattern, stop_loss, risk_reward_ratio,
        )

        # Determine execution status
        execution_status = self._determine_status(
            composite, pattern, stop_loss, risk_reward_ratio, entry_price,
        )

        # Calculate confidence
        confidence = self._calculate_confidence(
            composite, pattern, execution_status, execution_checklist,
        )

        # Aggregate reasons and warnings
        self._collect_reasons(reasons, composite, pattern)
        self._collect_warnings(warnings, composite, pattern)

        # Validate plan and collect validation flags
        self._validate_plan(
            entry_price, stop_loss, risk_reward_ratio, position_size, warnings, validation_flags,
        )

        return TradePlan(
            entry_price=entry_price,
            entry_type=entry_type,
            stop_loss=stop_loss,
            stop_distance=stop_distance,
            risk_percent=risk_percent,
            target_1=target_1,
            target_2=target_2,
            target_3=target_3,
            risk_reward_ratio=risk_reward_ratio,
            position_size=position_size,
            trade_quality=trade_quality,
            execution_status=execution_status,
            execution_checklist=execution_checklist[:MAX_ITEMS],
            confidence=round(confidence, 2),
            reasons=reasons[:MAX_ITEMS],
            warnings=warnings[:MAX_ITEMS],
            decision_trace=decision_trace,
            validation_flags=validation_flags,
        )

    def _determine_entry(
        self,
        pattern: PatternResult | None,
        warnings: list[str],
    ) -> tuple[float | None, EntryType, str]:
        """Determine entry price and type from pattern.

        Returns:
            Tuple of (entry_price, entry_type, source_description).
        """
        if pattern is None:
            warnings.append("No pattern data available")
            return None, EntryType.MARKET, "none"

        # Prefer breakout price if available
        if pattern.breakout_price is not None:
            return pattern.breakout_price, EntryType.BREAKOUT, "pattern.breakout_price"

        # Fall back to pivot price
        if pattern.pivot_price is not None:
            return pattern.pivot_price, EntryType.LIMIT, "pattern.pivot_price"

        # No valid entry
        warnings.append("No breakout or pivot price available")
        return None, EntryType.MARKET, "none"

    def _determine_stop(
        self,
        pattern: PatternResult | None,
        entry_price: float | None,
        warnings: list[str],
    ) -> tuple[float | None, str]:
        """Determine stop loss price.

        Returns:
            Tuple of (stop_loss, source_description).
        """
        if pattern is None:
            return None, "none"

        if pattern.stop_price is not None:
            return pattern.stop_price, "pattern.stop_price"

        # Estimate stop from entry if pattern risk not available
        if entry_price is not None:
            warnings.append("Stop price not provided, estimated from entry")
            return entry_price * 0.95, "pattern.entry_95pct"

        return None, "none"

    def _calculate_risk(
        self,
        entry_price: float | None,
        stop_loss: float | None,
    ) -> tuple[float | None, float | None]:
        """Calculate stop distance and risk percentage."""
        if entry_price is None or stop_loss is None:
            return None, None

        stop_distance = entry_price - stop_loss
        risk_percent = (stop_distance / entry_price) * 100 if entry_price > 0 else 0.0

        return round(stop_distance, 2), round(risk_percent, 2)

    def _calculate_targets(
        self,
        entry_price: float | None,
        stop_loss: float | None,
    ) -> tuple[float | None, float | None, float | None, str]:
        """Calculate targets using risk multiple (1R, 2R, 3R).

        Returns:
            Tuple of (target_1, target_2, target_3, source_description).
        """
        if entry_price is None or stop_loss is None:
            return None, None, None, "none"

        risk = entry_price - stop_loss
        if risk <= 0:
            return None, None, None, "none"

        target_1 = entry_price + risk  # 1R
        target_2 = entry_price + risk * 2  # 2R
        target_3 = entry_price + risk * 3  # 3R

        return round(target_1, 2), round(target_2, 2), round(target_3, 2), "risk_multiple"

    def _calculate_risk_reward(
        self,
        entry_price: float | None,
        stop_loss: float | None,
        target_1: float | None,
    ) -> float | None:
        """Calculate risk/reward ratio."""
        if entry_price is None or stop_loss is None or target_1 is None:
            return None

        risk = entry_price - stop_loss
        reward = target_1 - entry_price

        if risk <= 0:
            return None

        return round(reward / risk, 2)

    def _classify_quality(
        self,
        composite: CompositeResult,
        risk_reward_ratio: float | None,
        pattern: PatternResult | None,
    ) -> TradeQuality:
        """Classify trade quality based on composite and pattern risk/reward."""
        rec = composite.recommendation

        if rec == Recommendation.AVOID:
            return TradeQuality.REJECT

        if rec == Recommendation.MONITOR:
            return TradeQuality.D

        if rec == Recommendation.WATCHLIST:
            return TradeQuality.C

        # Use pattern's risk_reward if available
        rr = None
        if pattern is not None and pattern.risk_reward is not None:
            rr = pattern.risk_reward
        elif risk_reward_ratio is not None:
            rr = risk_reward_ratio

        # For Buy/Strong Buy, factor in risk/reward
        if rr is not None:
            if rr >= _RR_STRONG_BUY:
                return TradeQuality.A_PLUS
            if rr >= _RR_BUY:
                return TradeQuality.A
            if rr >= _RR_WATCHLIST:
                return TradeQuality.B
            return TradeQuality.C

        # No risk/reward data
        if rec == Recommendation.STRONG_BUY:
            return TradeQuality.A
        return TradeQuality.B

    def _build_checklist(
        self,
        composite: CompositeResult,
        pattern: PatternResult | None,
        stop_loss: float | None,
        risk_reward_ratio: float | None,
    ) -> list[str]:
        """Build ordered execution checklist."""
        checklist: list[str] = []

        # Market trend
        if composite.market_score >= 10:
            checklist.append("Market trend supportive")
        else:
            checklist.append("Market trend NOT supportive")

        # Relative strength
        if composite.relative_strength_score >= 14:
            checklist.append("Relative strength confirmed")
        else:
            checklist.append("Relative strength weak")

        # Trend quality
        if composite.trend_score >= 17:
            checklist.append("Trend quality acceptable")
        else:
            checklist.append("Trend quality poor")

        # Pattern
        if pattern is not None and pattern.score >= _PATTERN_ACCEPTABLE:
            checklist.append("Pattern confirmed")
        else:
            checklist.append("Pattern NOT confirmed")

        # Volume
        if composite.volume_score >= 14:
            checklist.append("Volume confirmed")
        else:
            checklist.append("Volume weak")

        # Stop
        if stop_loss is not None:
            checklist.append("Stop defined")
        else:
            checklist.append("Stop NOT defined")

        # Risk/reward
        if risk_reward_ratio is not None and risk_reward_ratio >= 2.0:
            checklist.append("Risk Reward >= 2")
        else:
            checklist.append("Risk Reward < 2")

        return checklist

    def _determine_status(
        self,
        composite: CompositeResult,
        pattern: PatternResult | None,
        stop_loss: float | None,
        risk_reward_ratio: float | None,
        entry_price: float | None,
    ) -> ExecutionStatus:
        """Determine execution status."""
        rec = composite.recommendation

        # REJECT conditions
        if rec == Recommendation.AVOID:
            return ExecutionStatus.REJECT

        if stop_loss is None:
            return ExecutionStatus.REJECT

        if entry_price is None:
            return ExecutionStatus.REJECT

        if pattern is None or pattern.breakout_price is None:
            if pattern is None or pattern.pivot_price is None:
                return ExecutionStatus.REJECT

        # READY conditions
        if rec in (Recommendation.STRONG_BUY, Recommendation.BUY):
            if risk_reward_ratio is not None and risk_reward_ratio >= 2.0:
                if stop_loss is not None:
                    return ExecutionStatus.READY

        # WAIT conditions
        return ExecutionStatus.WAIT

    def _calculate_confidence(
        self,
        composite: CompositeResult,
        pattern: PatternResult | None,
        execution_status: ExecutionStatus,
        checklist: list[str],
    ) -> float:
        """Calculate trade confidence."""
        # Base confidence from composite
        conf = composite.confidence

        # Pattern confidence boost/penalty
        if pattern is not None:
            pattern_factor = pattern.confidence * 0.3
            conf = conf * 0.7 + pattern_factor

        # Execution completeness
        passed = sum(1 for item in checklist if "NOT" not in item and "weak" not in item.lower())
        total = len(checklist)
        if total > 0:
            completeness = passed / total
            conf = conf * 0.8 + completeness * 20

        # Status penalty
        if execution_status == ExecutionStatus.REJECT:
            conf *= 0.3
        elif execution_status == ExecutionStatus.WAIT:
            conf *= 0.7

        return max(0.0, min(100.0, conf))

    def _collect_reasons(
        self,
        reasons: list[str],
        composite: CompositeResult,
        pattern: PatternResult | None,
    ) -> None:
        """Aggregate reasons from composite and pattern."""
        for r in composite.reasons:
            if r not in reasons:
                reasons.append(r)

        if pattern is not None:
            for r in pattern.reasons:
                if r not in reasons:
                    reasons.append(r)

    def _collect_warnings(
        self,
        warnings: list[str],
        composite: CompositeResult,
        pattern: PatternResult | None,
    ) -> None:
        """Aggregate warnings from composite and pattern."""
        for w in composite.warnings:
            if w not in warnings:
                warnings.append(w)

        if pattern is not None:
            for w in pattern.warnings:
                if w not in warnings:
                    warnings.append(w)

    def _validate_plan(
        self,
        entry_price: float | None,
        stop_loss: float | None,
        risk_reward_ratio: float | None,
        position_size: float,
        warnings: list[str],
        validation_flags: list[str],
    ) -> None:
        """Validate trade plan and add warnings and validation flags."""
        if entry_price is not None:
            validation_flags.append("VALID_ENTRY")
        else:
            validation_flags.append("INVALID_ENTRY")
            warnings.append("Missing entry price")

        if stop_loss is not None:
            if "VALID_STOP" not in validation_flags:
                validation_flags.append("VALID_STOP")
        else:
            if "INVALID_STOP" not in validation_flags:
                validation_flags.append("INVALID_STOP")
            warnings.append("Missing stop loss")

        if risk_reward_ratio is not None:
            validation_flags.append("VALID_RISK_REWARD")
            if risk_reward_ratio < 2.0:
                warnings.append("Low risk reward ratio")
        else:
            warnings.append("Missing risk reward ratio")

        if position_size > 0:
            validation_flags.append("VALID_POSITION_SIZE")

        if entry_price is not None and stop_loss is not None and entry_price - stop_loss > 0:
            validation_flags.append("VALID_TARGET")
