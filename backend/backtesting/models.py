"""Backtesting models.

Frozen dataclasses for backtesting definitions, orders, positions, and results.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from datetime import date, datetime
from enum import StrEnum
from typing import Any, Protocol, runtime_checkable

from backend.core.constants import DEFAULT_INITIAL_CAPITAL


class OrderType(StrEnum):
    """Order types for backtesting."""

    MARKET = "MARKET"
    LIMIT = "LIMIT"
    STOP = "STOP"


class OrderStatus(StrEnum):
    """Order status for backtesting."""

    PENDING = "PENDING"
    FILLED = "FILLED"
    CANCELLED = "CANCELLED"
    EXPIRED = "EXPIRED"
    REJECTED = "REJECTED"


class PositionSide(StrEnum):
    """Position side for backtesting."""

    LONG = "LONG"
    SHORT = "SHORT"


@dataclass(frozen=True)
class BacktestMetadata:
    """Metadata for a backtest run.

    Attributes:
        name:        Backtest name.
        description: Backtest description.
        version:     Schema version.
        author:      Backtest author.
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
class BacktestConfig:
    """Configuration for a backtest run.

    Attributes:
        initial_capital: Starting capital.
        start_date:      Backtest start date.
        end_date:        Backtest end date.
        symbols:         Symbols to backtest.
        benchmark:       Benchmark symbol for comparison.
        risk_free_rate:  Risk-free rate for Sharpe/Sortino calculations.
        commission:      Commission rate per trade.
        slippage:        Slippage rate per trade.
        stt_rate:        Securities Transaction Tax rate.
        exchange_rate:   Exchange transaction charges rate.
        sebi_rate:       SEBI charges rate.
        gst_rate:        GST rate.
        stamp_duty_rate: Stamp duty rate.
    """

    initial_capital: float = DEFAULT_INITIAL_CAPITAL
    start_date: date = field(default_factory=date.today)
    end_date: date = field(default_factory=date.today)
    symbols: tuple[str, ...] = field(default_factory=tuple)
    benchmark: str = ""
    risk_free_rate: float = 0.06
    commission: float = 0.0003
    slippage: float = 0.0001
    stt_rate: float = 0.001
    exchange_rate: float = 0.00003
    sebi_rate: float = 0.000001
    gst_rate: float = 0.18
    stamp_duty_rate: float = 0.00015


@dataclass(frozen=True)
class BacktestDefinition:
    """Complete backtest definition.

    Attributes:
        metadata: Backtest metadata.
        config:   Backtest configuration.
    """

    metadata: BacktestMetadata
    config: BacktestConfig


@dataclass(frozen=True)
class Order:
    """An order to be executed.

    Attributes:
        order_id:     Unique order identifier.
        symbol:       Ticker symbol.
        order_type:   Order type.
        side:         Position side.
        quantity:     Number of shares.
        price:        Order price.
        stop_price:   Stop price for stop orders.
        created_at:   Order creation timestamp.
        status:       Order status.
        filled_price: Actual fill price.
        filled_at:    Fill timestamp.
    """

    order_id: str
    symbol: str
    order_type: OrderType = OrderType.MARKET
    side: PositionSide = PositionSide.LONG
    quantity: int = 0
    price: float = 0.0
    stop_price: float = 0.0
    created_at: datetime = field(default_factory=lambda: datetime.now().astimezone())
    status: OrderStatus = OrderStatus.PENDING
    filled_price: float = 0.0
    filled_at: datetime | None = None


@dataclass(frozen=True)
class Trade:
    """A completed trade.

    Attributes:
        trade_id:       Unique trade identifier.
        symbol:         Ticker symbol.
        side:           Position side.
        quantity:       Number of shares.
        entry_price:    Entry price.
        exit_price:     Exit price.
        entry_date:     Entry date.
        exit_date:      Exit date.
        pnl:            Profit/Loss.
        pnl_pct:        Profit/Loss percentage.
        commission:     Total commission paid.
        slippage:       Total slippage cost.
        holding_period: Holding period in days.
    """

    trade_id: str
    symbol: str
    side: PositionSide = PositionSide.LONG
    quantity: int = 0
    entry_price: float = 0.0
    exit_price: float = 0.0
    entry_date: datetime = field(default_factory=lambda: datetime.now().astimezone())
    exit_date: datetime = field(default_factory=lambda: datetime.now().astimezone())
    pnl: float = 0.0
    pnl_pct: float = 0.0
    commission: float = 0.0
    slippage: float = 0.0
    holding_period: int = 0


@dataclass(frozen=True)
class Position:
    """A current position.

    Attributes:
        symbol:         Ticker symbol.
        side:           Position side.
        quantity:       Number of shares.
        average_cost:   Average cost per share.
        current_price:  Current market price.
        market_value:   Current market value.
        unrealized_pnl: Unrealized profit/loss.
        unrealized_pct: Unrealized profit/loss percentage.
        realized_pnl:   Realized profit/loss.
    """

    symbol: str
    side: PositionSide = PositionSide.LONG
    quantity: int = 0
    average_cost: float = 0.0
    current_price: float = 0.0
    market_value: float = 0.0
    unrealized_pnl: float = 0.0
    unrealized_pct: float = 0.0
    realized_pnl: float = 0.0


