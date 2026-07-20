"""
Market Data Platform models.

Frozen dataclasses and enumerations for data requests, responses,
and validation results.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from datetime import date, datetime
from enum import StrEnum


class DataType(StrEnum):
    """Types of market data that can be requested."""

    PRICE_DAILY = "price_daily"
    PRICE_INTRADAY = "price_intraday"
    CORPORATE_ACTIONS = "corporate_actions"
    FINANCIALS = "financials"
    RATIOS = "ratios"
    SHAREHOLDING = "shareholding"
    DIVIDENDS = "dividends"
    SPLITS = "splits"
    BONUS = "bonus"
    BUYBACKS = "buybacks"
    RIGHTS = "rights"
    EARNINGS = "earnings"
    NEWS = "news"
    BLOCK_DEALS = "block_deals"
    BULK_DEALS = "bulk_deals"
    INSIDER_TRADES = "insider_trades"


class DataStatus(StrEnum):
    """Status of a data response."""

    SUCCESS = "success"
    PARTIAL = "partial"
    FAILED = "failed"
    CACHED = "cached"


@dataclass(frozen=True)
class DataRequest:
    """Immutable request for market data.

    Attributes:
        symbol:              Ticker symbol (e.g. "RELIANCE").
        exchange:            Exchange identifier (e.g. "NSE", "BSE").
        data_type:           Type of data requested.
        start_date:          Inclusive start of the data window.
        end_date:            Inclusive end of the data window.
        provider_preference: Optional preferred provider name.
    """

    symbol: str
    exchange: str
    data_type: DataType
    start_date: date
    end_date: date
    provider_preference: str | None = None


@dataclass(frozen=True)
class ValidationResult:
    """Result of validating a DataRequest or fetched data.

    Attributes:
        valid:          True when all checks pass.
        errors:         Blocking validation errors.
        warnings:       Non-blocking observations.
        missing_fields: Fields that are empty or absent.
    """

    valid: bool
    errors: tuple[str, ...] = field(default_factory=tuple)
    warnings: tuple[str, ...] = field(default_factory=tuple)
    missing_fields: tuple[str, ...] = field(default_factory=tuple)


@dataclass(frozen=True)
class DataResponse:
    """Immutable response from a data provider.

    Attributes:
        request:           Original request.
        provider:          Provider that fulfilled the request.
        timestamp:         When the response was generated.
        status:            Outcome status.
        payload:           The data payload (list of dicts).
        metadata:          Provider-specific metadata.
        validation_result: Validation outcome for the response data.
    """

    request: DataRequest
    provider: str
    timestamp: datetime
    status: DataStatus
    payload: tuple[dict[str, object], ...] = field(default_factory=tuple)
    metadata: dict[str, str] = field(default_factory=dict)
    validation_result: ValidationResult = field(
        default_factory=lambda: ValidationResult(valid=True)
    )
