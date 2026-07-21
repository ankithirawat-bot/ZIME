"""Portfolio exception hierarchy."""

from __future__ import annotations


class PortfolioError(Exception):
    """Base exception for all portfolio errors."""


class InvalidPortfolioConfigError(PortfolioError):
    """Raised when portfolio configuration is invalid."""

    def __init__(self, message: str) -> None:
        super().__init__(f"Invalid portfolio config: {message}")


class ConstraintViolationError(PortfolioError):
    """Raised when a constraint is violated."""

    def __init__(self, constraint: str, message: str) -> None:
        self.constraint = constraint
        super().__init__(f"Constraint violation ({constraint}): {message}")


class InsufficientFundsError(PortfolioError):
    """Raised when there are insufficient funds for an allocation."""

    def __init__(self, required: float, available: float) -> None:
        self.required = required
        self.available = available
        super().__init__(
            f"Insufficient funds: required {required:.2f}, available {available:.2f}"
        )


class PositionLimitExceededError(PortfolioError):
    """Raised when position limit is exceeded."""

    def __init__(self, limit: int, current: int) -> None:
        self.limit = limit
        self.current = current
        super().__init__(f"Position limit exceeded: limit {limit}, current {current}")


class AllocationError(PortfolioError):
    """Raised when allocation fails."""

    def __init__(self, message: str) -> None:
        super().__init__(f"Allocation error: {message}")


class RebalanceError(PortfolioError):
    """Raised when rebalancing fails."""

    def __init__(self, message: str) -> None:
        super().__init__(f"Rebalance error: {message}")


class PositionNotFoundError(PortfolioError):
    """Raised when a position is not found."""

    def __init__(self, symbol: str) -> None:
        self.symbol = symbol
        super().__init__(f"Position not found for {symbol}")


class EmptyPortfolioError(PortfolioError):
    """Raised when the portfolio is empty."""

    def __init__(self) -> None:
        super().__init__("Portfolio is empty")


class InvalidAllocationError(PortfolioError):
    """Raised when allocation weights are invalid."""

    def __init__(self, message: str) -> None:
        super().__init__(f"Invalid allocation: {message}")
