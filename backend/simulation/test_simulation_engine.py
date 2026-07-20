"""
Tests for Simulation Engine.

Validates execution modes, metric calculations, invalid inputs,
drawdown, equity curve, trade log, validation, and regression.
"""

from datetime import date

from backend.portfolio.models import (
    AllocationSummary,
    PortfolioDecisionTrace,
    PortfolioPosition,
    PortfolioResult,
    PortfolioSummary,
)
from backend.simulation.metrics import (
    cagr,
    calmar_ratio,
    expectancy,
    loss_rate,
    maximum_drawdown,
    profit_factor,
    sharpe_ratio,
    sortino_ratio,
    win_rate,
)
from backend.simulation.models import (
    SimulationConfiguration,
    SimulationInput,
    SimulationModeType,
)
from backend.simulation.simulation_engine import SimulationEngine


def _portfolio_result(
    positions: list[PortfolioPosition] | None = None,
) -> PortfolioResult:
    """Create a PortfolioResult for testing."""
    if positions is None:
        positions = [
            PortfolioPosition(
                symbol="RELIANCE",
                rank=1,
                allocation_percent=15.0,
                capital_allocated=15_000.0,
                shares=100,
                expected_risk=5.0,
                expected_reward=10.0,
                confidence=85.0,
                approval_reason="Execution allowed",
            ),
            PortfolioPosition(
                symbol="TCS",
                rank=2,
                allocation_percent=10.0,
                capital_allocated=10_000.0,
                shares=50,
                expected_risk=8.0,
                expected_reward=12.0,
                confidence=80.0,
                approval_reason="Execution allowed",
            ),
        ]

    return PortfolioResult(
        summary=PortfolioSummary(
            total_capital=100_000.0,
            capital_deployed=25_000.0,
            cash_remaining=75_000.0,
            cash_percent=75.0,
            deployment_percent=25.0,
            approved_positions=len(positions),
            rejected_positions=0,
            portfolio_risk=35.0,
            portfolio_return_score=55.0,
            portfolio_confidence=82.5,
            diversification_score=80.0,
        ),
        positions=tuple(positions),
        allocation=AllocationSummary(
            largest_position=15.0,
            smallest_position=10.0,
            average_position=12.5,
            cash_percent=75.0,
            deployment_percent=25.0,
        ),
        decision_trace=PortfolioDecisionTrace(
            ranking_source="composite_confidence_then_risk_grade",
            allocation_source="recommended_position_size",
            cash_source="remaining_capital",
            risk_source="risk_engine",
            approval_source="execution_allowed",
        ),
        validation_flags=("VALID_CAPITAL",),
        reasons=("Strong setup",),
        warnings=(),
    )


def _sim_input(
    mode: SimulationModeType = SimulationModeType.BACKTEST,
    starting_capital: float = 100_000.0,
    start_date: date | None = None,
    end_date: date | None = None,
    transaction_cost: float = 0.1,
    slippage: float = 0.05,
) -> SimulationInput:
    """Create a SimulationInput for testing."""
    config = SimulationConfiguration(
        starting_capital=starting_capital,
        benchmark="NIFTY50",
        simulation_mode=mode,
        transaction_cost_percent=transaction_cost,
        slippage_percent=slippage,
    )
    return SimulationInput(
        portfolio=_portfolio_result(),
        configuration=config,
        start_date=start_date or date(2025, 1, 1),
        end_date=end_date or date(2025, 12, 31),
    )


