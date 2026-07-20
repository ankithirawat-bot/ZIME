"""
Data Source abstraction.

Abstract base class that each provider implements to normalize
its raw payload into ZIME's canonical data models.
"""

from __future__ import annotations

from abc import ABC, abstractmethod

from backend.data.models import DataType, RawDataResponse
from backend.data.schemas import (
    CorporateAction,
    DailyOHLCV,
    FinancialStatement,
    IntradayOHLCV,
    NewsRecord,
    ShareholdingRecord,
)

# Union type for all normalized records.
NormalizedRecord = (
    DailyOHLCV
    | IntradayOHLCV
    | FinancialStatement
    | CorporateAction
    | NewsRecord
    | ShareholdingRecord
)


class DataSource(ABC):
    """Abstract interface for data normalization.

    Each provider implements a DataSource that knows how to convert
    that provider's raw payload format into ZIME canonical schemas.
    """

    @abstractmethod
    def source_name(self) -> str:
        """Unique identifier for this data source."""

    @abstractmethod
    def supported_types(self) -> tuple[DataType, ...]:
        """Return data types this source can normalize."""

    @abstractmethod
    def normalize(self, response: RawDataResponse) -> tuple[NormalizedRecord, ...]:
        """Normalize a raw provider response into canonical records.

        Args:
            response: Raw data from a provider.

        Returns:
            Tuple of normalized records.
        """

    @abstractmethod
    def validate_schema(
        self,
        response: RawDataResponse,
    ) -> tuple[bool, tuple[str, ...]]:
        """Validate that raw payload conforms to expected schema.

        Args:
            response: Raw data to validate.

        Returns:
            (is_valid, errors) tuple.
        """
