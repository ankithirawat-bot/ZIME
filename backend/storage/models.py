"""
Storage Engine models.

Frozen dataclasses and enumerations for storage requests,
responses, versioning, and dataset management.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from datetime import date, datetime
from enum import StrEnum


class DatasetType(StrEnum):
    """Types of datasets that can be stored and retrieved."""

    PRICE_DAILY = "price_daily"
    PRICE_INTRADAY = "price_intraday"
    FINANCIALS = "financials"
    CORPORATE_ACTIONS = "corporate_actions"
    SHAREHOLDING = "shareholding"
    NEWS = "news"
    EARNINGS = "earnings"


class StorageStatus(StrEnum):
    """Outcome status of a storage operation."""

    SUCCESS = "success"
    PARTIAL = "partial"
    FAILED = "failed"
    DUPLICATE = "duplicate"


@dataclass(frozen=True)
class StorageRequest:
    """Immutable request to store a dataset.

    Attributes:
        dataset:      Records to store (tuple of dicts).
        dataset_type: Type of dataset.
        provider:     Provider name that produced the data.
        version:      Dataset version identifier.
        metadata:     Additional storage metadata.
    """

    dataset: tuple[dict[str, object], ...]
    dataset_type: DatasetType
    provider: str
    version: str
    metadata: dict[str, str] = field(default_factory=dict)


@dataclass(frozen=True)
class StorageResult:
    """Immutable result of a storage operation.

    Attributes:
        success:     True when storage succeeded.
        storage_id:  Unique identifier for the stored dataset.
        version:     Version that was stored.
        timestamp:   When the storage occurred.
        warnings:    Non-blocking warnings.
    """

    success: bool
    storage_id: str
    version: str
    timestamp: datetime
    warnings: tuple[str, ...] = field(default_factory=tuple)


@dataclass(frozen=True)
class RetrievalRequest:
    """Immutable request to retrieve a dataset.

    Attributes:
        dataset_type: Type of dataset to retrieve.
        symbol:       Ticker symbol.
        start_date:   Inclusive start of the data window.
        end_date:     Inclusive end of the data window.
        version:      Optional specific version to retrieve.
    """

    dataset_type: DatasetType
    symbol: str
    start_date: date
    end_date: date
    version: str | None = None


@dataclass(frozen=True)
class RetrievalResult:
    """Immutable result of a retrieval operation.

    Attributes:
        records:  Retrieved data records.
        provider: Provider that originally produced the data.
        version:  Version of the retrieved data.
        metadata: Additional retrieval metadata.
    """

    records: tuple[dict[str, object], ...]
    provider: str
    version: str
    metadata: dict[str, str] = field(default_factory=dict)


@dataclass(frozen=True)
class DatasetVersion:
    """Immutable version metadata for a stored dataset.

    Attributes:
        provider:     Provider name.
        version:      Version identifier.
        created_at:   When this version was created.
        checksum:     Data integrity checksum.
        record_count: Number of records in this version.
    """

    provider: str
    version: str
    created_at: datetime
    checksum: str
    record_count: int
