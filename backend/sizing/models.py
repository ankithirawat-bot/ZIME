"""Sizing models.

Frozen dataclasses for position sizing definitions, configurations,
requests, results, and protocols.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from datetime import datetime
from typing import Protocol, runtime_checkable


@dataclass(frozen=True)
class SizingMetadata:
    """Metadata for a sizing definition.

    Attributes:
        name:        Sizing analysis name.
        description: Sizing analysis description.
        version:     Schema version.
        author:      Sizing analysis author.
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
class SizingConfig:
    """Configuration for position sizing.

    Attributes:
        method:                 Position sizing method name.
        risk_per_trade:         Risk per trade as fraction of capital.
        max_position_size:      Maximum position size as fraction of capital.
        min_position_size:      Minimum position size as fraction of capital.
        max_portfolio_exposure: Maximum total portfolio exposure.
        max_sector_exposure:    Maximum sector exposure.
        cash_reserve:           Cash reserve as fraction of capital.
        max_leverage:           Maximum leverage (future support).
        round_lot:              Round lot size.
        min_trade_value:        Minimum trade value.
        kelly_fraction:         Fractional Kelly multiplier.
        atr_period:             ATR lookback period.
        atr_multiplier:         ATR position sizing multiplier.
        vol_target:             Volatility target for vol targeting method.
        vol_lookback:           Volatility lookback period.
        equal_risk_vol_target:  Volatility target for equal risk contribution.
        default_account_size:   Default account/capital size.
    """

    method: str = "fixed_fractional"
    risk_per_trade: float = 0.02
    max_position_size: float = 0.25
    min_position_size: float = 0.01
    max_portfolio_exposure: float = 1.0
    max_sector_exposure: float = 0.30
    cash_reserve: float = 0.05
    max_leverage: float = 1.0
    round_lot: int = 1
    min_trade_value: float = 0.0
    kelly_fraction: float = 0.25
    atr_period: int = 14
    atr_multiplier: float = 2.0
    vol_target: float = 0.15
    vol_lookback: int = 20
    equal_risk_vol_target: float = 0.15
    default_account_size: float = 1000000.0


@dataclass(frozen=True)
class SizingDefinition:
    """Complete sizing definition.

    Attributes:
        metadata: Sizing metadata.
        config:   Sizing configuration.
    """

    metadata: SizingMetadata
    config: SizingConfig


@dataclass(frozen=True)
class PositionRequest:
    """Request to size a position.

    Attributes:
        symbol:         Ticker symbol.
        price:          Current market price.
        account_size:   Total account / capital size.
        portfolio_value: Current portfolio value.
        available_cash: Available cash for trading.
        volatility:     Position volatility (for vol-aware methods).
        atr:            Average True Range (for ATR sizing).
        win_rate:       Historical win rate (for Kelly).
        avg_win:        Average win amount (for Kelly).
        avg_loss:       Average loss amount (for Kelly).
        sector:         Sector classification.
        signal_strength: Strategy signal strength.
        existing_weight: Current position weight.
        entry_price:    Entry price for existing positions.
        current_shares: Current number of shares held.
    """

    symbol: str
    price: float
    account_size: float = 0.0
    portfolio_value: float = 0.0
    available_cash: float = 0.0
    volatility: float = 0.0
    atr: float = 0.0
    win_rate: float = 0.0
    avg_win: float = 0.0
    avg_loss: float = 0.0
    sector: str = ""
    signal_strength: float = 1.0
    existing_weight: float = 0.0
    entry_price: float = 0.0
    current_shares: int = 0


@dataclass(frozen=True)
class RiskBudget:
    """Risk budget allocation.

    Attributes:
        symbol:        Ticker symbol.
        risk_weight:   Risk weight for the position.
        risk_amount:   Risk amount in currency.
        volatility:    Position volatility.
        contribution:  Risk contribution to portfolio.
    """

    symbol: str
    risk_weight: float = 0.0
    risk_amount: float = 0.0
    volatility: float = 0.0
    contribution: float = 0.0


@dataclass(frozen=True)
class PositionSizing:
    """Position sizing result.

    Attributes:
        symbol:          Ticker symbol.
        method:          Sizing method used.
        shares:          Number of shares to trade.
        value:           Position value in currency.
        weight:          Position weight as fraction of portfolio.
        price:           Price used for calculation.
        risk_amount:     Risk amount in currency.
        risk_percentage: Risk as fraction of account.
        confidence:      Sizing confidence (0.0 to 1.0).
        reason:          Human-readable explanation.
    """

    symbol: str
    method: str = ""
    shares: float = 0.0
    value: float = 0.0
    weight: float = 0.0
    price: float = 0.0
    risk_amount: float = 0.0
    risk_percentage: float = 0.0
    confidence: float = 1.0
    reason: str = ""


@dataclass(frozen=True)
class AllocationResult:
    """Allocation result for a portfolio.

    Attributes:
        positions:      Position sizing results.
        total_value:    Total allocated value.
        total_risk:     Total risk amount.
        cash_remaining: Remaining cash after allocation.
        cash_reserve:   Cash reserve held back.
        exposure:       Total portfolio exposure.
        risk_budgets:   Risk budget allocations.
        warnings:       Allocation warnings.
    """

    positions: tuple[PositionSizing, ...] = field(default_factory=tuple)
    total_value: float = 0.0
    total_risk: float = 0.0
    cash_remaining: float = 0.0
    cash_reserve: float = 0.0
    exposure: float = 0.0
    risk_budgets: tuple[RiskBudget, ...] = field(default_factory=tuple)
    warnings: tuple[str, ...] = field(default_factory=tuple)


@dataclass(frozen=True)
class SizingMetrics:
    """Sizing metrics.

    Attributes:
        total_positions:    Number of sized positions.
        total_exposure:     Total portfolio exposure.
        largest_position:   Largest position weight.
        smallest_position:  Smallest position weight.
        average_position:   Average position weight.
        concentration:      Position concentration (HHI).
        cash_ratio:         Cash to account ratio.
        leverage:           Current leverage.
        sector_exposure:    Sector exposure map.
    """

    total_positions: int = 0
    total_exposure: float = 0.0
    largest_position: float = 0.0
    smallest_position: float = 0.0
    average_position: float = 0.0
    concentration: float = 0.0
    cash_ratio: float = 0.0
    leverage: float = 1.0
    sector_exposure: dict[str, float] = field(default_factory=dict)


@dataclass(frozen=True)
class SizingStatistics:
    """Sizing statistics.

    Attributes:
        total_calculations: Total sizing calculations performed.
        constraint_violations: Number of constraint violations.
        warnings:             Sizing warnings.
        violations:           Constraint violation details.
        recommended_adjustments: Recommended adjustments.
        elapsed_seconds:      Calculation time.
    """

    total_calculations: int = 0
    constraint_violations: int = 0
    warnings: tuple[str, ...] = field(default_factory=tuple)
    violations: tuple[str, ...] = field(default_factory=tuple)
    recommended_adjustments: tuple[str, ...] = field(default_factory=tuple)
    elapsed_seconds: float = 0.0


@runtime_checkable
class SizingMethod(Protocol):
    """Protocol for position sizing methods."""

    def calculate(
        self,
        request: PositionRequest,
        config: SizingConfig,
    ) -> PositionSizing:
        """Calculate position size.

        Args:
            request: Position request with market data.
            config:  Sizing configuration.

        Returns:
            PositionSizing with calculated size.
        """
        ...

    @property
    def name(self) -> str:
        """Method name identifier."""
        ...
