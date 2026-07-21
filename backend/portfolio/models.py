"""Portfolio models.

Frozen dataclasses for portfolio definitions, positions, allocations, and results.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from datetime import datetime
from enum import StrEnum
from typing import Any, Protocol, runtime_checkable


class AllocationStrategy(StrEnum):
    """Allocation strategies."""

    EQUAL_WEIGHT = "EQUAL_WEIGHT"
    FIXED_WEIGHT = "FIXED_WEIGHT"
    RISK_WEIGHT = "RISK_WEIGHT"
    VOLATILITY_WEIGHT = "VOLATILITY_WEIGHT"
    SCORE_WEIGHT = "SCORE_WEIGHT"
    MARKET_CAP_WEIGHT = "MARKET_CAP_WEIGHT"


class RebalanceFrequency(StrEnum):
    """Rebalance frequency."""

    DAILY = "DAILY"
    WEEKLY = "WEEKLY"
    MONTHLY = "MONTHLY"
    QUARTERLY = "QUARTERLY"
    THRESHOLD = "THRESHOLD"
    DRIFT = "DRIFT"


class RebalanceActionType(StrEnum):
    """Rebalance action types."""

    BUY = "BUY"
    SELL = "SELL"
    HOLD = "HOLD"


@dataclass(frozen=True)
class PortfolioMetadata:
    """Metadata for a portfolio definition.

    Attributes:
        name:        Portfolio name.
        description: Portfolio description.
        version:     Schema version.
        author:      Portfolio author.
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
class PortfolioConfig:
    """Configuration for portfolio management.

    Attributes:
        initial_capital:         Starting capital.
        allocation_strategy:     Allocation strategy to use.
        rebalance_frequency:     Rebalance frequency.
        rebalance_threshold:     Threshold for threshold-based rebalancing.
        drift_threshold:         Drift threshold for drift-based rebalancing.
        max_positions:           Maximum number of positions.
        min_positions:           Minimum number of positions.
        max_position_size:       Maximum position size (0.0 to 1.0).
        min_position_size:       Minimum position size (0.0 to 1.0).
        max_sector_exposure:     Maximum sector exposure (0.0 to 1.0).
        max_stock_exposure:      Maximum single stock exposure (0.0 to 1.0).
        cash_reserve:            Cash reserve (0.0 to 1.0).
        liquidity_threshold:     Liquidity threshold.
        transaction_cost:        Transaction cost rate.
        risk_free_rate:          Risk-free rate for Sharpe/Sortino calculations.
    """

    initial_capital: float = 1_000_000.0
    allocation_strategy: AllocationStrategy = AllocationStrategy.EQUAL_WEIGHT
    rebalance_frequency: RebalanceFrequency = RebalanceFrequency.MONTHLY
    rebalance_threshold: float = 0.05
    drift_threshold: float = 0.03
    max_positions: int = 50
    min_positions: int = 5
    max_position_size: float = 0.20
    min_position_size: float = 0.02
    max_sector_exposure: float = 0.30
    max_stock_exposure: float = 0.25
    cash_reserve: float = 0.05
    liquidity_threshold: float = 0.01
    transaction_cost: float = 0.001
    risk_free_rate: float = 0.06


@dataclass(frozen=True)
class PortfolioDefinition:
    """Complete portfolio definition.

    Attributes:
        metadata: Portfolio metadata.
        config:   Portfolio configuration.
    """

    metadata: PortfolioMetadata
    config: PortfolioConfig


@dataclass(frozen=True)
class PortfolioHolding:
    """A holding in the portfolio.

    Attributes:
        symbol:       Ticker symbol.
        quantity:     Number of shares.
        average_cost: Average cost per share.
        current_price: Current market price.
        market_value: Current market value.
        allocation:   Allocation percentage (0.0 to 1.0).
        sector:       Sector classification.
    """

    symbol: str
    quantity: int = 0
    average_cost: float = 0.0
    current_price: float = 0.0
    market_value: float = 0.0
    allocation: float = 0.0
    sector: str = ""


@dataclass(frozen=True)
class PortfolioPosition:
    """A position in the portfolio with P/L tracking.

    Attributes:
        symbol:          Ticker symbol.
        quantity:        Number of shares.
        average_cost:    Average cost per share.
        current_price:   Current market price.
        market_value:    Current market value.
        unrealized_pnl:  Unrealized profit/loss.
        unrealized_pct:  Unrealized profit/loss percentage.
        realized_pnl:    Realized profit/loss.
        holding_period:  Holding period in days.
        allocation:      Allocation percentage (0.0 to 1.0).
        sector:          Sector classification.
        weight:          Portfolio weight (0.0 to 1.0).
    """

    symbol: str
    quantity: int = 0
    average_cost: float = 0.0
    current_price: float = 0.0
    market_value: float = 0.0
    unrealized_pnl: float = 0.0
    unrealized_pct: float = 0.0
    realized_pnl: float = 0.0
    holding_period: int = 0
    allocation: float = 0.0
    sector: str = ""
    weight: float = 0.0


