"""
Simulation Engine Models.

Frozen dataclasses for portfolio simulation across execution modes.
"""

from __future__ import annotations

from abc import ABC, abstractmethod
from dataclasses import dataclass
from datetime import date
from enum import StrEnum

from backend.portfolio.models import PortfolioResult


class SimulationModeType(StrEnum):
    """Available simulation execution mode identifiers."""

    BACKTEST = "Backtest"
    WALK_FORWARD = "Walk Forward"
    PAPER = "Paper"
    MONTE_CARLO = "Monte Carlo"
    STRESS_TEST = "Stress Test"


class SimulationMode(ABC):
    """Abstract base class for all simulation execution modes.

    Each mode must implement :meth:`simulate`.
    """

    @abstractmethod
    def simulate(
        self,
        simulation_input: SimulationInput,
    ) -> tuple[
        list[EquityCurvePoint],
        list[TradeLogEntry],
        float,
        float,
    ]:
        """Execute simulation.

        Args:
            simulation_input: Full simulation input.

        Returns:
            Tuple of (equity_curve, trade_log, ending_capital, portfolio_turnover).
        """


@dataclass(frozen=True)
class SimulationConfiguration:
    """Runtime configuration for a simulation.

    Attributes:
        starting_capital:         Initial capital.
        benchmark:                Benchmark symbol (e.g. "NIFTY50").
        simulation_mode:          Execution mode identifier.
        transaction_cost_percent: Transaction cost as percentage.
        slippage_percent:         Slippage as percentage.
    """

    starting_capital: float
    benchmark: str
    simulation_mode: SimulationModeType
    transaction_cost_percent: float = 0.0
    slippage_percent: float = 0.0


@dataclass(frozen=True)
class SimulationInput:
    """Input to the simulation engine.

    Attributes:
        portfolio:     Portfolio result to simulate.
        configuration: Runtime configuration.
        start_date:    Simulation start date.
        end_date:      Simulation end date.
    """

    portfolio: PortfolioResult
    configuration: SimulationConfiguration
    start_date: date
    end_date: date


@dataclass(frozen=True)
class SimulationSummary:
    """High-level simulation statistics.

    Attributes:
        starting_capital:    Initial capital.
        ending_capital:      Final capital.
        total_return_percent: Total return percentage.
        annualized_return:   Annualized return percentage.
        maximum_drawdown:    Maximum drawdown percentage.
        win_rate:            Winning trades as percentage.
        loss_rate:           Losing trades as percentage.
        profit_factor:       Profit factor ratio.
        sharpe_ratio:        Sharpe ratio.
        sortino_ratio:       Sortino ratio.
        calmar_ratio:        Calmar ratio.
        portfolio_turnover:  Portfolio turnover percentage.
    """

    starting_capital: float
    ending_capital: float
    total_return_percent: float
    annualized_return: float
    maximum_drawdown: float
    win_rate: float
    loss_rate: float
    profit_factor: float
    sharpe_ratio: float
    sortino_ratio: float
    calmar_ratio: float
    portfolio_turnover: float


@dataclass(frozen=True)
class SimulationStatistics:
    """Detailed trade statistics.

    Attributes:
        total_trades:            Total number of trades.
        winning_trades:          Number of winning trades.
        losing_trades:           Number of losing trades.
        average_win:             Average winning trade return.
        average_loss:            Average losing trade return.
        expectancy:              Expected value per trade.
        average_holding_period:  Average holding period in days.
    """

    total_trades: int
    winning_trades: int
    losing_trades: int
    average_win: float
    average_loss: float
    expectancy: float
    average_holding_period: float


@dataclass(frozen=True)
class EquityCurvePoint:
    """A single point on the equity curve.

    Attributes:
        date:      Date of the point.
        equity:    Portfolio equity value.
        drawdown:  Drawdown from peak at this point.
    """

    date: date
    equity: float
    drawdown: float


@dataclass(frozen=True)
class TradeLogEntry:
    """A single trade in the simulation log.

    Attributes:
        symbol:        Ticker symbol.
        entry_date:    Trade entry date.
        exit_date:     Trade exit date.
        entry_price:   Entry price per share.
        exit_price:    Exit price per share.
        shares:        Number of shares traded.
        pnl:           Profit or loss.
        return_percent: Return percentage.
    """

    symbol: str
    entry_date: date
    exit_date: date
    entry_price: float
    exit_price: float
    shares: int
    pnl: float
    return_percent: float


@dataclass(frozen=True)
class SimulationDecisionTrace:
    """Trace of simulation decisions.

    Attributes:
        execution_mode: How the simulation was executed.
        metric_source:  How metrics were calculated.
        benchmark_source: How benchmark was used.
        approval_source: How trades were approved.
    """

    execution_mode: str
    metric_source: str
    benchmark_source: str
    approval_source: str


@dataclass(frozen=True)
class SimulationResult:
    """Complete simulation result.

    Attributes:
        summary:          Simulation summary statistics.
        statistics:       Detailed trade statistics.
        equity_curve:     Equity curve over time.
        drawdowns:        Drawdown series.
        trade_log:        Individual trade log.
        decision_trace:   Trace of simulation decisions.
        validation_flags: Validation outcomes.
        reasons:          Aggregated explanations.
        warnings:         Aggregated warnings.
    """

    summary: SimulationSummary
    statistics: SimulationStatistics
    equity_curve: tuple[EquityCurvePoint, ...]
    drawdowns: tuple[EquityCurvePoint, ...]
    trade_log: tuple[TradeLogEntry, ...]
    decision_trace: SimulationDecisionTrace
    validation_flags: tuple[str, ...]
    reasons: tuple[str, ...]
    warnings: tuple[str, ...]
