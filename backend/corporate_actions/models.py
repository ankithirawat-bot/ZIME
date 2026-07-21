"""
Corporate Actions immutable models.

Frozen dataclasses describing corporate action events, batches,
and adjustment requests/results.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from datetime import date, datetime
from typing import Any

from backend.corporate_actions.types import ActionType


@dataclass(frozen=True)
class CorporateAction:
    """A single immutable corporate action event.

    Attributes:
        symbol:        Ticker symbol (e.g. "RELIANCE").
        exchange:      Exchange identifier (e.g. "NSE").
        action_type:   Type of corporate action.
        effective_date: Date the action takes effect.
        provider:      Originating provider name.
        ratio:         Split/bonus ratio (e.g. 2.0 for 2:1). None otherwise.
        cash_amount:   Cash component (dividend/rights). None otherwise.
        currency:      Currency of cash_amount (e.g. "INR").
        description:   Human readable description.
        metadata:      Provider-specific or extended attributes.
    """

    symbol: str
    exchange: str
    action_type: ActionType
    effective_date: date
    provider: str
    ratio: float | None = None
    cash_amount: float | None = None
    currency: str = "INR"
    description: str = ""
    metadata: dict[str, Any] = field(default_factory=dict)


@dataclass(frozen=True)
class CorporateActionBatch:
    """An immutable batch of corporate actions for one or more symbols.

    Attributes:
        actions:  Tuple of CorporateAction events.
        source:   Origin label (provider name or file name).
        fetched_at: When the batch was produced.
    """

    actions: tuple[CorporateAction, ...]
    source: str = ""
    fetched_at: datetime = field(default_factory=lambda: datetime.now().astimezone())


@dataclass(frozen=True)
class AdjustmentRequest:
    """Request to adjust raw prices for corporate actions.

    Attributes:
        symbol:    Ticker symbol.
        exchange:  Exchange identifier.
        raw_prices: Immutable sequence of raw OHLCV dicts.
        actions:   Corporate actions to apply (already validated).
        as_of:     Optional reference date. If None all actions apply.
    """

    symbol: str
    exchange: str
    raw_prices: tuple[dict[str, Any], ...]
    actions: tuple[CorporateAction, ...]
    as_of: date | None = None


@dataclass(frozen=True)
class AdjustedPrice:
    """A single adjusted price row.

    Attributes:
        trade_date:   Trading date.
        open:          Adjusted open.
        high:          Adjusted high.
        low:           Adjusted low.
        close:         Adjusted close.
        adjusted_close: Total-return adjusted close.
        volume:        Adjusted volume.
        raw_open:      Original open (immutable source).
        raw_high:      Original high.
        raw_low:       Original low.
        raw_close:     Original close.
        raw_volume:    Original volume.
        factor:        Cumulative adjustment factor applied.
    """

    trade_date: date
    open: float
    high: float
    low: float
    close: float
    adjusted_close: float
    volume: int
    raw_open: float
    raw_high: float
    raw_low: float
    raw_close: float
    raw_volume: int
    factor: float


@dataclass(frozen=True)
class AdjustmentResult:
    """Result of an adjustment operation.

    Attributes:
        symbol:       Ticker symbol.
        exchange:     Exchange identifier.
        prices:       Tuple of adjusted price rows.
        actions_applied: Corporate actions that affected output.
        raw_preserved: True when raw prices were never mutated.
        generated_at: When the result was produced.
    """

    symbol: str
    exchange: str
    prices: tuple[AdjustedPrice, ...]
    actions_applied: tuple[CorporateAction, ...]
    raw_preserved: bool
    generated_at: datetime = field(default_factory=lambda: datetime.now().astimezone())