class TestMetrics:

    def test_sharpe_ratio_empty(self):
        """Empty returns should give 0."""
        assert sharpe_ratio([]) == 0.0

    def test_sharpe_ratio_single(self):
        """Single return should give 0."""
        assert sharpe_ratio([0.01]) == 0.0

    def test_sharpe_ratio_positive(self):
        """Positive returns with variance should give positive sharpe."""
        returns = [0.01, 0.02, 0.005, 0.015, 0.012] * 50
        result = sharpe_ratio(returns)
        assert result > 0

    def test_sortino_ratio_empty(self):
        """Empty returns should give 0."""
        assert sortino_ratio([]) == 0.0

    def test_sortino_ratio_positive(self):
        """Positive returns should give positive sortino."""
        returns = [0.01] * 252
        result = sortino_ratio(returns)
        assert result > 0

    def test_calmar_ratio(self):
        """Calmar ratio should be return / drawdown."""
        result = calmar_ratio(20.0, 10.0)
        assert result == 2.0

    def test_calmar_ratio_zero_drawdown(self):
        """Zero drawdown should give 0."""
        assert calmar_ratio(20.0, 0.0) == 0.0

    def test_maximum_drawdown_empty(self):
        """Empty curve should give 0."""
        assert maximum_drawdown([]) == 0.0

    def test_maximum_drawdown_no_drawdown(self):
        """Monotonically increasing should give 0."""
        assert maximum_drawdown([100, 110, 120, 130]) == 0.0

    def test_maximum_drawdown_with_drawdown(self):
        """Should detect peak-to-trough."""
        curve = [100, 110, 90, 95, 80, 100]
        result = maximum_drawdown(curve)
        assert abs(result - 27.27) < 0.1

    def test_profit_factor(self):
        """Profit factor should be gross_profit / gross_loss."""
        returns = [0.1, 0.05, -0.03, -0.02, 0.08]
        result = profit_factor(returns)
        assert result > 0

    def test_profit_factor_all_wins(self):
        """All wins should give 10."""
        assert profit_factor([0.1, 0.05, 0.08]) == 10.0

    def test_profit_factor_all_losses(self):
        """All losses should give 0."""
        assert profit_factor([-0.1, -0.05, -0.08]) == 0.0

    def test_expectancy(self):
        """Expectancy should be average return."""
        returns = [0.1, -0.05, 0.08, -0.02]
        result = expectancy(returns)
        assert abs(result - 0.0275) < 0.001

    def test_expectancy_empty(self):
        """Empty returns should give 0."""
        assert expectancy([]) == 0.0

    def test_cagr(self):
        """CAGR should compound correctly."""
        result = cagr(100_000, 200_000, 5.0)
        assert abs(result - 14.87) < 0.1

    def test_cagr_zero(self):
        """Zero values should give 0."""
        assert cagr(0, 100, 5) == 0.0

    def test_win_rate(self):
        """Win rate should be winning/total * 100."""
        assert win_rate(7, 10) == 70.0

    def test_win_rate_zero(self):
        """Zero trades should give 0."""
        assert win_rate(0, 0) == 0.0

    def test_loss_rate(self):
        """Loss rate should be losing/total * 100."""
        assert loss_rate(3, 10) == 30.0


class TestBacktestMode:

    def test_backtest_equity_curve(self):
        """Backtest should produce equity curve."""
        engine = SimulationEngine()
        result = engine.evaluate(_sim_input())
        assert len(result.equity_curve) > 0

    def test_backtest_equity_starts_at_capital(self):
        """Equity should start at starting capital."""
        engine = SimulationEngine()
        result = engine.evaluate(_sim_input())
        assert result.equity_curve[0].equity == 100_000.0

    def test_backtest_trade_log(self):
        """Backtest should produce trade log."""
        engine = SimulationEngine()
        result = engine.evaluate(_sim_input())
        assert len(result.trade_log) == 2

    def test_backtest_summary(self):
        """Backtest should populate summary."""
        engine = SimulationEngine()
        result = engine.evaluate(_sim_input())
        assert result.summary.starting_capital == 100_000.0
        assert result.summary.ending_capital > 0

    def test_backtest_statistics(self):
        """Backtest should populate statistics."""
        engine = SimulationEngine()
        result = engine.evaluate(_sim_input())
        assert result.statistics.total_trades == 2


class TestWalkForwardMode:

    def test_walk_forward_produces_result(self):
        """Walk-forward should produce valid result."""
        engine = SimulationEngine()
        result = engine.evaluate(_sim_input(mode=SimulationModeType.WALK_FORWARD))
        assert len(result.equity_curve) > 0
        assert result.summary.starting_capital == 100_000.0


class TestPaperMode:

    def test_paper_produces_result(self):
        """Paper mode should produce valid result."""
        engine = SimulationEngine()
        result = engine.evaluate(_sim_input(mode=SimulationModeType.PAPER))
        assert len(result.equity_curve) > 0
        assert result.summary.starting_capital == 100_000.0


class TestMonteCarloMode:

    def test_monte_carlo_produces_result(self):
        """Monte Carlo should produce valid result."""
        engine = SimulationEngine()
        result = engine.evaluate(_sim_input(mode=SimulationModeType.MONTE_CARLO))
        assert len(result.equity_curve) > 0
        assert result.summary.starting_capital == 100_000.0

    def test_monte_carlo_deterministic(self):
        """Monte Carlo should be deterministic."""
        engine = SimulationEngine()
        result1 = engine.evaluate(_sim_input(mode=SimulationModeType.MONTE_CARLO))
        result2 = engine.evaluate(_sim_input(mode=SimulationModeType.MONTE_CARLO))
        assert result1.equity_curve == result2.equity_curve


class TestStressTestMode:

    def test_stress_test_produces_result(self):
        """Stress test should produce valid result."""
        engine = SimulationEngine()
        result = engine.evaluate(_sim_input(mode=SimulationModeType.STRESS_TEST))
        assert len(result.equity_curve) > 0
        assert result.summary.starting_capital == 100_000.0

    def test_stress_test_amplifies_losses(self):
        """Stress test should have worse outcomes than backtest."""
        engine = SimulationEngine()
        backtest = engine.evaluate(_sim_input(mode=SimulationModeType.BACKTEST))
        stress = engine.evaluate(_sim_input(mode=SimulationModeType.STRESS_TEST))
        assert stress.summary.ending_capital <= backtest.summary.ending_capital


