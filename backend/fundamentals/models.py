"""
Fundamentals immutable models.

Frozen dataclasses describing company fundamentals for point-in-time
research. Every model carries common point-in-time metadata so that
historical queries never expose data unavailable on a given date.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from datetime import date, datetime
from typing import Any

from backend.fundamentals.types import PeriodType, StatementType


@dataclass(frozen=True)
class _FundamentalCommon:
    """Shared fields for every fundamental statement.

    Attributes:
        symbol:         Ticker symbol (e.g. "RELIANCE").
        exchange:       Exchange identifier (e.g. "NSE").
        provider:       Originating provider name.
        period_type:    Reporting cadence (annual/quarterly/...).
        fiscal_year:    Fiscal year of the statement.
        report_date:    Date the period ended.
        filing_date:    Date the statement was filed/published.
        fiscal_quarter: Quarter within the fiscal year (1-4) or None.
        currency:       Reporting currency (e.g. "INR").
        effective_from: Point-in-time lower bound (inclusive).
        effective_to:   Point-in-time upper bound (None = open-ended).
        metadata:       Provider-specific provenance attributes.
        data:           Statement-specific metric values.
    """

    symbol: str
    exchange: str
    provider: str
    period_type: PeriodType
    fiscal_year: int
    report_date: date
    filing_date: date
    fiscal_quarter: int | None = None
    currency: str = "INR"
    effective_from: date | None = None
    effective_to: date | None = None
    metadata: dict[str, Any] = field(default_factory=dict)
    data: dict[str, Any] = field(default_factory=dict)


@dataclass(frozen=True)
class CompanyProfile(_FundamentalCommon):
    """Immutable company profile snapshot."""

    name: str = ""
    sector: str = ""
    industry: str = ""


@dataclass(frozen=True)
class IncomeStatement(_FundamentalCommon):
    """Immutable income statement."""


@dataclass(frozen=True)
class BalanceSheet(_FundamentalCommon):
    """Immutable balance sheet."""


@dataclass(frozen=True)
class CashFlowStatement(_FundamentalCommon):
    """Immutable cash flow statement."""


@dataclass(frozen=True)
class ShareholdingPattern(_FundamentalCommon):
    """Immutable shareholding pattern snapshot."""


@dataclass(frozen=True)
class KeyRatios(_FundamentalCommon):
    """Immutable key financial ratios snapshot."""


@dataclass(frozen=True)
class FundamentalBatch:
    """Immutable batch of fundamental statements for storage."""

    statements: tuple[object, ...]
    source: str = ""
    fetched_at: datetime = field(default_factory=lambda: datetime.now().astimezone())


@dataclass(frozen=True)
class FundamentalSnapshot:
    """Point-in-time collection of the latest statement per type.

    Attributes:
        symbol:       Ticker symbol.
        exchange:     Exchange identifier.
        as_of:        Reference date of the snapshot.
        statements:   Mapping of statement type to latest model.
    """

    symbol: str
    exchange: str
    as_of: date
    statements: dict[StatementType, object] = field(default_factory=dict)
