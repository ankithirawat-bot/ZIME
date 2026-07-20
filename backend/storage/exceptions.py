"""
Storage Engine exceptions.

Domain-specific exceptions for storage operations.
"""


class StorageError(Exception):
    """Base exception for all storage errors."""


class RepositoryNotFoundError(StorageError):
    """Raised when no repository is registered for a dataset type."""

    def __init__(self, dataset_type: str) -> None:
        self.dataset_type = dataset_type
        super().__init__(f"No repository registered for dataset type: {dataset_type}")


class DuplicateDatasetError(StorageError):
    """Raised when attempting to store a dataset that already exists."""

    def __init__(self, dataset_id: str) -> None:
        self.dataset_id = dataset_id
        super().__init__(f"Dataset already exists: {dataset_id}")


class DatasetNotFoundError(StorageError):
    """Raised when a requested dataset does not exist."""

    def __init__(self, dataset_id: str) -> None:
        self.dataset_id = dataset_id
        super().__init__(f"Dataset not found: {dataset_id}")


class VersionConflictError(StorageError):
    """Raised when a version conflict is detected."""

    def __init__(self, expected: str, actual: str) -> None:
        self.expected = expected
        self.actual = actual
        super().__init__(
            f"Version conflict: expected {expected}, got {actual}"
        )