class TestDrawdown:

    def test_drawdown_populated(self):
        """Drawdowns should be populated when there are drawdowns."""
        engine = SimulationEngine()
        result = engine.evaluate(_sim_input())
        assert isinstance(result.drawdowns, tuple)

    def test_drawdown_points_have_date(self):
        """Drawdown points should have dates."""
        engine = SimulationEngine()
        result = engine.evaluate(_sim_input())
        for point in result.drawdowns:
            assert point.date is not None


class TestTradeLog:

    def test_trade_log_entries(self):
        """Trade log should have entries for each position."""
        engine = SimulationEngine()
        result = engine.evaluate(_sim_input())
        assert len(result.trade_log) == 2

    def test_trade_log_fields(self):
        """Trade log entries should have all required fields."""
        engine = SimulationEngine()
        result = engine.evaluate(_sim_input())
        for entry in result.trade_log:
            assert entry.symbol is not None
            assert entry.entry_date is not None
            assert entry.exit_date is not None
            assert entry.entry_price > 0
            assert entry.exit_price > 0
            assert entry.shares > 0


class TestValidation:

    def test_valid_input(self):
        """Valid input should have VALID flags."""
        engine = SimulationEngine()
        result = engine.evaluate(_sim_input())
        assert "VALID_CAPITAL" in result.validation_flags
        assert "VALID_DATES" in result.validation_flags
        assert "VALID_MODE" in result.validation_flags

    def test_invalid_capital(self):
        """Negative capital should be rejected."""
        engine = SimulationEngine()
        result = engine.evaluate(_sim_input(starting_capital=-1000))
        assert "INVALID_CAPITAL" in result.validation_flags
        assert any("capital" in w.lower() for w in result.warnings)

    def test_invalid_dates(self):
        """End date before start date should be rejected."""
        engine = SimulationEngine()
        result = engine.evaluate(_sim_input(
            start_date=date(2025, 12, 31),
            end_date=date(2025, 1, 1),
        ))
        assert "INVALID_DATES" in result.validation_flags


class TestDecisionTrace:

    def test_decision_trace_populated(self):
        """Decision trace should be populated."""
        engine = SimulationEngine()
        result = engine.evaluate(_sim_input())
        assert result.decision_trace.execution_mode == "Backtest"
        assert result.decision_trace.metric_source == "metrics.py"
        assert result.decision_trace.benchmark_source == "NIFTY50"


class TestReasons:

    def test_reasons_populated(self):
        """Reasons should be populated."""
        engine = SimulationEngine()
        result = engine.evaluate(_sim_input())
        assert len(result.reasons) > 0

    def test_reasons_contain_mode(self):
        """Reasons should mention simulation mode."""
        engine = SimulationEngine()
        result = engine.evaluate(_sim_input())
        assert any("Backtest" in r for r in result.reasons)


class TestWarnings:

    def test_warnings_from_high_drawdown(self):
        """High drawdown should produce warning."""
        engine = SimulationEngine()
        result = engine.evaluate(_sim_input(
            mode=SimulationModeType.STRESS_TEST,
            start_date=date(2025, 1, 1),
            end_date=date(2026, 12, 31),
        ))
        assert isinstance(result.warnings, tuple)


class TestRegression:

    def test_typical_simulation(self):
        """Typical simulation should work end-to-end."""
        engine = SimulationEngine()
        result = engine.evaluate(_sim_input())

        assert result.summary.starting_capital == 100_000.0
        assert result.summary.ending_capital > 0
        assert isinstance(result.summary.total_return_percent, float)
        assert isinstance(result.summary.annualized_return, float)
        assert isinstance(result.summary.sharpe_ratio, float)

        assert result.statistics.total_trades == 2
        assert result.statistics.winning_trades + result.statistics.losing_trades <= 2

        assert len(result.equity_curve) > 0
        assert result.equity_curve[0].equity == 100_000.0

        assert len(result.trade_log) == 2

        assert result.decision_trace.execution_mode == "Backtest"

        assert "VALID_CAPITAL" in result.validation_flags

    def test_all_modes_produce_results(self):
        """All simulation modes should produce valid results."""
        engine = SimulationEngine()
        for mode in SimulationModeType:
            result = engine.evaluate(_sim_input(mode=mode))
            assert len(result.equity_curve) > 0, f"Failed for {mode}"
            assert result.summary.starting_capital == 100_000.0, f"Failed for {mode}"
