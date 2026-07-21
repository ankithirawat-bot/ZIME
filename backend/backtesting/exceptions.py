"""Backtesting exception hierarchy."""

from __future__ import annotations


class BacktestError(Exception):
    """Base exception for all backtest errors."""


class InsufficientDataError(BacktestError):
    """Raised when insufficient data is provided for backtesting."""

    def __init__(self, message: str) -> None:
        super().__init__(f"Insufficient data: {message}")


class InvalidOrderError(BacktestError):
    """Raised when an order is invalid."""

    def __init__(self, message: str) -> None:
        super().__init__(f"Invalid order: {message}")


class OrderExecutionError(BacktestError):
    """Raised when order execution fails."""

    def __init__(self, order_id: str, message: str) -> None:
        self.order_id = order_id
        super().__init__(f"Order execution failed for {order_id}: {message}")


class InsufficientCashError(BacktestError):
    """Raised when there is insufficient cash to execute an order."""

    def __init__(self, required: float, available: float) -> None:
        self.required = required
        self.available = available
        super().__init__(
            f"Insufficient cash: required {required:.2f}, available {available:.2f}"
        )


class InsufficientSharesError(BacktestError):
    """Raised when there are insufficient shares to execute a sell order."""

    def __init__(self, symbol: str, required: int, available: int) -> None:
        self.symbol = symbol
        self.required = required
        self.available = available
        super().__init__(
            f"Insufficient shares for {symbol}: required {required}, available {available}"
        )


class PositionNotFoundError(BacktestError):
    """Raised when a position is not found."""

    def __init__(self, symbol: str) -> None:
        self.symbol = symbol
        super().__init__(f"Position not found for {symbol}")


class BrokerError(BacktestError):
    """Raised when a broker operation fails."""

    def __init__(self, message: str) -> None:
        super().__init__(f"Broker error: {message}")


class InvalidBacktestConfigError(BacktestError):
    """Raised when backtest configuration is invalid."""

    def __init__(self, message: str) -> None:
        super().__init__(f"Invalid backtest config: {message}")


class EmptyUniverseError(BacktestError):
    """Raised when no symbols are provided for backtesting."""

    def __init__(self) -> None:
        super().__init__("No symbols provided for backtesting")


class StrategyError(BacktestError):
    """Raised when strategy evaluation fails during backtesting."""

    def __init__(self, message: str) -> None:
        super().__init__(f"Strategy error: {message}")
