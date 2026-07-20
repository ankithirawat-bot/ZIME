"""
Tests for Risk Management Engine.

Validates risk calculation, position sizing, exposure mapping,
validation flags, decision trace, confidence, and all edge cases.
"""

from backend.composite.models import (
    CompositeResult,
    DecisionTrace,
    InvestmentGrade,
    Recommendation,
)
from backend.risk.models import ExposureStatus, PortfolioRiskGrade, RejectionReason, TradeRiskGrade
from backend.risk.risk_engine import RiskEngine
from backend.trade.models import (
    EntryType,
    ExecutionStatus,
    TradeDecisionTrace,
    TradePlan,
    TradeQuality,
)


def _strong_composite(
    rec: Recommendation = Recommendation.BUY,
    position_size: float = 0.15,
) -> CompositeResult:
    """Create a strong composite result."""
    return CompositeResult(
        overall_score=85.0,
        market_score=12.75,
        relative_strength_score=17.0,
        trend_score=21.25,
        pattern_score=17.0,
        volume_score=17.0,
        investment_grade=InvestmentGrade.A_MINUS,
        recommendation=rec,
        confidence=80.0,
        position_size=position_size,
        reasons=["Bull market", "Strong uptrend"],
        warnings=[],
        decision_trace=DecisionTrace(
            market_contribution=12.75,
            relative_strength_contribution=17.0,
            trend_contribution=21.25,
            pattern_contribution=17.0,
            volume_contribution=17.0,
        ),
    )


def _strong_trade_plan(
    execution_status: ExecutionStatus = ExecutionStatus.READY,
    risk_reward_ratio: float = 2.5,
) -> TradePlan:
    """Create a strong trade plan."""
    return TradePlan(
        entry_price=103.0,
        entry_type=EntryType.BREAKOUT,
        stop_loss=95.0,
        stop_distance=8.0,
        risk_percent=7.77,
        target_1=111.0,
        target_2=119.0,
        target_3=127.0,
        risk_reward_ratio=risk_reward_ratio,
        position_size=0.15,
        trade_quality=TradeQuality.A,
        execution_status=execution_status,
        execution_checklist=["Stop defined", "Risk Reward >= 2"],
        confidence=80.0,
        reasons=["Tight VCP"],
        warnings=[],
        decision_trace=TradeDecisionTrace(
            entry_source="pattern.breakout_price",
            stop_source="pattern.stop_price",
            target_source="risk_multiple",
            position_size_source="composite",
            recommendation_source="composite",
        ),
    )


class TestCapitalAtRisk:

    def test_capital_at_risk_calculated(self):
        """Capital at risk should be entry - stop."""
        engine = RiskEngine()
        result = engine.evaluate(
            trade_plan=_strong_trade_plan(),
            composite=_strong_composite(),
        )
        # Entry=103, Stop=95, CapitalAtRisk=8
        assert result.capital_at_risk == 8.0

    def test_capital_at_risk_none_when_no_stop(self):
        """Capital at risk should be None when stop is missing."""
        trade_plan = TradePlan(
            entry_price=103.0,
            entry_type=EntryType.BREAKOUT,
            stop_loss=None,
            stop_distance=None,
            risk_percent=None,
            target_1=None,
            target_2=None,
            target_3=None,
            risk_reward_ratio=None,
            position_size=0.15,
            trade_quality=TradeQuality.B,
            execution_status=ExecutionStatus.REJECT,
            execution_checklist=[],
            confidence=50.0,
            reasons=[],
            warnings=[],
            decision_trace=TradeDecisionTrace(
                entry_source="pattern.breakout_price",
                stop_source="none",
                target_source="none",
                position_size_source="composite",
                recommendation_source="composite",
            ),
        )
        engine = RiskEngine()
        result = engine.evaluate(
            trade_plan=trade_plan,
            composite=_strong_composite(),
        )
        assert result.capital_at_risk is None

    def test_capital_at_risk_none_when_no_entry(self):
        """Capital at risk should be None when entry is missing."""
        trade_plan = TradePlan(
            entry_price=None,
            entry_type=EntryType.MARKET,
            stop_loss=95.0,
            stop_distance=None,
            risk_percent=None,
            target_1=None,
            target_2=None,
            target_3=None,
            risk_reward_ratio=None,
            position_size=0.15,
            trade_quality=TradeQuality.B,
            execution_status=ExecutionStatus.REJECT,
            execution_checklist=[],
            confidence=50.0,
            reasons=[],
            warnings=[],
            decision_trace=TradeDecisionTrace(
                entry_source="none",
                stop_source="pattern.stop_price",
                target_source="none",
                position_size_source="composite",
                recommendation_source="composite",
            ),
        )
        engine = RiskEngine()
        result = engine.evaluate(
            trade_plan=trade_plan,
            composite=_strong_composite(),
        )
        assert result.capital_at_risk is None


