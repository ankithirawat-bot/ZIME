"""
Simulation Engine.

Evaluates complete portfolios across multiple execution modes.
Stateless, deterministic, explainable.
"""

from __future__ import annotations

from backend.simulation.execution_modes import (
    BacktestMode,
    MonteCarloMode,
    PaperMode,
    StressTestMode,
    WalkForwardMode,
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
    SimulationDecisionTrace,
    SimulationInput,
    SimulationMode,
    SimulationModeType,
    SimulationResult,
    SimulationStatistics,
    SimulationSummary,
)

_MAX_REASONS: int = 20
_MAX_WARNINGS: int = 20

_MODES: dict[SimulationModeType, SimulationMode] = {
    SimulationModeType.BACKTEST: BacktestMode(),
    SimulationModeType.WALK_FORWARD: WalkForwardMode(),
    SimulationModeType.PAPER: PaperMode(),
    SimulationModeType.MONTE_CARLO: MonteCarloMode(),
    SimulationModeType.STRESS_TEST: StressTestMode(),
}


class SimulationEngine:
    """Simulation Engine.

    Evaluates portfolios across multiple execution modes.
    """

    def evaluate(
        self,
        simulation_input: SimulationInput,
    ) -> SimulationResult:
        """Evaluate and simulate a portfolio.

        Args:
            simulation_input: Simulation configuration and portfolio.

        Returns:
            SimulationResult with simulation output.
        """
        validation_flags: list[str] = []
        reasons: list[str] = []
        warnings: list[str] = []

        self._validate_input(simulation_input, validation_flags, warnings)

        config = simulation_input.configuration
        mode = _MODES.get(config.simulation_mode)
        if mode is None:
            mode = _MODES[SimulationModeType.BACKTEST]

        equity_curve, trade_log, ending_capital, turnover = mode.simulate(simulation_input)

        drawdowns = [p for p in equity_curve if p.drawdown > 0]

        trade_returns = [t.return_percent / 100 for t in trade_log]
        winning = [r for r in trade_returns if r > 0]
        losing = [r for r in trade_returns if r < 0]
        total = len(trade_returns)

        w_rate = win_rate(len(winning), total)
        l_rate = loss_rate(len(losing), total)
        pf = profit_factor(trade_returns)
        exp = expectancy(trade_returns)
        avg_win = (sum(winning) / len(winning) * 100) if winning else 0.0
        avg_loss = (sum(losing) / len(losing) * 100) if losing else 0.0

        total_return = ((ending_capital - config.starting_capital)
                        / config.starting_capital * 100) if config.starting_capital > 0 else 0.0
        years = (simulation_input.end_date - simulation_input.start_date).days / 365.25
        ann_return = cagr(config.starting_capital, ending_capital, years)
        max_dd = maximum_drawdown([p.equity for p in equity_curve]) if equity_curve else 0.0
        sr = sharpe_ratio(trade_returns)
        sort_r = sortino_ratio(trade_returns)
        cal_r = calmar_ratio(ann_return, max_dd)

        holding_days = []
        for t in trade_log:
            delta = (t.exit_date - t.entry_date).days
            holding_days.append(delta)
        avg_hold = (sum(holding_days) / len(holding_days)) if holding_days else 0.0

        summary = SimulationSummary(
            starting_capital=config.starting_capital,
            ending_capital=ending_capital,
            total_return_percent=round(total_return, 2),
            annualized_return=round(ann_return, 2),
            maximum_drawdown=round(max_dd, 2),
            win_rate=round(w_rate, 2),
            loss_rate=round(l_rate, 2),
            profit_factor=round(pf, 2),
            sharpe_ratio=round(sr, 2),
            sortino_ratio=round(sort_r, 2),
            calmar_ratio=round(cal_r, 2),
            portfolio_turnover=turnover,
        )

        statistics = SimulationStatistics(
            total_trades=total,
            winning_trades=len(winning),
            losing_trades=len(losing),
            average_win=round(avg_win, 2),
            average_loss=round(avg_loss, 2),
            expectancy=round(exp * 100, 2),
            average_holding_period=round(avg_hold, 1),
        )

        decision_trace = SimulationDecisionTrace(
            execution_mode=config.simulation_mode.value,
            metric_source="metrics.py",
            benchmark_source=config.benchmark,
            approval_source="portfolio_engine",
        )

        reasons.append(f"Simulated {config.simulation_mode.value} over {(simulation_input.end_date - simulation_input.start_date).days} days")
        reasons.append(f"Positions simulated: {len(simulation_input.portfolio.positions)}")

        if max_dd > 20:
            warnings.append(f"High maximum drawdown: {max_dd:.1f}%")
        if total > 0 and w_rate < 50:
            warnings.append(f"Low win rate: {w_rate:.1f}%")
        if config.transaction_cost_percent > 1.0:
            warnings.append(f"High transaction costs: {config.transaction_cost_percent}%")

        return SimulationResult(
            summary=summary,
            statistics=statistics,
            equity_curve=tuple(equity_curve),
            drawdowns=tuple(drawdowns),
            trade_log=tuple(trade_log),
            decision_trace=decision_trace,
            validation_flags=tuple(validation_flags),
            reasons=tuple(reasons[:_MAX_REASONS]),
            warnings=tuple(warnings[:_MAX_WARNINGS]),
        )

    def _validate_input(
        self,
        sim_input: SimulationInput,
        validation_flags: list[str],
        warnings: list[str],
    ) -> None:
        """Validate simulation input."""
        config = sim_input.configuration
        valid = True

        if config.starting_capital <= 0:
            validation_flags.append("INVALID_CAPITAL")
            warnings.append("Starting capital must be positive")
            valid = False
        else:
            validation_flags.append("VALID_CAPITAL")

        if sim_input.end_date <= sim_input.start_date:
            validation_flags.append("INVALID_DATES")
            warnings.append("End date must be after start date")
            valid = False
        else:
            validation_flags.append("VALID_DATES")

        if config.simulation_mode not in _MODES:
            validation_flags.append("INVALID_MODE")
            warnings.append(f"Unknown simulation mode: {config.simulation_mode}")
            valid = False
        else:
            validation_flags.append("VALID_MODE")

        if valid:
            validation_flags.append("VALID_PORTFOLIO")
