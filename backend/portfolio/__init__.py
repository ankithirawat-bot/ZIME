"""Portfolio management engine.

Provides a production-grade portfolio management engine responsible for capital
allocation, position sizing, rebalancing, exposure control, and portfolio analytics.
"""

from __future__ import annotations

from backend.portfolio.allocation import (
    calculate_weights,
    equal_weight,
    fixed_weight,
    get_allocation_strategy,
    market_cap_weight,
    risk_weight,
    score_weight,
    validate_weights,
    volatility_weight,
)
from backend.portfolio.constraints import ConstraintValidator
from backend.portfolio.engine import PortfolioEngine
from backend.portfolio.exceptions import (
    AllocationError,
    ConstraintViolationError,
    EmptyPortfolioError,
    InsufficientFundsError,
    InvalidAllocationError,
    InvalidPortfolioConfigError,
    PortfolioError,
    PositionLimitExceededError,
    PositionNotFoundError,
    RebalanceError,
)
from backend.portfolio.factory import PortfolioFactory
from backend.portfolio.models import (
    Allocation,
    AllocationStrategy,
    PortfolioConfig,
    PortfolioDefinition,
    PortfolioHolding,
    PortfolioMetadata,
    PortfolioMetrics,
    PortfolioPosition,
    PortfolioSnapshot,
    PortfolioStatistics,
    RebalanceAction,
    RebalanceActionType,
    RebalanceFrequency,
)
from backend.portfolio.positions import PositionManager
from backend.portfolio.rebalancer import Rebalancer

__all__ = [
    "Allocation",
    "AllocationError",
    "AllocationStrategy",
    "ConstraintValidator",
    "ConstraintViolationError",
    "EmptyPortfolioError",
    "InsufficientFundsError",
    "InvalidAllocationError",
    "InvalidPortfolioConfigError",
    "PortfolioConfig",
    "PortfolioDefinition",
    "PortfolioEngine",
    "PortfolioError",
    "PortfolioFactory",
    "PortfolioHolding",
    "PortfolioMetadata",
    "PortfolioMetrics",
    "PortfolioPosition",
    "PortfolioSnapshot",
    "PortfolioStatistics",
    "PositionLimitExceededError",
    "PositionManager",
    "PositionNotFoundError",
    "RebalanceAction",
    "RebalanceActionType",
    "RebalanceError",
    "RebalanceFrequency",
    "Rebalancer",
    "calculate_weights",
    "equal_weight",
    "fixed_weight",
    "get_allocation_strategy",
    "market_cap_weight",
    "risk_weight",
    "score_weight",
    "validate_weights",
    "volatility_weight",
]
