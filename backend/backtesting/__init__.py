"""Backtesting engine.

Provides a production-grade backtesting engine capable of replaying historical
market data and evaluating strategies under realistic trading conditions.
"""

from __future__ import annotations

from backend.backtesting.broker import Broker
from backend.backtesting.engine import BacktestEngine
from backend.backtesting.exceptions import (
    BacktestError,
    EmptyUniverseError,
    InsufficientCashError,
    InsufficientDataError,
    InsufficientSharesError,
    InvalidBacktestConfigError,
    InvalidOrderError,
    OrderExecutionError,
    PositionNotFoundError,
    StrategyError,
)
from backend.backtesting.factory import BacktestFactory
from backend.backtesting.metrics import (
    calculate_cagr,
    calculate_calmar_ratio,
    calculate_drawdown_curve,
    calculate_maximum_drawdown,
    calculate_monthly_returns,
    calculate_performance_metrics,
    calculate_sharpe_ratio,
    calculate_sortino_ratio,
    calculate_total_return,
    calculate_trade_metrics,
    calculate_yearly_returns,
)
from backend.backtesting.models import (
    BacktestConfig,
    BacktestDefinition,
    BacktestMetadata,
    BacktestResult,
    BacktestStatistics,
    DrawdownPoint,
    EquityPoint,
    Order,
    OrderStatus,
    OrderType,
    PerformanceMetrics,
    PortfolioSnapshot,
    Position,
    PositionSide,
    Trade,
)
from backend.backtesting.portfolio import Portfolio
from backend.backtesting.report import BacktestReport

__all__ = [
    "BacktestConfig",
    "BacktestDefinition",
    "BacktestEngine",
    "BacktestError",
    "BacktestFactory",
    "BacktestMetadata",
    "BacktestReport",
    "BacktestResult",
    "BacktestStatistics",
    "Broker",
    "DrawdownPoint",
    "EmptyUniverseError",
    "EquityPoint",
    "InsufficientCashError",
    "InsufficientDataError",
    "InsufficientSharesError",
    "InvalidBacktestConfigError",
    "InvalidOrderError",
    "Order",
    "OrderExecutionError",
    "OrderStatus",
    "OrderType",
    "PerformanceMetrics",
    "Portfolio",
    "PortfolioSnapshot",
    "Position",
    "PositionNotFoundError",
    "PositionSide",
    "StrategyError",
    "Trade",
    "calculate_cagr",
    "calculate_calmar_ratio",
    "calculate_drawdown_curve",
    "calculate_maximum_drawdown",
    "calculate_monthly_returns",
    "calculate_performance_metrics",
    "calculate_sharpe_ratio",
    "calculate_sortino_ratio",
    "calculate_total_return",
    "calculate_trade_metrics",
    "calculate_yearly_returns",
]