class TestPositionSizing:

    def test_position_size_from_composite(self):
        """Position size should match composite."""
        engine = RiskEngine()
        result = engine.evaluate(
            trade_plan=_strong_trade_plan(),
            composite=_strong_composite(position_size=0.20),
        )
        assert result.recommended_position_size == 0.20

    def test_position_size_capped(self):
        """Position size should not exceed composite."""
        engine = RiskEngine()
        result = engine.evaluate(
            trade_plan=_strong_trade_plan(),
            composite=_strong_composite(position_size=0.05),
        )
        assert result.recommended_position_size == 0.05

    def test_position_size_zero(self):
        """Position size should be zero when composite is zero."""
        engine = RiskEngine()
        result = engine.evaluate(
            trade_plan=_strong_trade_plan(),
            composite=_strong_composite(position_size=0.0),
        )
        assert result.recommended_position_size == 0.0


class TestMaximumLoss:

    def test_maximum_loss_calculated(self):
        """Maximum loss should be position_size * capital_at_risk."""
        engine = RiskEngine()
        result = engine.evaluate(
            trade_plan=_strong_trade_plan(),
            composite=_strong_composite(position_size=0.15),
        )
        # CapitalAtRisk=8, PositionSize=0.15, MaxLoss=1.2
        assert result.maximum_loss is not None
        assert result.maximum_loss == 1.2

    def test_maximum_loss_none_when_no_risk(self):
        """Maximum loss should be None when capital at risk is None."""
        trade_plan = TradePlan(
            entry_price=103.0,
            entry_type=EntryType.BREAKOUT,
            stop_loss=None,
            stop_distance=None,
            risk_percent=None,
            target_1=None,
            target_2=None,
            target_3=None,
            risk_reward_ratio=None,
            position_size=0.15,
            trade_quality=TradeQuality.B,
            execution_status=ExecutionStatus.REJECT,
            execution_checklist=[],
            confidence=50.0,
            reasons=[],
            warnings=[],
            decision_trace=TradeDecisionTrace(
                entry_source="pattern.breakout_price",
                stop_source="none",
                target_source="none",
                position_size_source="composite",
                recommendation_source="composite",
            ),
        )
        engine = RiskEngine()
        result = engine.evaluate(
            trade_plan=trade_plan,
            composite=_strong_composite(),
        )
        assert result.maximum_loss is None


class TestExposureMapping:

    def test_low_exposure(self):
        """Low exposure for <=5%."""
        engine = RiskEngine()
        result = engine.evaluate(
            trade_plan=_strong_trade_plan(),
            composite=_strong_composite(position_size=0.05),
        )
        assert result.exposure_status == ExposureStatus.LOW

    def test_normal_exposure(self):
        """Normal exposure for <=10%."""
        engine = RiskEngine()
        result = engine.evaluate(
            trade_plan=_strong_trade_plan(),
            composite=_strong_composite(position_size=0.10),
        )
        assert result.exposure_status == ExposureStatus.NORMAL

    def test_high_exposure(self):
        """High exposure for <=20%."""
        engine = RiskEngine()
        result = engine.evaluate(
            trade_plan=_strong_trade_plan(),
            composite=_strong_composite(position_size=0.20),
        )
        assert result.exposure_status == ExposureStatus.HIGH

    def test_excessive_exposure(self):
        """Excessive exposure for >20%."""
        engine = RiskEngine()
        result = engine.evaluate(
            trade_plan=_strong_trade_plan(),
            composite=_strong_composite(position_size=0.25),
        )
        assert result.exposure_status == ExposureStatus.EXCESSIVE


