"""
Data quality immutable models.

All runtime state is captured by frozen dataclasses. A :class:`PriceBar` is
the minimal generic OHLCV record (no provider-specific fields), and every
other model is derived from one or more requests/results.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from datetime import date, datetime
from typing import Any
from uuid import uuid4

from backend.data_quality.exceptions import ValidationError


@dataclass(frozen=True)
class PriceBar:
    """Immutable generic OHLCV bar (provider agnostic).

    Attributes:
        trade_date:      Session date of the bar.
        open:            Open price.
        high:            High price.
        low:             Low price.
        close:           Close price.
        volume:          Traded volume (>= 0).
        adjusted_close:  Split/dividend adjusted close, if available.
    """

    trade_date: date
    open: float
    high: float
    low: float
    close: float
    volume: float
    adjusted_close: float | None = None


@dataclass(frozen=True)
class Issue:
    """Immutable structured validation issue.

    Attributes:
        code:     Machine readable category (e.g. "missing_days").
        message:  Human readable description.
        index:    Offending bar index, when applicable.
        severity: "low" | "medium" | "high".
        value:    Optional payload (e.g. the missing date).
    """

    code: str
    message: str
    index: int | None = None
    severity: str = "medium"
    value: Any = None


@dataclass(frozen=True)
class ValidationRequest:
    """Immutable validation request.

    Attributes:
        symbol:    Instrument symbol.
        exchange:  Exchange identifier.
        provider:  Data provider name.
        bars:      Tuple of price bars to validate.
        request_id: Unique id (auto-generated).
        as_of:     Baseline date for future-date checks (None = today).
    """

    symbol: str
    exchange: str
    provider: str
    bars: tuple[PriceBar, ...]
    request_id: str = field(default_factory=lambda: uuid4().hex)
    as_of: date | None = None

    def __post_init__(self) -> None:
        if not self.symbol or not self.exchange or not self.provider:
            raise ValidationError("symbol, exchange and provider are required")
        if self.bars is None:
            raise ValidationError("bars must be provided")


@dataclass(frozen=True)
class ValidationResult:
    """Immutable outcome of validating one provider's bars."""

    symbol: str
    exchange: str
    provider: str
    missing_days: tuple[date, ...]
    duplicate_rows: tuple[int, ...]
    invalid_ohlc: tuple[int, ...]
    invalid_volume: tuple[int, ...]
    timestamp_issues: tuple[int, ...]
    future_dates: tuple[int, ...]
    issues: tuple[Issue, ...]
    is_valid: bool
    checked_at: datetime = field(default_factory=lambda: datetime.now().astimezone())


@dataclass(frozen=True)
class MissingRecord:
    """Immutable record of a date missing for a provider."""

    provider: str
    date: date


@dataclass(frozen=True)
class ComparisonResult:
    """Immutable difference of one metric between two providers on a date."""

    date: date
    metric: str
    provider_a: str
    provider_b: str
    value_a: float
    value_b: float
    diff: float
    pct_diff: float


@dataclass(frozen=True)
class CorporateActionDivergence:
    """Immutable flag of suspected corporate-action mismatch between providers."""

    date: date
    provider_a: str
    provider_b: str
    ratio: float
    description: str


@dataclass(frozen=True)
class ProviderComparison:
    """Immutable multi-provider comparison outcome."""

    symbol: str
    exchange: str
    providers: tuple[str, ...]
    ohlc_diffs: tuple[ComparisonResult, ...]
    volume_diffs: tuple[ComparisonResult, ...]
    missing_records: tuple[MissingRecord, ...]
    date_mismatches: tuple[date, ...]
    corporate_action_divergence: tuple[CorporateActionDivergence, ...]
    agreement_score: float


@dataclass(frozen=True)
class Anomaly:
    """Immutable detected anomaly."""

    provider: str
    symbol: str
    anomaly_type: str
    severity: str
    description: str
    date: date | None = None
    index: int | None = None
    value: float | None = None


@dataclass(frozen=True)
class ConfidenceScore:
    """Immutable confidence score (0-100) with component breakdown."""

    symbol: str
    exchange: str
    provider: str
    score: float
    components: dict[str, float]
    reasons: tuple[str, ...]


@dataclass(frozen=True)
class ValidationReport:
    """Immutable end-to-end data quality report."""

    request_id: str
    symbol: str
    exchange: str
    provider: str
    generated_at: datetime
    summary: dict[str, Any]
    issues: tuple[str, ...]
    anomalies: tuple[Anomaly, ...]
    confidence: ConfidenceScore
    recommendations: tuple[str, ...]
