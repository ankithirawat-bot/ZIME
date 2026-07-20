"""
Tests for Portfolio Construction Engine.

Validates ranking, allocation, cash management, diversification,
portfolio statistics, decision trace, and all edge cases.
"""

from datetime import date

from backend.portfolio.models import PortfolioCandidate, PortfolioInput
from backend.portfolio.portfolio_engine import PortfolioEngine
from backend.risk.models import (
    ExposureStatus,
    PortfolioRiskGrade,
    RejectionReason,
    RiskDecisionTrace,
    RiskManagementResult,
    TradeRiskGrade,
)


def _risk_result(
    *,
    execution_allowed: bool = True,
    confidence: float = 80.0,
    trade_risk_grade: TradeRiskGrade = TradeRiskGrade.MODERATE,
    recommended_position_size: float = 0.10,
    capital_at_risk: float = 8.0,
    risk_per_share: float = 8.0,
    maximum_loss: float = 0.8,
    shares_to_buy: int = 10,
    portfolio_exposure: float = 10.0,
    rejection_reason: RejectionReason = RejectionReason.NONE,
    reasons: list[str] | None = None,
    warnings: list[str] | None = None,
) -> RiskManagementResult:
    """Create a risk management result for testing."""
    return RiskManagementResult(
        max_risk_percent=1.0,
        recommended_position_size=recommended_position_size,
        capital_at_risk=capital_at_risk,
        risk_per_share=risk_per_share,
        maximum_loss=maximum_loss,
        shares_to_buy=shares_to_buy,
        portfolio_exposure=portfolio_exposure,
        exposure_status=ExposureStatus.NORMAL,
        trade_risk_grade=trade_risk_grade,
        portfolio_risk_grade=PortfolioRiskGrade.MODERATE,
        execution_allowed=execution_allowed,
        rejection_reason=rejection_reason,
        decision_trace=RiskDecisionTrace(
            risk_source="default_1pct",
            position_source="composite",
            exposure_source="position_size_calculation",
            approval_source="rule_based",
            loss_source="position_size_x_risk_per_share",
        ),
        validation_flags=["VALID_STOP", "VALID_POSITION", "VALID_RISK"],
        confidence=confidence,
        reasons=reasons or ["Strong setup"],
        warnings=warnings or [],
    )


def _portfolio_input(
    candidates: list[tuple[str, RiskManagementResult]],
    available_capital: float = 100_000.0,
    evaluation_date: date | None = None,
) -> PortfolioInput:
    """Create a PortfolioInput from symbol-result pairs."""
    return PortfolioInput(
        candidates=tuple(
            PortfolioCandidate(symbol=s, risk_result=r) for s, r in candidates
        ),
        available_capital=available_capital,
        evaluation_date=evaluation_date or date.today(),
    )


class TestSinglePosition:

    def test_single_position_approved(self):
        """Single approved position should be in result."""
        engine = PortfolioEngine()
        result = engine.evaluate(_portfolio_input([("RELIANCE", _risk_result())]))
        assert len(result.positions) == 1
        assert result.positions[0].symbol == "RELIANCE"
        assert result.summary.approved_positions == 1
        assert result.summary.rejected_positions == 0

    def test_single_position_allocation(self):
        """Single position allocation should match recommended size."""
        engine = PortfolioEngine()
        result = engine.evaluate(_portfolio_input(
            [("RELIANCE", _risk_result(recommended_position_size=0.15))],
        ))
        pos = result.positions[0]
        assert pos.allocation_percent == 15.0
        assert pos.capital_allocated == 15_000.0

    def test_single_position_cash(self):
        """Cash remaining should reflect unused capital."""
        engine = PortfolioEngine()
        result = engine.evaluate(_portfolio_input(
            [("RELIANCE", _risk_result(recommended_position_size=0.10))],
        ))
        assert result.summary.cash_remaining == 90_000.0
        assert result.summary.cash_percent == 90.0
        assert result.summary.deployment_percent == 10.0