class TestRiskGrade:

    def test_very_low_risk(self):
        """Very low risk for capital_at_risk <= 2."""
        trade_plan = TradePlan(
            entry_price=102.0,
            entry_type=EntryType.BREAKOUT,
            stop_loss=100.0,
            stop_distance=2.0,
            risk_percent=1.96,
            target_1=104.0,
            target_2=106.0,
            target_3=108.0,
            risk_reward_ratio=2.0,
            position_size=0.10,
            trade_quality=TradeQuality.B,
            execution_status=ExecutionStatus.READY,
            execution_checklist=["Stop defined"],
            confidence=80.0,
            reasons=[],
            warnings=[],
            decision_trace=TradeDecisionTrace(
                entry_source="pattern.breakout_price",
                stop_source="pattern.stop_price",
                target_source="risk_multiple",
                position_size_source="composite",
                recommendation_source="composite",
            ),
        )
        engine = RiskEngine()
        result = engine.evaluate(
            trade_plan=trade_plan,
            composite=_strong_composite(),
        )
        assert result.trade_risk_grade == TradeRiskGrade.VERY_LOW

    def test_low_risk(self):
        """Low risk for capital_at_risk <= 5."""
        trade_plan = TradePlan(
            entry_price=105.0,
            entry_type=EntryType.BREAKOUT,
            stop_loss=100.0,
            stop_distance=5.0,
            risk_percent=4.76,
            target_1=110.0,
            target_2=115.0,
            target_3=120.0,
            risk_reward_ratio=2.0,
            position_size=0.10,
            trade_quality=TradeQuality.B,
            execution_status=ExecutionStatus.READY,
            execution_checklist=["Stop defined"],
            confidence=80.0,
            reasons=[],
            warnings=[],
            decision_trace=TradeDecisionTrace(
                entry_source="pattern.breakout_price",
                stop_source="pattern.stop_price",
                target_source="risk_multiple",
                position_size_source="composite",
                recommendation_source="composite",
            ),
        )
        engine = RiskEngine()
        result = engine.evaluate(
            trade_plan=trade_plan,
            composite=_strong_composite(),
        )
        assert result.trade_risk_grade == TradeRiskGrade.LOW

    def test_moderate_risk(self):
        """Moderate risk for capital_at_risk <= 10."""
        engine = RiskEngine()
        result = engine.evaluate(
            trade_plan=_strong_trade_plan(),
            composite=_strong_composite(),
        )
        assert result.trade_risk_grade == TradeRiskGrade.MODERATE

    def test_high_risk(self):
        """High risk for capital_at_risk <= 20."""
        trade_plan = TradePlan(
            entry_price=120.0,
            entry_type=EntryType.BREAKOUT,
            stop_loss=100.0,
            stop_distance=20.0,
            risk_percent=16.67,
            target_1=140.0,
            target_2=160.0,
            target_3=180.0,
            risk_reward_ratio=2.0,
            position_size=0.10,
            trade_quality=TradeQuality.B,
            execution_status=ExecutionStatus.READY,
            execution_checklist=["Stop defined"],
            confidence=80.0,
            reasons=[],
            warnings=[],
            decision_trace=TradeDecisionTrace(
                entry_source="pattern.breakout_price",
                stop_source="pattern.stop_price",
                target_source="risk_multiple",
                position_size_source="composite",
                recommendation_source="composite",
            ),
        )
        engine = RiskEngine()
        result = engine.evaluate(
            trade_plan=trade_plan,
            composite=_strong_composite(),
        )
        assert result.trade_risk_grade == TradeRiskGrade.HIGH

    def test_very_high_risk(self):
        """Very high risk for capital_at_risk > 20."""
        trade_plan = TradePlan(
            entry_price=130.0,
            entry_type=EntryType.BREAKOUT,
            stop_loss=100.0,
            stop_distance=30.0,
            risk_percent=23.08,
            target_1=160.0,
            target_2=190.0,
            target_3=220.0,
            risk_reward_ratio=2.0,
            position_size=0.10,
            trade_quality=TradeQuality.B,
            execution_status=ExecutionStatus.READY,
            execution_checklist=["Stop defined"],
            confidence=80.0,
            reasons=[],
            warnings=[],
            decision_trace=TradeDecisionTrace(
                entry_source="pattern.breakout_price",
                stop_source="pattern.stop_price",
                target_source="risk_multiple",
                position_size_source="composite",
                recommendation_source="composite",
            ),
        )
        engine = RiskEngine()
        result = engine.evaluate(
            trade_plan=trade_plan,
            composite=_strong_composite(),
        )
        assert result.trade_risk_grade == TradeRiskGrade.VERY_HIGH

    def test_reject_grade(self):
        """Reject grade for rejected trade."""
        engine = RiskEngine()
        result = engine.evaluate(
            trade_plan=_strong_trade_plan(execution_status=ExecutionStatus.REJECT),
            composite=_strong_composite(),
        )
        assert result.trade_risk_grade == TradeRiskGrade.REJECT


