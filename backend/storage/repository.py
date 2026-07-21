"""
Repository abstraction.

Abstract base class for dataset persistence.
"""

from __future__ import annotations

from abc import ABC, abstractmethod

from backend.storage.models import (
    DatasetType,
    RetrievalRequest,
    RetrievalResult,
    StorageRequest,
    StorageResult,
)


class Repository(ABC):
    """Abstract interface for dataset persistence.

    Concrete implementations handle the actual storage mechanism
    (PostgreSQL, filesystem, etc.).
    """

    @abstractmethod
    def store(self, request: StorageRequest) -> StorageResult:
        """Persist a dataset.

        Args:
            request: Storage request.

        Returns:
            StorageResult with storage_id and status.
        """

    @abstractmethod
    def retrieve(self, request: RetrievalRequest) -> RetrievalResult:
        """Retrieve a dataset.

        Args:
            request: Retrieval request.

        Returns:
            RetrievalResult with records and metadata.
        """

    @abstractmethod
    def delete(self, dataset_type: DatasetType, symbol: str) -> bool:
        """Delete a dataset.

        Args:
            dataset_type: Type of dataset.
            symbol:       Ticker symbol.

        Returns:
            True if deleted successfully.
        """

    @abstractmethod
    def exists(self, dataset_type: DatasetType, symbol: str) -> bool:
        """Check if a dataset exists.

        Args:
            dataset_type: Type of dataset.
            symbol:       Ticker symbol.

        Returns:
            True if dataset exists.
        """

    @abstractmethod
    def supported_dataset_types(self) -> tuple[DatasetType, ...]:
        """Return dataset types this repository supports.

        Returns:
            Tuple of supported dataset types.
        """