class TestMultiplePositions:

    def test_multiple_positions(self):
        """Multiple approved positions should all appear."""
        engine = PortfolioEngine()
        result = engine.evaluate(_portfolio_input([
            ("RELIANCE", _risk_result(confidence=85.0)),
            ("TCS", _risk_result(confidence=80.0)),
            ("INFY", _risk_result(confidence=75.0)),
        ]))
        assert len(result.positions) == 3
        assert result.summary.approved_positions == 3

    def test_multiple_positions_ranked(self):
        """Positions should be ranked by confidence (highest first)."""
        engine = PortfolioEngine()
        result = engine.evaluate(_portfolio_input([
            ("INFY", _risk_result(confidence=75.0)),
            ("RELIANCE", _risk_result(confidence=85.0)),
            ("TCS", _risk_result(confidence=80.0)),
        ]))
        symbols = [p.symbol for p in result.positions]
        assert symbols == ["RELIANCE", "TCS", "INFY"]

    def test_multiple_positions_rank_values(self):
        """Rank values should be sequential starting from 1."""
        engine = PortfolioEngine()
        result = engine.evaluate(_portfolio_input([
            ("RELIANCE", _risk_result(confidence=85.0)),
            ("TCS", _risk_result(confidence=80.0)),
            ("INFY", _risk_result(confidence=75.0)),
        ]))
        ranks = [p.rank for p in result.positions]
        assert ranks == [1, 2, 3]


class TestRanking:

    def test_ranking_by_confidence(self):
        """Higher confidence should rank higher."""
        engine = PortfolioEngine()
        result = engine.evaluate(_portfolio_input([
            ("A", _risk_result(confidence=50.0)),
            ("B", _risk_result(confidence=90.0)),
            ("C", _risk_result(confidence=70.0)),
        ]))
        symbols = [p.symbol for p in result.positions]
        assert symbols == ["B", "C", "A"]

    def test_ranking_by_risk_grade(self):
        """Lower risk grade should rank higher when confidence is equal."""
        engine = PortfolioEngine()
        result = engine.evaluate(_portfolio_input([
            ("HIGH_RISK", _risk_result(confidence=80.0, trade_risk_grade=TradeRiskGrade.HIGH)),
            ("LOW_RISK", _risk_result(confidence=80.0, trade_risk_grade=TradeRiskGrade.LOW)),
            ("MODERATE_RISK", _risk_result(confidence=80.0, trade_risk_grade=TradeRiskGrade.MODERATE)),
        ]))
        symbols = [p.symbol for p in result.positions]
        assert symbols == ["LOW_RISK", "MODERATE_RISK", "HIGH_RISK"]

    def test_ranking_tie_breaker_alphabetical(self):
        """Alphabetical order should break ties."""
        engine = PortfolioEngine()
        result = engine.evaluate(_portfolio_input([
            ("Z", _risk_result(confidence=80.0, trade_risk_grade=TradeRiskGrade.MODERATE)),
            ("A", _risk_result(confidence=80.0, trade_risk_grade=TradeRiskGrade.MODERATE)),
            ("M", _risk_result(confidence=80.0, trade_risk_grade=TradeRiskGrade.MODERATE)),
        ]))
        symbols = [p.symbol for p in result.positions]
        assert symbols == ["A", "M", "Z"]

    def test_ranking_deterministic(self):
        """Same input should always produce same output."""
        engine = PortfolioEngine()
        input_data = _portfolio_input([
            ("C", _risk_result(confidence=80.0)),
            ("A", _risk_result(confidence=90.0)),
            ("B", _risk_result(confidence=85.0)),
        ])
        result1 = engine.evaluate(input_data)
        result2 = engine.evaluate(input_data)
        assert result1.positions == result2.positions


class TestAllocation:

    def test_allocation_matches_recommended(self):
        """Allocation should match recommended_position_size."""
        engine = PortfolioEngine()
        result = engine.evaluate(_portfolio_input(
            [("RELIANCE", _risk_result(recommended_position_size=0.20))],
        ))
        assert result.positions[0].allocation_percent == 20.0
        assert result.positions[0].capital_allocated == 20_000.0

    def test_allocation_multiple(self):
        """Multiple positions should each get their recommended allocation."""
        engine = PortfolioEngine()
        result = engine.evaluate(_portfolio_input([
            ("A", _risk_result(recommended_position_size=0.10)),
            ("B", _risk_result(recommended_position_size=0.15)),
        ]))
        allocs = {p.symbol: p.allocation_percent for p in result.positions}
        assert allocs == {"A": 10.0, "B": 15.0}

    def test_allocation_capped_by_capital(self):
        """Position should be capped if capital is insufficient."""
        engine = PortfolioEngine()
        result = engine.evaluate(_portfolio_input(
            [("RELIANCE", _risk_result(recommended_position_size=0.50))],
            available_capital=10_000.0,
        ))
        # 50% of 10k = 5k — within available capital
        assert result.positions[0].capital_allocated == 5_000.0
        assert result.positions[0].allocation_percent == 50.0

    def test_allocation_multiple_capped(self):
        """Later positions should be capped when capital runs out."""
        engine = PortfolioEngine()
        result = engine.evaluate(_portfolio_input([
            ("A", _risk_result(recommended_position_size=0.60)),
            ("B", _risk_result(recommended_position_size=0.50)),
        ]))
        a_alloc = next(p for p in result.positions if p.symbol == "A")
        b_alloc = next(p for p in result.positions if p.symbol == "B")
        assert a_alloc.capital_allocated == 60_000.0
        assert b_alloc.capital_allocated == 40_000.0