class TestExecutionAllowed:

    def test_allowed_when_ready(self):
        """Execution allowed when trade is READY."""
        engine = RiskEngine()
        result = engine.evaluate(
            trade_plan=_strong_trade_plan(),
            composite=_strong_composite(),
        )
        assert result.execution_allowed is True

    def test_rejected_when_wait(self):
        """Execution rejected when trade is WAIT."""
        engine = RiskEngine()
        result = engine.evaluate(
            trade_plan=_strong_trade_plan(execution_status=ExecutionStatus.WAIT),
            composite=_strong_composite(),
        )
        assert result.execution_allowed is False

    def test_rejected_when_reject(self):
        """Execution rejected when trade is REJECT."""
        engine = RiskEngine()
        result = engine.evaluate(
            trade_plan=_strong_trade_plan(execution_status=ExecutionStatus.REJECT),
            composite=_strong_composite(),
        )
        assert result.execution_allowed is False

    def test_rejected_when_no_stop(self):
        """Execution rejected when stop is missing."""
        trade_plan = TradePlan(
            entry_price=103.0,
            entry_type=EntryType.BREAKOUT,
            stop_loss=None,
            stop_distance=None,
            risk_percent=None,
            target_1=None,
            target_2=None,
            target_3=None,
            risk_reward_ratio=None,
            position_size=0.15,
            trade_quality=TradeQuality.B,
            execution_status=ExecutionStatus.READY,
            execution_checklist=[],
            confidence=80.0,
            reasons=[],
            warnings=[],
            decision_trace=TradeDecisionTrace(
                entry_source="pattern.breakout_price",
                stop_source="none",
                target_source="none",
                position_size_source="composite",
                recommendation_source="composite",
            ),
        )
        engine = RiskEngine()
        result = engine.evaluate(
            trade_plan=trade_plan,
            composite=_strong_composite(),
        )
        assert result.execution_allowed is False


class TestValidationFlags:

    def test_valid_stop_flag(self):
        """VALID_STOP when stop is below entry."""
        engine = RiskEngine()
        result = engine.evaluate(
            trade_plan=_strong_trade_plan(),
            composite=_strong_composite(),
        )
        assert "VALID_STOP" in result.validation_flags

    def test_invalid_stop_flag(self):
        """INVALID_STOP when stop is missing."""
        trade_plan = TradePlan(
            entry_price=103.0,
            entry_type=EntryType.BREAKOUT,
            stop_loss=None,
            stop_distance=None,
            risk_percent=None,
            target_1=None,
            target_2=None,
            target_3=None,
            risk_reward_ratio=None,
            position_size=0.15,
            trade_quality=TradeQuality.B,
            execution_status=ExecutionStatus.REJECT,
            execution_checklist=[],
            confidence=50.0,
            reasons=[],
            warnings=[],
            decision_trace=TradeDecisionTrace(
                entry_source="pattern.breakout_price",
                stop_source="none",
                target_source="none",
                position_size_source="composite",
                recommendation_source="composite",
            ),
        )
        engine = RiskEngine()
        result = engine.evaluate(
            trade_plan=trade_plan,
            composite=_strong_composite(),
        )
        assert "INVALID_STOP" in result.validation_flags

    def test_valid_position_flag(self):
        """VALID_POSITION when position is valid."""
        engine = RiskEngine()
        result = engine.evaluate(
            trade_plan=_strong_trade_plan(),
            composite=_strong_composite(),
        )
        assert "VALID_POSITION" in result.validation_flags

    def test_invalid_position_flag(self):
        """INVALID_POSITION when position is zero."""
        engine = RiskEngine()
        result = engine.evaluate(
            trade_plan=_strong_trade_plan(),
            composite=_strong_composite(position_size=0.0),
        )
        assert "INVALID_POSITION" in result.validation_flags

    def test_valid_risk_flag(self):
        """VALID_RISK when risk/reward is acceptable."""
        engine = RiskEngine()
        result = engine.evaluate(
            trade_plan=_strong_trade_plan(risk_reward_ratio=2.5),
            composite=_strong_composite(),
        )
        assert "VALID_RISK" in result.validation_flags

    def test_invalid_risk_flag(self):
        """INVALID_RISK when risk/reward is below threshold."""
        engine = RiskEngine()
        result = engine.evaluate(
            trade_plan=_strong_trade_plan(risk_reward_ratio=1.5),
            composite=_strong_composite(),
        )
        assert "INVALID_RISK" in result.validation_flags


