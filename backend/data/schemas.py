"""
Canonical data schemas.

Immutable schemas representing normalized market data formats
that all providers must map to.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from datetime import date, datetime


@dataclass(frozen=True)
class DailyOHLCV:
    """Daily price bar schema.

    Attributes:
        date:     Trading date.
        open:     Opening price.
        high:     Intraday high.
        low:      Intraday low.
        close:    Closing price.
        adj_close: Adjusted close (splits + dividends).
        volume:   Trading volume (shares).
    """

    date: date
    open: float
    high: float
    low: float
    close: float
    adj_close: float
    volume: float


@dataclass(frozen=True)
class IntradayOHLCV:
    """Intraday price bar schema.

    Attributes:
        datetime: Bar timestamp.
        open:     Opening price.
        high:     Intraday high.
        low:      Intraday low.
        close:    Closing price.
        volume:   Trading volume (shares).
    """

    datetime: datetime
    open: float
    high: float
    low: float
    close: float
    volume: float


@dataclass(frozen=True)
class FinancialStatement:
    """Financial statement record schema.

    Attributes:
        symbol:           Ticker symbol.
        report_date:      Reporting period end date.
        period:           Reporting period (e.g. "Q3 FY24", "FY24").
        revenue:          Total revenue.
        net_profit:       Net profit after tax.
        eps:              Earnings per share.
        total_assets:     Total assets.
        total_liabilities: Total liabilities.
        equity:           Shareholders' equity.
        operating_profit: Operating profit (EBIT).
        metadata:         Additional provider-specific fields.
    """

    symbol: str
    report_date: date
    period: str
    revenue: float | None = None
    net_profit: float | None = None
    eps: float | None = None
    total_assets: float | None = None
    total_liabilities: float | None = None
    equity: float | None = None
    operating_profit: float | None = None
    metadata: dict[str, object] = field(default_factory=dict)


@dataclass(frozen=True)
class CorporateAction:
    """Corporate action record schema.

    Attributes:
        symbol:       Ticker symbol.
        action_type:  Type of action (dividend, split, bonus, etc.).
        announcement_date: When the action was announced.
        ex_date:      Effective date.
        record_date:  Record date for eligibility.
        value:        Action value (dividend amount, split ratio, etc.).
        metadata:     Additional provider-specific fields.
    """

    symbol: str
    action_type: str
    announcement_date: date | None = None
    ex_date: date | None = None
    record_date: date | None = None
    value: float | None = None
    metadata: dict[str, object] = field(default_factory=dict)


@dataclass(frozen=True)
class NewsRecord:
    """News article record schema.

    Attributes:
        symbol:      Associated ticker symbol.
        headline:    Article headline.
        source:      News source.
        published_at: Publication timestamp.
        url:         Article URL.
        summary:     Brief summary or snippet.
        sentiment:   Optional sentiment label.
        metadata:    Additional provider-specific fields.
    """

    symbol: str
    headline: str
    source: str
    published_at: datetime | None = None
    url: str | None = None
    summary: str | None = None
    sentiment: str | None = None
    metadata: dict[str, object] = field(default_factory=dict)


@dataclass(frozen=True)
class ShareholdingRecord:
    """Shareholding pattern record schema.

    Attributes:
        symbol:            Ticker symbol.
        report_date:       Reporting date.
        category:          Holder category (promoter, FII, DII, public, etc.).
        shares_held:       Number of shares held.
        percentage:        Percentage of total shares.
        change_shares:     Change in shares from previous period.
        change_percentage: Change in percentage from previous period.
        metadata:          Additional provider-specific fields.
    """

    symbol: str
    report_date: date
    category: str
    shares_held: float
    percentage: float
    change_shares: float | None = None
    change_percentage: float | None = None
    metadata: dict[str, object] = field(default_factory=dict)
