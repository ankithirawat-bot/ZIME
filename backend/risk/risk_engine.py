"""
Risk Management Engine.

Transforms a TradePlan into a capital-preserving execution plan.
"""

from __future__ import annotations

from backend.composite.models import CompositeResult
from backend.risk.models import (
    ExposureStatus,
    PortfolioRiskGrade,
    RejectionReason,
    RiskDecisionTrace,
    RiskManagementResult,
    TradeRiskGrade,
)
from backend.trade.models import ExecutionStatus, TradePlan

# Maximum reasons/warnings
_MAX_ITEMS = 15

# Default maximum risk per trade (percent)
_DEFAULT_MAX_RISK = 1.0

# Risk/reward acceptance threshold
_MIN_RR_ACCEPTABLE = 2.0

# Exposure thresholds (percent)
_EXPOSURE_LOW = 5.0
_EXPOSURE_NORMAL = 10.0
_EXPOSURE_HIGH = 20.0

# Wide stop threshold (percent of entry)
_WIDE_STOP_THRESHOLD = 10.0


class RiskEngine:
    """Risk Management Engine.

    Transforms a TradePlan into a capital-preserving execution plan.
    """

    def evaluate(
        self,
        trade_plan: TradePlan,
        composite: CompositeResult,
    ) -> RiskManagementResult:
        """Evaluate and generate a risk management result.

        Args:
            trade_plan: Trade plan from TradeEngine.
            composite:  Composite decision result.

        Returns:
            RiskManagementResult with risk constraints and approvals.
        """
        reasons: list[str] = []
        warnings: list[str] = []
        validation_flags: list[str] = []

        # Determine max risk percent
        max_risk_percent = _DEFAULT_MAX_RISK

        # Validate trade plan inputs
        entry_price = trade_plan.entry_price
        stop_loss = trade_plan.stop_loss

        # Use composite position size as the authoritative limit
        position_size = composite.position_size

        # Validate stop
        stop_valid = self._validate_stop(entry_price, stop_loss, validation_flags, warnings)

        # Validate position
        position_valid = self._validate_position(
            position_size, composite.position_size, validation_flags, warnings,
        )

        # Validate risk/reward
        rr_valid = self._validate_risk_reward(
            trade_plan.risk_reward_ratio, validation_flags, warnings,
        )

        # Calculate capital at risk
        capital_at_risk = self._calculate_capital_at_risk(entry_price, stop_loss, reasons)

        # Risk per share
        risk_per_share = capital_at_risk

        # Calculate maximum loss
        maximum_loss = self._calculate_maximum_loss(
            position_size, capital_at_risk, reasons,
        )

        # Calculate shares to buy: Maximum Loss / Risk Per Share
        shares_to_buy = self._calculate_shares_to_buy(
            maximum_loss, risk_per_share, reasons, warnings,
        )

        # Calculate portfolio exposure
        portfolio_exposure = self._calculate_portfolio_exposure(
            position_size, reasons,
        )

        # Classify exposure
        exposure_status = self._classify_exposure(portfolio_exposure)

        # Classify trade risk grade
        trade_risk_grade = self._classify_risk_grade(
            capital_at_risk, risk_per_share, trade_plan,
        )

        # Classify portfolio risk grade
        portfolio_risk_grade = self._classify_portfolio_risk(portfolio_exposure)

        # Determine rejection reason
        rejection_reason = self._determine_rejection_reason(
            trade_plan, stop_valid, rr_valid, exposure_status,
        )

        # Determine execution allowed
        execution_allowed = self._determine_execution_allowed(
            trade_plan.execution_status, stop_valid, position_valid,
            rr_valid, trade_plan.risk_reward_ratio,
        )

        # Build decision trace
        decision_trace = RiskDecisionTrace(
            risk_source="default_1pct",
            position_source="composite",
            exposure_source="position_size_calculation",
            approval_source="rule_based",
            loss_source="position_size_x_risk_per_share",
        )

        # Calculate confidence
        confidence = self._calculate_confidence(
            trade_plan, composite, execution_allowed, validation_flags,
        )

        # Aggregate reasons and warnings from trade plan
        self._collect_reasons(reasons, trade_plan, composite)
        self._collect_warnings(warnings, trade_plan, composite)

        return RiskManagementResult(
            max_risk_percent=max_risk_percent,
            recommended_position_size=round(position_size, 4),
            capital_at_risk=capital_at_risk,
            risk_per_share=risk_per_share,
            maximum_loss=maximum_loss,
            shares_to_buy=shares_to_buy,
            portfolio_exposure=round(portfolio_exposure, 2),
            exposure_status=exposure_status,
            trade_risk_grade=trade_risk_grade,
            portfolio_risk_grade=portfolio_risk_grade,
            execution_allowed=execution_allowed,
            rejection_reason=rejection_reason,
            decision_trace=decision_trace,
            validation_flags=validation_flags,
            confidence=round(confidence, 2),
            reasons=reasons[:_MAX_ITEMS],
            warnings=warnings[:_MAX_ITEMS],
        )

    def _validate_stop(
        self,
        entry_price: float | None,
        stop_loss: float | None,
        validation_flags: list[str],
        warnings: list[str],
    ) -> bool:
        """Validate stop loss. Returns True if valid."""
        if stop_loss is None:
            validation_flags.append("INVALID_STOP")
            warnings.append("Missing stop loss")
            return False

        if entry_price is None:
            validation_flags.append("INVALID_STOP")
            warnings.append("Missing entry price for stop validation")
            return False

        if stop_loss >= entry_price:
            validation_flags.append("INVALID_STOP")
            warnings.append("Stop loss above entry price")
            return False

        validation_flags.append("VALID_STOP")
        return True

    def _validate_position(
        self,
        position_size: float,
        composite_max: float,
        validation_flags: list[str],
        warnings: list[str],
    ) -> bool:
        """Validate position size. Returns True if valid."""
        if position_size <= 0:
            validation_flags.append("INVALID_POSITION")
            warnings.append("Position size is zero")
            return False

        if position_size > composite_max:
            validation_flags.append("INVALID_POSITION")
            warnings.append("Position size exceeds composite maximum")
            return False

        validation_flags.append("VALID_POSITION")
        return True

    def _validate_risk_reward(
        self,
        risk_reward_ratio: float | None,
        validation_flags: list[str],
        warnings: list[str],
    ) -> bool:
        """Validate risk/reward ratio. Returns True if acceptable."""
        if risk_reward_ratio is None:
            validation_flags.append("INVALID_RISK")
            warnings.append("Missing risk/reward ratio")
            return False

        if risk_reward_ratio < _MIN_RR_ACCEPTABLE:
            validation_flags.append("INVALID_RISK")
            warnings.append(f"Risk/reward ratio {risk_reward_ratio} below {_MIN_RR_ACCEPTABLE}")
            return False

        validation_flags.append("VALID_RISK")
        return True

    def _calculate_capital_at_risk(
        self,
        entry_price: float | None,
        stop_loss: float | None,
        reasons: list[str],
    ) -> float | None:
        """Calculate capital at risk per share."""
        if entry_price is None or stop_loss is None:
            return None

        risk = entry_price - stop_loss
        if risk <= 0:
            return None

        reasons.append(f"Capital at risk per share: {risk:.2f}")
        return round(risk, 2)

    def _calculate_maximum_loss(
        self,
        position_size: float,
        capital_at_risk: float | None,
        reasons: list[str],
    ) -> float | None:
        """Calculate maximum loss if stop is hit."""
        if capital_at_risk is None or capital_at_risk <= 0:
            return None

        max_loss = position_size * capital_at_risk
        reasons.append(f"Maximum loss: {max_loss:.2f}")
        return round(max_loss, 4)

    def _calculate_shares_to_buy(
        self,
        maximum_loss: float | None,
        risk_per_share: float | None,
        reasons: list[str],
        warnings: list[str],
    ) -> int:
        """Calculate shares to buy.

        Formula: Maximum Loss / Risk Per Share.
        """
        if maximum_loss is None or risk_per_share is None:
            return 0

        if risk_per_share <= 0:
            warnings.append("Risk per share is zero or negative")
            return 0

        shares = int(maximum_loss / risk_per_share)
        reasons.append(f"Shares to buy: {shares}")
        return shares

    def _calculate_portfolio_exposure(
        self,
        position_size: float,
        reasons: list[str],
    ) -> float:
        """Calculate portfolio exposure."""
        exposure = position_size * 100
        reasons.append(f"Portfolio exposure: {exposure:.1f}%")
        return exposure

    def _classify_exposure(self, portfolio_exposure: float) -> ExposureStatus:
        """Classify portfolio exposure."""
        if portfolio_exposure <= _EXPOSURE_LOW:
            return ExposureStatus.LOW
        if portfolio_exposure <= _EXPOSURE_NORMAL:
            return ExposureStatus.NORMAL
        if portfolio_exposure <= _EXPOSURE_HIGH:
            return ExposureStatus.HIGH
        return ExposureStatus.EXCESSIVE

    def _classify_risk_grade(
        self,
        capital_at_risk: float | None,
        risk_per_share: float | None,
        trade_plan: TradePlan,
    ) -> TradeRiskGrade:
        """Classify trade risk grade."""
        if trade_plan.execution_status == ExecutionStatus.REJECT:
            return TradeRiskGrade.REJECT

        if capital_at_risk is None:
            return TradeRiskGrade.REJECT

        if capital_at_risk <= 2.0:
            return TradeRiskGrade.VERY_LOW
        if capital_at_risk <= 5.0:
            return TradeRiskGrade.LOW
        if capital_at_risk <= 10.0:
            return TradeRiskGrade.MODERATE
        if capital_at_risk <= 20.0:
            return TradeRiskGrade.HIGH
        return TradeRiskGrade.VERY_HIGH

    def _classify_portfolio_risk(self, portfolio_exposure: float) -> PortfolioRiskGrade:
        """Classify portfolio risk grade (independent of trade risk grade)."""
        if portfolio_exposure <= _EXPOSURE_LOW:
            return PortfolioRiskGrade.LOW
        if portfolio_exposure <= _EXPOSURE_NORMAL:
            return PortfolioRiskGrade.MODERATE
        if portfolio_exposure <= _EXPOSURE_HIGH:
            return PortfolioRiskGrade.HIGH
        return PortfolioRiskGrade.CRITICAL

    def _determine_rejection_reason(
        self,
        trade_plan: TradePlan,
        stop_valid: bool,
        rr_valid: bool,
        exposure_status: ExposureStatus,
    ) -> RejectionReason:
        """Determine deterministic rejection reason."""
        if trade_plan.execution_status != ExecutionStatus.READY:
            return RejectionReason.TRADE_NOT_READY

        if trade_plan.entry_price is None:
            return RejectionReason.INVALID_ENTRY

        if trade_plan.stop_loss is None:
            return RejectionReason.MISSING_STOP

        if trade_plan.stop_loss >= trade_plan.entry_price:
            return RejectionReason.INVALID_STOP

        if not stop_valid:
            return RejectionReason.MISSING_STOP

        if not rr_valid:
            return RejectionReason.LOW_RISK_REWARD

        if exposure_status == ExposureStatus.EXCESSIVE:
            return RejectionReason.HIGH_EXPOSURE

        return RejectionReason.NONE

    def _determine_execution_allowed(
        self,
        execution_status: ExecutionStatus,
        stop_valid: bool,
        position_valid: bool,
        rr_valid: bool,
        risk_reward_ratio: float | None,
    ) -> bool:
        """Determine if execution is allowed."""
        if execution_status != ExecutionStatus.READY:
            return False

        if not stop_valid:
            return False

        if not position_valid:
            return False

        if not rr_valid:
            return False

        if risk_reward_ratio is not None and risk_reward_ratio < _MIN_RR_ACCEPTABLE:
            return False

        return True

    def _calculate_confidence(
        self,
        trade_plan: TradePlan,
        composite: CompositeResult,
        execution_allowed: bool,
        validation_flags: list[str],
    ) -> float:
        """Calculate risk management confidence."""
        # Base confidence from trade plan and composite
        base = (trade_plan.confidence + composite.confidence) / 2

        # Validation completeness
        valid_count = sum(1 for f in validation_flags if f.startswith("VALID_"))
        total_flags = len(validation_flags)
        completeness = valid_count / total_flags if total_flags > 0 else 0.0

        conf = base * 0.7 + completeness * 30

        # Penalty if execution not allowed
        if not execution_allowed:
            conf *= 0.3

        return max(0.0, min(100.0, conf))

    def _collect_reasons(
        self,
        reasons: list[str],
        trade_plan: TradePlan,
        composite: CompositeResult,
    ) -> None:
        """Aggregate reasons from trade plan and composite."""
        for r in composite.reasons:
            if r not in reasons:
                reasons.append(r)

        for r in trade_plan.reasons:
            if r not in reasons:
                reasons.append(r)

    def _collect_warnings(
        self,
        warnings: list[str],
        trade_plan: TradePlan,
        composite: CompositeResult,
    ) -> None:
        """Aggregate warnings from trade plan and composite."""
        for w in composite.warnings:
            if w not in warnings:
                warnings.append(w)

        for w in trade_plan.warnings:
            if w not in warnings:
                warnings.append(w)