class TestDecisionTrace:

    def test_decision_trace_populated(self):
        """Decision trace should be populated."""
        engine = RiskEngine()
        result = engine.evaluate(
            trade_plan=_strong_trade_plan(),
            composite=_strong_composite(),
        )
        assert result.decision_trace is not None
        assert result.decision_trace.risk_source == "default_1pct"
        assert result.decision_trace.position_source == "composite"
        assert result.decision_trace.exposure_source == "position_size_calculation"
        assert result.decision_trace.approval_source == "rule_based"
        assert result.decision_trace.loss_source == "position_size_x_risk_per_share"


class TestConfidence:

    def test_confidence_range(self):
        """Confidence should be 0-100."""
        engine = RiskEngine()
        result = engine.evaluate(
            trade_plan=_strong_trade_plan(),
            composite=_strong_composite(),
        )
        assert 0 <= result.confidence <= 100

    def test_confidence_rejected_lower(self):
        """Rejected trade should have lower confidence."""
        engine = RiskEngine()
        result_ready = engine.evaluate(
            trade_plan=_strong_trade_plan(execution_status=ExecutionStatus.READY),
            composite=_strong_composite(),
        )
        result_reject = engine.evaluate(
            trade_plan=_strong_trade_plan(execution_status=ExecutionStatus.REJECT),
            composite=_strong_composite(),
        )
        assert result_reject.confidence < result_ready.confidence


class TestReasons:

    def test_reasons_aggregated(self):
        """Reasons should be aggregated."""
        engine = RiskEngine()
        result = engine.evaluate(
            trade_plan=_strong_trade_plan(),
            composite=_strong_composite(),
        )
        assert len(result.reasons) > 0

    def test_reasons_deduplicated(self):
        """Reasons should be deduplicated."""
        engine = RiskEngine()
        result = engine.evaluate(
            trade_plan=_strong_trade_plan(),
            composite=_strong_composite(),
        )
        assert len(result.reasons) == len(set(result.reasons))


class TestWarnings:

    def test_warnings_populated(self):
        """Warnings should be populated."""
        engine = RiskEngine()
        result = engine.evaluate(
            trade_plan=_strong_trade_plan(risk_reward_ratio=1.5),
            composite=_strong_composite(),
        )
        assert len(result.warnings) > 0

    def test_warnings_deduplicated(self):
        """Warnings should be deduplicated."""
        engine = RiskEngine()
        result = engine.evaluate(
            trade_plan=_strong_trade_plan(),
            composite=_strong_composite(),
        )
        assert len(result.warnings) == len(set(result.warnings))


class TestMaxRiskPercent:

    def test_max_risk_percent_default(self):
        """Max risk percent should be 1.0%."""
        engine = RiskEngine()
        result = engine.evaluate(
            trade_plan=_strong_trade_plan(),
            composite=_strong_composite(),
        )
        assert result.max_risk_percent == 1.0


class TestRiskPerShare:

    def test_risk_per_share_matches_capital_at_risk(self):
        """Risk per share should match capital at risk."""
        engine = RiskEngine()
        result = engine.evaluate(
            trade_plan=_strong_trade_plan(),
            composite=_strong_composite(),
        )
        assert result.risk_per_share == result.capital_at_risk


class TestPortfolioExposure:

    def test_portfolio_exposure_calculated(self):
        """Portfolio exposure should be position_size * 100."""
        engine = RiskEngine()
        result = engine.evaluate(
            trade_plan=_strong_trade_plan(),
            composite=_strong_composite(position_size=0.15),
        )
        assert result.portfolio_exposure == 15.0