@dataclass(frozen=True)
class PortfolioSnapshot:
    """A snapshot of portfolio state.

    Attributes:
        timestamp:       Snapshot timestamp.
        cash:            Available cash.
        holdings_value:  Total holdings value.
        total_equity:    Total equity (cash + holdings).
        unrealized_pnl:  Total unrealized P/L.
        realized_pnl:    Total realized P/L.
        exposure:        Portfolio exposure (holdings / total_equity).
        positions:       Current positions.
    """

    timestamp: datetime = field(default_factory=lambda: datetime.now().astimezone())
    cash: float = 0.0
    holdings_value: float = 0.0
    total_equity: float = 0.0
    unrealized_pnl: float = 0.0
    realized_pnl: float = 0.0
    exposure: float = 0.0
    positions: tuple[Position, ...] = field(default_factory=tuple)


@dataclass(frozen=True)
class EquityPoint:
    """A point on the equity curve.

    Attributes:
        date:   Date of the point.
        equity: Total equity value.
        cash:   Cash value.
    """

    date: datetime = field(default_factory=lambda: datetime.now().astimezone())
    equity: float = 0.0
    cash: float = 0.0


@dataclass(frozen=True)
class DrawdownPoint:
    """A point on the drawdown curve.

    Attributes:
        date:        Date of the point.
        drawdown:    Drawdown percentage (negative).
        peak_equity: Peak equity at this point.
    """

    date: datetime = field(default_factory=lambda: datetime.now().astimezone())
    drawdown: float = 0.0
    peak_equity: float = 0.0


@dataclass(frozen=True)
class PerformanceMetrics:
    """Performance metrics for a backtest.

    Attributes:
        cagr:                Compound Annual Growth Rate.
        total_return:        Total return percentage.
        annualized_return:   Annualized return.
        sharpe_ratio:        Sharpe ratio.
        sortino_ratio:       Sortino ratio.
        calmar_ratio:        Calmar ratio.
        maximum_drawdown:    Maximum drawdown percentage.
        recovery_factor:     Recovery factor.
        win_rate:            Win rate percentage.
        loss_rate:           Loss rate percentage.
        profit_factor:       Profit factor.
        expectancy:          Expected value per trade.
        average_win:         Average winning trade.
        average_loss:        Average losing trade.
        largest_win:         Largest winning trade.
        largest_loss:        Largest losing trade.
        average_holding:     Average holding period in days.
        number_of_trades:    Total number of trades.
        exposure:            Average portfolio exposure.
    """

    cagr: float = 0.0
    total_return: float = 0.0
    annualized_return: float = 0.0
    sharpe_ratio: float = 0.0
    sortino_ratio: float = 0.0
    calmar_ratio: float = 0.0
    maximum_drawdown: float = 0.0
    recovery_factor: float = 0.0
    win_rate: float = 0.0
    loss_rate: float = 0.0
    profit_factor: float = 0.0
    expectancy: float = 0.0
    average_win: float = 0.0
    average_loss: float = 0.0
    largest_win: float = 0.0
    largest_loss: float = 0.0
    average_holding: float = 0.0
    number_of_trades: int = 0
    exposure: float = 0.0


@dataclass(frozen=True)
class BacktestStatistics:
    """Statistics for a backtest run.

    Attributes:
        total_orders:      Total orders generated.
        filled_orders:     Total orders filled.
        cancelled_orders:  Total orders cancelled.
        rejected_orders:   Total orders rejected.
        total_trades:      Total round-trip trades.
        total_commission:  Total commission paid.
        total_slippage:    Total slippage cost.
        elapsed_seconds:   Backtest execution time.
        symbols_processed: Symbols that were processed.
    """

    total_orders: int = 0
    filled_orders: int = 0
    cancelled_orders: int = 0
    rejected_orders: int = 0
    total_trades: int = 0
    total_commission: float = 0.0
    total_slippage: float = 0.0
    elapsed_seconds: float = 0.0
    symbols_processed: tuple[str, ...] = field(default_factory=tuple)


@dataclass(frozen=True)
class BacktestResult:
    """Result of a backtest run.

    Attributes:
        strategy_name: Strategy name used.
        config:        Backtest configuration.
        trades:        Completed trades.
        equity_curve:  Equity curve data.
        drawdown_curve: Drawdown curve data.
        metrics:       Performance metrics.
        statistics:    Backtest statistics.
        snapshots:     Portfolio snapshots.
        monthly_returns: Monthly return data.
        yearly_returns: Yearly return data.
        evaluated_at:  When the evaluation was performed.
    """

    strategy_name: str
    config: BacktestConfig
    trades: tuple[Trade, ...] = field(default_factory=tuple)
    equity_curve: tuple[EquityPoint, ...] = field(default_factory=tuple)
    drawdown_curve: tuple[DrawdownPoint, ...] = field(default_factory=tuple)
    metrics: PerformanceMetrics = field(default_factory=PerformanceMetrics)
    statistics: BacktestStatistics = field(default_factory=BacktestStatistics)
    snapshots: tuple[PortfolioSnapshot, ...] = field(default_factory=tuple)
    monthly_returns: tuple[tuple[str, float], ...] = field(default_factory=tuple)
    yearly_returns: tuple[tuple[str, float], ...] = field(default_factory=tuple)
    evaluated_at: datetime = field(default_factory=lambda: datetime.now().astimezone())


@runtime_checkable
class Strategy(Protocol):
    """Protocol for strategies that can be backtested."""

    def evaluate(self, data: dict[str, Any]) -> str:
        """Evaluate market data and return a signal.

        Args:
            data: Market data dictionary.

        Returns:
            Signal string ("BUY", "SELL", "HOLD").
        """
        ...