@dataclass(frozen=True)
class Allocation:
    """An allocation target for a symbol.

    Attributes:
        symbol:     Ticker symbol.
        weight:     Target weight (0.0 to 1.0).
        amount:     Target allocation amount.
        sector:     Sector classification.
        priority:   Allocation priority (lower = higher priority).
    """

    symbol: str
    weight: float = 0.0
    amount: float = 0.0
    sector: str = ""
    priority: int = 0


@dataclass(frozen=True)
class RebalanceAction:
    """A rebalancing action.

    Attributes:
        symbol:       Ticker symbol.
        action_type:  Action type (BUY/SELL/HOLD).
        quantity:     Number of shares.
        current_weight: Current portfolio weight.
        target_weight:  Target portfolio weight.
        current_value:  Current position value.
        target_value:   Target position value.
        drift:         Weight drift (current - target).
    """

    symbol: str
    action_type: RebalanceActionType = RebalanceActionType.HOLD
    quantity: int = 0
    current_weight: float = 0.0
    target_weight: float = 0.0
    current_value: float = 0.0
    target_value: float = 0.0
    drift: float = 0.0


@dataclass(frozen=True)
class PortfolioSnapshot:
    """A snapshot of portfolio state.

    Attributes:
        timestamp:        Snapshot timestamp.
        cash:             Available cash.
        holdings_value:   Total holdings value.
        total_equity:     Total equity (cash + holdings).
        unrealized_pnl:   Total unrealized P/L.
        realized_pnl:     Total realized P/L.
        exposure:         Portfolio exposure (holdings / total equity).
        positions:        Current positions.
        cash_reserve:     Cash reserve amount.
        available_cash:   Available cash after reserve.
    """

    timestamp: datetime = field(default_factory=lambda: datetime.now().astimezone())
    cash: float = 0.0
    holdings_value: float = 0.0
    total_equity: float = 0.0
    unrealized_pnl: float = 0.0
    realized_pnl: float = 0.0
    exposure: float = 0.0
    positions: tuple[PortfolioPosition, ...] = field(default_factory=tuple)
    cash_reserve: float = 0.0
    available_cash: float = 0.0


@dataclass(frozen=True)
class PortfolioMetrics:
    """Portfolio performance metrics.

    Attributes:
        portfolio_return:      Portfolio return.
        alpha:                 Alpha (vs benchmark).
        beta:                  Beta (vs benchmark).
        volatility:           Portfolio volatility.
        sharpe_ratio:          Sharpe ratio.
        maximum_drawdown:      Maximum drawdown.
        turnover:              Portfolio turnover.
        concentration_index:   Concentration index (Herfindahl).
        cash_utilization:      Cash utilization rate.
        sector_exposure:       Sector exposure breakdown.
    """

    portfolio_return: float = 0.0
    alpha: float = 0.0
    beta: float = 0.0
    volatility: float = 0.0
    sharpe_ratio: float = 0.0
    maximum_drawdown: float = 0.0
    turnover: float = 0.0
    concentration_index: float = 0.0
    cash_utilization: float = 0.0
    sector_exposure: dict[str, float] = field(default_factory=dict)


@dataclass(frozen=True)
class PortfolioStatistics:
    """Statistics for portfolio operations.

    Attributes:
        total_positions:     Total number of positions.
        total_trades:        Total trades executed.
        total_turnover:      Total turnover.
        total_commission:    Total commission paid.
        elapsed_seconds:     Operation time.
        rebalance_count:     Number of rebalances performed.
    """

    total_positions: int = 0
    total_trades: int = 0
    total_turnover: float = 0.0
    total_commission: float = 0.0
    elapsed_seconds: float = 0.0
    rebalance_count: int = 0


@runtime_checkable
class AllocationStrategyProtocol(Protocol):
    """Protocol for allocation strategies."""

    def calculate_weights(
        self,
        symbols: tuple[str, ...],
        data: dict[str, Any],
        config: PortfolioConfig,
    ) -> dict[str, float]:
        """Calculate allocation weights.

        Args:
            symbols: Symbols to allocate.
            data:    Market data for calculations.
            config:  Portfolio configuration.

        Returns:
            Dictionary of symbol -> weight.
        """
        ...