class TestSharesToBuy:

    def test_shares_to_buy_calculated(self):
        """Shares to buy should be Maximum Loss / Risk Per Share."""
        engine = RiskEngine()
        result = engine.evaluate(
            trade_plan=_strong_trade_plan(),
            composite=_strong_composite(position_size=0.15),
        )
        # MaximumLoss=1.2, RiskPerShare=8, SharesToBuy=0
        assert result.shares_to_buy == 0

    def test_shares_to_buy_zero_when_no_risk(self):
        """Shares to buy should be zero when risk per share is None."""
        trade_plan = TradePlan(
            entry_price=103.0,
            entry_type=EntryType.BREAKOUT,
            stop_loss=None,
            stop_distance=None,
            risk_percent=None,
            target_1=None,
            target_2=None,
            target_3=None,
            risk_reward_ratio=None,
            position_size=0.15,
            trade_quality=TradeQuality.B,
            execution_status=ExecutionStatus.REJECT,
            execution_checklist=[],
            confidence=50.0,
            reasons=[],
            warnings=[],
            decision_trace=TradeDecisionTrace(
                entry_source="pattern.breakout_price",
                stop_source="none",
                target_source="none",
                position_size_source="composite",
                recommendation_source="composite",
            ),
        )
        engine = RiskEngine()
        result = engine.evaluate(
            trade_plan=trade_plan,
            composite=_strong_composite(),
        )
        assert result.shares_to_buy == 0


class TestPortfolioRiskGrade:

    def test_low_portfolio_risk(self):
        """Low portfolio risk for <=5% exposure."""
        engine = RiskEngine()
        result = engine.evaluate(
            trade_plan=_strong_trade_plan(),
            composite=_strong_composite(position_size=0.05),
        )
        assert result.portfolio_risk_grade == PortfolioRiskGrade.LOW

    def test_moderate_portfolio_risk(self):
        """Moderate portfolio risk for <=10% exposure."""
        engine = RiskEngine()
        result = engine.evaluate(
            trade_plan=_strong_trade_plan(),
            composite=_strong_composite(position_size=0.10),
        )
        assert result.portfolio_risk_grade == PortfolioRiskGrade.MODERATE

    def test_high_portfolio_risk(self):
        """High portfolio risk for <=20% exposure."""
        engine = RiskEngine()
        result = engine.evaluate(
            trade_plan=_strong_trade_plan(),
            composite=_strong_composite(position_size=0.20),
        )
        assert result.portfolio_risk_grade == PortfolioRiskGrade.HIGH

    def test_critical_portfolio_risk(self):
        """Critical portfolio risk for >20% exposure."""
        engine = RiskEngine()
        result = engine.evaluate(
            trade_plan=_strong_trade_plan(),
            composite=_strong_composite(position_size=0.25),
        )
        assert result.portfolio_risk_grade == PortfolioRiskGrade.CRITICAL


