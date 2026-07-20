"""
Storage Engine.

Public APIs: ``store`` and ``retrieve``.
"""

from __future__ import annotations

from backend.storage.models import (
    DatasetType,
    RetrievalRequest,
    RetrievalResult,
    StorageRequest,
    StorageResult,
)
from backend.storage.repository_registry import RepositoryRegistry


class StorageEngine:
    """Orchestrates storage and retrieval through repository abstraction.

    Uses RepositoryRegistry for dependency inversion.  Never calls
    repositories directly — always resolves through the registry.
    """

    def __init__(self, registry: RepositoryRegistry) -> None:
        self._registry = registry

    def store(self, request: StorageRequest) -> StorageResult:
        """Store a dataset.

        Resolution order:
            1. Resolve repository for dataset_type.
            2. Delegate to repository.store().

        Args:
            request: Storage request.

        Returns:
            StorageResult with storage_id and status.

        Raises:
            RepositoryNotFoundError: If no repository is registered.
        """
        repo = self._registry.resolve(request.dataset_type)
        return repo.store(request)

    def retrieve(self, request: RetrievalRequest) -> RetrievalResult:
        """Retrieve a dataset.

        Resolution order:
            1. Resolve repository for dataset_type.
            2. Delegate to repository.retrieve().

        Args:
            request: Retrieval request.

        Returns:
            RetrievalResult with records and metadata.

        Raises:
            RepositoryNotFoundError: If no repository is registered.
        """
        repo = self._registry.resolve(request.dataset_type)
        return repo.retrieve(request)

    def delete(self, dataset_type: DatasetType, symbol: str) -> bool:
        """Delete a dataset.

        Args:
            dataset_type: Type of dataset.
            symbol:       Ticker symbol.

        Returns:
            True if deleted.

        Raises:
            RepositoryNotFoundError: If no repository is registered.
        """
        repo = self._registry.resolve(dataset_type)
        return repo.delete(dataset_type, symbol)

    def exists(self, dataset_type: DatasetType, symbol: str) -> bool:
        """Check if a dataset exists.

        Args:
            dataset_type: Type of dataset.
            symbol:       Ticker symbol.

        Returns:
            True if dataset exists.

        Raises:
            RepositoryNotFoundError: If no repository is registered.
        """
        repo = self._registry.resolve(dataset_type)
        return repo.exists(dataset_type, symbol)
