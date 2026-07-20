"""
Adapter interfaces.

Abstract base classes for converting provider-specific field names
and formats into ZIME's canonical schema fields.
"""

from __future__ import annotations

from abc import ABC, abstractmethod

from backend.data.schemas import (
    CorporateAction,
    DailyOHLCV,
    FinancialStatement,
    IntradayOHLCV,
    NewsRecord,
    ShareholdingRecord,
)


class PriceAdapter(ABC):
    """Adapter for converting provider price data to canonical OHLCV."""

    @abstractmethod
    def to_daily(self, raw: dict[str, object]) -> DailyOHLCV:
        """Convert a raw price record to DailyOHLCV.

        Args:
            raw: Provider-specific price record.

        Returns:
            Normalized DailyOHLCV.
        """

    @abstractmethod
    def to_intraday(self, raw: dict[str, object]) -> IntradayOHLCV:
        """Convert a raw intraday record to IntradayOHLCV.

        Args:
            raw: Provider-specific intraday record.

        Returns:
            Normalized IntradayOHLCV.
        """


class FinancialAdapter(ABC):
    """Adapter for converting provider financial data to canonical schema."""

    @abstractmethod
    def to_statement(self, raw: dict[str, object], symbol: str) -> FinancialStatement:
        """Convert a raw financial record to FinancialStatement.

        Args:
            raw:    Provider-specific financial record.
            symbol: Ticker symbol.

        Returns:
            Normalized FinancialStatement.
        """


class NewsAdapter(ABC):
    """Adapter for converting provider news data to canonical schema."""

    @abstractmethod
    def to_record(self, raw: dict[str, object], symbol: str) -> NewsRecord:
        """Convert a raw news record to NewsRecord.

        Args:
            raw:    Provider-specific news record.
            symbol: Ticker symbol.

        Returns:
            Normalized NewsRecord.
        """


class ShareholdingAdapter(ABC):
    """Adapter for converting provider shareholding data to canonical schema."""

    @abstractmethod
    def to_record(self, raw: dict[str, object], symbol: str) -> ShareholdingRecord:
        """Convert a raw shareholding record to ShareholdingRecord.

        Args:
            raw:    Provider-specific shareholding record.
            symbol: Ticker symbol.

        Returns:
            Normalized ShareholdingRecord.
        """


class CorporateActionAdapter(ABC):
    """Adapter for converting provider corporate action data to canonical schema."""

    @abstractmethod
    def to_record(self, raw: dict[str, object], symbol: str) -> CorporateAction:
        """Convert a raw corporate action record to CorporateAction.

        Args:
            raw:    Provider-specific corporate action record.
            symbol: Ticker symbol.

        Returns:
            Normalized CorporateAction.
        """