class TestCashManagement:

    def test_cash_remaining(self):
        """Cash remaining should be total minus deployed."""
        engine = PortfolioEngine()
        result = engine.evaluate(_portfolio_input(
            [("RELIANCE", _risk_result(recommended_position_size=0.30))],
        ))
        assert result.summary.cash_remaining == 70_000.0

    def test_cash_percent(self):
        """Cash percent should be correctly calculated."""
        engine = PortfolioEngine()
        result = engine.evaluate(_portfolio_input(
            [("RELIANCE", _risk_result(recommended_position_size=0.25))],
        ))
        assert result.summary.cash_percent == 75.0

    def test_deployment_percent(self):
        """Deployment percent should match allocated percentage."""
        engine = PortfolioEngine()
        result = engine.evaluate(_portfolio_input(
            [("RELIANCE", _risk_result(recommended_position_size=0.25))],
        ))
        assert result.summary.deployment_percent == 25.0

    def test_cash_zero_capital(self):
        """Zero capital should result in zero deployment."""
        engine = PortfolioEngine()
        result = engine.evaluate(_portfolio_input(
            [("RELIANCE", _risk_result())],
            available_capital=0.0,
        ))
        assert result.summary.cash_remaining == 0.0
        assert result.summary.deployment_percent == 0.0


class TestDiversification:

    def test_single_position_diversification(self):
        """Single position should have moderate diversification."""
        engine = PortfolioEngine()
        result = engine.evaluate(_portfolio_input([("RELIANCE", _risk_result())]))
        assert result.summary.diversification_score == 50.0

    def test_multiple_positions_diversification(self):
        """More positions should increase diversification score."""
        engine = PortfolioEngine()
        result = engine.evaluate(_portfolio_input([
            ("A", _risk_result(recommended_position_size=0.10)),
            ("B", _risk_result(recommended_position_size=0.10)),
            ("C", _risk_result(recommended_position_size=0.10)),
        ]))
        assert result.summary.diversification_score > 50.0

    def test_concentrated_portfolio_low_diversification(self):
        """Concentrated portfolio should have lower diversification."""
        engine = PortfolioEngine()
        result = engine.evaluate(_portfolio_input([
            ("A", _risk_result(recommended_position_size=0.80)),
            ("B", _risk_result(recommended_position_size=0.10)),
        ]))
        assert result.summary.diversification_score < 80.0

    def test_equal_weights_high_diversification(self):
        """Equal weights should have high diversification."""
        engine = PortfolioEngine()
        result = engine.evaluate(_portfolio_input([
            ("A", _risk_result(recommended_position_size=0.10)),
            ("B", _risk_result(recommended_position_size=0.10)),
            ("C", _risk_result(recommended_position_size=0.10)),
            ("D", _risk_result(recommended_position_size=0.10)),
        ]))
        assert result.summary.diversification_score > 90.0


class TestPortfolioRisk:

    def test_no_positions_risk_zero(self):
        """No positions should result in zero risk."""
        engine = PortfolioEngine()
        result = engine.evaluate(_portfolio_input([], available_capital=100_000.0))
        assert result.summary.portfolio_risk == 0.0

    def test_risk_from_positions(self):
        """Portfolio risk should reflect average position risk."""
        engine = PortfolioEngine()
        result = engine.evaluate(_portfolio_input([
            ("A", _risk_result(risk_per_share=5.0)),
            ("B", _risk_result(risk_per_share=10.0)),
        ]))
        # Average risk = 7.5, normalized = 7.5/20 * 100 = 37.5
        assert result.summary.portfolio_risk == 37.5


class TestPortfolioConfidence:

    def test_confidence_average(self):
        """Portfolio confidence should be average of position confidences."""
        engine = PortfolioEngine()
        result = engine.evaluate(_portfolio_input([
            ("A", _risk_result(confidence=80.0)),
            ("B", _risk_result(confidence=60.0)),
        ]))
        assert result.summary.portfolio_confidence == 70.0

    def test_confidence_no_positions(self):
        """No positions should result in zero confidence."""
        engine = PortfolioEngine()
        result = engine.evaluate(_portfolio_input([], available_capital=100_000.0))
        assert result.summary.portfolio_confidence == 0.0