class TestRejectionReason:

    def test_rejection_reason_trade_not_ready(self):
        """Rejection reason should be TRADE_NOT_READY when trade is WAIT."""
        engine = RiskEngine()
        result = engine.evaluate(
            trade_plan=_strong_trade_plan(execution_status=ExecutionStatus.WAIT),
            composite=_strong_composite(),
        )
        assert result.rejection_reason == RejectionReason.TRADE_NOT_READY

    def test_rejection_reason_invalid_stop(self):
        """Rejection reason should be MISSING_STOP when stop is missing."""
        trade_plan = TradePlan(
            entry_price=103.0,
            entry_type=EntryType.BREAKOUT,
            stop_loss=None,
            stop_distance=None,
            risk_percent=None,
            target_1=None,
            target_2=None,
            target_3=None,
            risk_reward_ratio=None,
            position_size=0.15,
            trade_quality=TradeQuality.B,
            execution_status=ExecutionStatus.READY,
            execution_checklist=[],
            confidence=80.0,
            reasons=[],
            warnings=[],
            decision_trace=TradeDecisionTrace(
                entry_source="pattern.breakout_price",
                stop_source="none",
                target_source="none",
                position_size_source="composite",
                recommendation_source="composite",
            ),
        )
        engine = RiskEngine()
        result = engine.evaluate(
            trade_plan=trade_plan,
            composite=_strong_composite(),
        )
        assert result.rejection_reason == RejectionReason.MISSING_STOP

    def test_rejection_reason_invalid_stop_above_entry(self):
        """Rejection reason should be INVALID_STOP when stop >= entry."""
        trade_plan = TradePlan(
            entry_price=100.0,
            entry_type=EntryType.BREAKOUT,
            stop_loss=105.0,
            stop_distance=-5.0,
            risk_percent=-5.0,
            target_1=110.0,
            target_2=120.0,
            target_3=130.0,
            risk_reward_ratio=2.0,
            position_size=0.15,
            trade_quality=TradeQuality.B,
            execution_status=ExecutionStatus.READY,
            execution_checklist=[],
            confidence=80.0,
            reasons=[],
            warnings=[],
            decision_trace=TradeDecisionTrace(
                entry_source="pattern.breakout_price",
                stop_source="pattern.stop_price",
                target_source="risk_multiple",
                position_size_source="composite",
                recommendation_source="composite",
            ),
        )
        engine = RiskEngine()
        result = engine.evaluate(
            trade_plan=trade_plan,
            composite=_strong_composite(),
        )
        assert result.rejection_reason == RejectionReason.INVALID_STOP

    def test_rejection_reason_invalid_entry(self):
        """Rejection reason should be INVALID_ENTRY when entry is None."""
        trade_plan = TradePlan(
            entry_price=None,
            entry_type=EntryType.MARKET,
            stop_loss=95.0,
            stop_distance=None,
            risk_percent=None,
            target_1=None,
            target_2=None,
            target_3=None,
            risk_reward_ratio=None,
            position_size=0.15,
            trade_quality=TradeQuality.B,
            execution_status=ExecutionStatus.READY,
            execution_checklist=[],
            confidence=80.0,
            reasons=[],
            warnings=[],
            decision_trace=TradeDecisionTrace(
                entry_source="none",
                stop_source="pattern.stop_price",
                target_source="none",
                position_size_source="composite",
                recommendation_source="composite",
            ),
        )
        engine = RiskEngine()
        result = engine.evaluate(
            trade_plan=trade_plan,
            composite=_strong_composite(),
        )
        assert result.rejection_reason == RejectionReason.INVALID_ENTRY

    def test_rejection_reason_low_risk_reward(self):
        """Rejection reason should be LOW_RISK_REWARD when risk/reward is below threshold."""
        engine = RiskEngine()
        result = engine.evaluate(
            trade_plan=_strong_trade_plan(risk_reward_ratio=1.5),
            composite=_strong_composite(),
        )
        assert result.rejection_reason == RejectionReason.LOW_RISK_REWARD

    def test_rejection_reason_high_exposure(self):
        """Rejection reason should be HIGH_EXPOSURE when exposure is excessive."""
        engine = RiskEngine()
        result = engine.evaluate(
            trade_plan=_strong_trade_plan(),
            composite=_strong_composite(position_size=0.25),
        )
        assert result.rejection_reason == RejectionReason.HIGH_EXPOSURE

    def test_rejection_reason_none_when_valid(self):
        """Rejection reason should be NONE when all validations pass."""
        engine = RiskEngine()
        result = engine.evaluate(
            trade_plan=_strong_trade_plan(),
            composite=_strong_composite(),
        )
        assert result.rejection_reason == RejectionReason.NONE


class TestRegression:

    def test_ready_trade_passes(self):
        """Ready trade should pass risk management."""
        engine = RiskEngine()
        result = engine.evaluate(
            trade_plan=_strong_trade_plan(),
            composite=_strong_composite(),
        )
        assert result.execution_allowed is True
        assert result.trade_risk_grade in (TradeRiskGrade.VERY_LOW, TradeRiskGrade.LOW, TradeRiskGrade.MODERATE)
        assert result.exposure_status in (ExposureStatus.LOW, ExposureStatus.NORMAL, ExposureStatus.HIGH)

    def test_rejected_trade_fails(self):
        """Rejected trade should fail risk management."""
        engine = RiskEngine()
        result = engine.evaluate(
            trade_plan=_strong_trade_plan(execution_status=ExecutionStatus.REJECT),
            composite=_strong_composite(),
        )
        assert result.execution_allowed is False
        assert result.trade_risk_grade == TradeRiskGrade.REJECT
