"""Immutable dataclasses for the Backtesting workspace view models."""

from __future__ import annotations

from dataclasses import dataclass


@dataclass(frozen=True)
class BacktestConfiguration:
    strategy_name: str
    universe: str
    timeframe: str
    start_date: str
    end_date: str
    initial_capital: float
    commission: float
    slippage: float


@dataclass(frozen=True)
class Trade:
    trade_id: int
    symbol: str
    entry_date: str
    exit_date: str
    direction: str
    entry_price: float
    exit_price: float
    pnl: float
    return_pct: float


@dataclass(frozen=True)
class EquityPoint:
    timestamp: str
    cumulative_value: float


@dataclass(frozen=True)
class PerformanceMetrics:
    net_return: float
    cagr: float
    sharpe_ratio: float
    max_drawdown: float
    win_rate: float
    profit_factor: float
    total_trades: int
    expectancy: float


@dataclass(frozen=True)
class BacktestResult:
    configuration: BacktestConfiguration
    metrics: PerformanceMetrics
    equity_curve: list[EquityPoint]
    trades: list[Trade]
    completed_at_utc: str | None


@dataclass(frozen=True)
class BacktestingViewModel:
    configuration: BacktestConfiguration | None
    result: BacktestResult | None
    error_message: str | None
    is_running: bool
    last_run_at_utc: str | None
    controller_status: str
    backend_status: str