class TestPortfolioReturn:

    def test_return_score(self):
        """Portfolio return score should reflect average expected reward."""
        engine = PortfolioEngine()
        result = engine.evaluate(_portfolio_input([
            ("A", _risk_result(capital_at_risk=10.0)),
            ("B", _risk_result(capital_at_risk=10.0)),
        ]))
        # Average reward = 10.0, normalized = 10.0/20 * 100 = 50.0
        assert result.summary.portfolio_return_score == 50.0


class TestRejectedTrades:

    def test_rejected_trades_excluded(self):
        """Rejected trades should not appear in positions."""
        engine = PortfolioEngine()
        result = engine.evaluate(_portfolio_input([
            ("RELIANCE", _risk_result(execution_allowed=True)),
            ("TCS", _risk_result(execution_allowed=False, rejection_reason=RejectionReason.MISSING_STOP)),
        ]))
        assert len(result.positions) == 1
        assert result.positions[0].symbol == "RELIANCE"
        assert result.summary.rejected_positions == 1

    def test_rejected_trades_in_warnings(self):
        """Rejected trades should appear in warnings."""
        engine = PortfolioEngine()
        result = engine.evaluate(_portfolio_input([
            ("RELIANCE", _risk_result(execution_allowed=True)),
            ("TCS", _risk_result(execution_allowed=False, rejection_reason=RejectionReason.MISSING_STOP)),
        ]))
        assert any("TCS" in w for w in result.warnings)

    def test_all_rejected(self):
        """All rejected trades should result in empty positions."""
        engine = PortfolioEngine()
        result = engine.evaluate(_portfolio_input([
            ("A", _risk_result(execution_allowed=False, rejection_reason=RejectionReason.MISSING_STOP)),
            ("B", _risk_result(execution_allowed=False, rejection_reason=RejectionReason.INVALID_STOP)),
        ]))
        assert len(result.positions) == 0
        assert result.summary.approved_positions == 0
        assert result.summary.rejected_positions == 2


class TestDecisionTrace:

    def test_decision_trace_populated(self):
        """Decision trace should be populated with deterministic values."""
        engine = PortfolioEngine()
        result = engine.evaluate(_portfolio_input([("RELIANCE", _risk_result())]))
        trace = result.decision_trace
        assert trace.ranking_source == "composite_confidence_then_risk_grade"
        assert trace.allocation_source == "recommended_position_size"
        assert trace.cash_source == "remaining_capital"
        assert trace.risk_source == "risk_engine"
        assert trace.approval_source == "execution_allowed"


class TestValidationFlags:

    def test_valid_capital_flag(self):
        """VALID_CAPITAL flag should be present for positive capital."""
        engine = PortfolioEngine()
        result = engine.evaluate(_portfolio_input([("RELIANCE", _risk_result())]))
        assert "VALID_CAPITAL" in result.validation_flags

    def test_invalid_capital_flag(self):
        """INVALID_CAPITAL flag should be present for zero capital."""
        engine = PortfolioEngine()
        result = engine.evaluate(_portfolio_input(
            [("RELIANCE", _risk_result())],
            available_capital=0.0,
        ))
        assert "INVALID_CAPITAL" in result.validation_flags


class TestReasons:

    def test_reasons_aggregated(self):
        """Reasons should be aggregated from approved trades."""
        engine = PortfolioEngine()
        result = engine.evaluate(_portfolio_input([
            ("A", _risk_result(reasons=["Strong trend"])),
            ("B", _risk_result(reasons=["Good volume"])),
        ]))
        assert "Strong trend" in result.reasons
        assert "Good volume" in result.reasons

    def test_reasons_deduplicated(self):
        """Reasons should be deduplicated."""
        engine = PortfolioEngine()
        result = engine.evaluate(_portfolio_input([
            ("A", _risk_result(reasons=["Strong trend", "Good volume"])),
            ("B", _risk_result(reasons=["Strong trend"])),
        ]))
        assert len(result.reasons) == len(set(result.reasons))

    def test_reasons_max_20(self):
        """Reasons should be capped at 20."""
        engine = PortfolioEngine()
        reasons = [f"Reason {i}" for i in range(25)]
        result = engine.evaluate(_portfolio_input([("A", _risk_result(reasons=reasons))]))
        assert len(result.reasons) <= 20


class TestWarnings:

    def test_warnings_from_rejected(self):
        """Warnings should include rejected trade info."""
        engine = PortfolioEngine()
        result = engine.evaluate(_portfolio_input([
            ("A", _risk_result(execution_allowed=True)),
            ("B", _risk_result(execution_allowed=False, rejection_reason=RejectionReason.MISSING_STOP)),
        ]))
        assert any("B" in w for w in result.warnings)

    def test_warnings_deduplicated(self):
        """Warnings should be deduplicated."""
        engine = PortfolioEngine()
        result = engine.evaluate(_portfolio_input([
            ("A", _risk_result(warnings=["High exposure"])),
            ("B", _risk_result(warnings=["High exposure"])),
        ]))
        assert len(result.warnings) == len(set(result.warnings))


class TestAllocationSummary:

    def test_allocation_summary_single(self):
        """Single position allocation summary."""
        engine = PortfolioEngine()
        result = engine.evaluate(_portfolio_input(
            [("A", _risk_result(recommended_position_size=0.15))],
        ))
        assert result.allocation.largest_position == 15.0
        assert result.allocation.smallest_position == 15.0
        assert result.allocation.average_position == 15.0

    def test_allocation_summary_multiple(self):
        """Multiple positions allocation summary."""
        engine = PortfolioEngine()
        result = engine.evaluate(_portfolio_input([
            ("A", _risk_result(recommended_position_size=0.10)),
            ("B", _risk_result(recommended_position_size=0.20)),
            ("C", _risk_result(recommended_position_size=0.15)),
        ]))
        assert result.allocation.largest_position == 20.0
        assert result.allocation.smallest_position == 10.0
        assert result.allocation.average_position == 15.0

    def test_allocation_summary_empty(self):
        """Empty portfolio allocation summary."""
        engine = PortfolioEngine()
        result = engine.evaluate(_portfolio_input([], available_capital=100_000.0))
        assert result.allocation.largest_position == 0.0
        assert result.allocation.smallest_position == 0.0
        assert result.allocation.average_position == 0.0


class TestEmptyInput:

    def test_empty_trades(self):
        """Empty trades list should produce empty portfolio."""
        engine = PortfolioEngine()
        result = engine.evaluate(_portfolio_input([], available_capital=100_000.0))
        assert len(result.positions) == 0
        assert result.summary.approved_positions == 0
        assert result.summary.rejected_positions == 0
        assert result.summary.cash_remaining == 100_000.0
        assert result.summary.deployment_percent == 0.0


class TestRegression:

    def test_typical_portfolio(self):
        """Typical multi-stock portfolio should work end-to-end."""
        engine = PortfolioEngine()
        result = engine.evaluate(_portfolio_input([
            ("RELIANCE", _risk_result(
                confidence=85.0,
                trade_risk_grade=TradeRiskGrade.LOW,
                recommended_position_size=0.15,
                risk_per_share=5.0,
                capital_at_risk=5.0,
                shares_to_buy=300,
            )),
            ("TCS", _risk_result(
                confidence=80.0,
                trade_risk_grade=TradeRiskGrade.MODERATE,
                recommended_position_size=0.10,
                risk_per_share=8.0,
                capital_at_risk=8.0,
                shares_to_buy=125,
            )),
            ("INFY", _risk_result(
                confidence=75.0,
                trade_risk_grade=TradeRiskGrade.LOW,
                recommended_position_size=0.12,
                risk_per_share=4.0,
                capital_at_risk=4.0,
                shares_to_buy=300,
            )),
        ], available_capital=200_000.0))

        # Positions exist
        assert len(result.positions) == 3

        # Ranking: RELIANCE (85) > TCS (80) > INFY (75)
        symbols = [p.symbol for p in result.positions]
        assert symbols == ["RELIANCE", "TCS", "INFY"]

        # Allocation
        total_alloc = sum(p.capital_allocated for p in result.positions)
        assert total_alloc == 200_000.0 * (0.15 + 0.10 + 0.12)

        # Cash
        assert result.summary.cash_remaining == 200_000.0 - total_alloc
        assert result.summary.cash_percent > 0

        # Confidence
        assert result.summary.portfolio_confidence == 80.0

        # Diversification
        assert result.summary.diversification_score > 0

        # Decision trace
        assert result.decision_trace.ranking_source is not None

        # Validation flags
        assert "VALID_CAPITAL" in result.validation_flags
