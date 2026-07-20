"""
Storage Engine.

Provider-agnostic persistence, versioning, and caching architecture.
"""

from backend.storage.cache import CacheProvider
from backend.storage.exceptions import (
    DatasetNotFoundError,
    DuplicateDatasetError,
    RepositoryNotFoundError,
    StorageError,
    VersionConflictError,
)
from backend.storage.models import (
    DatasetType,
    DatasetVersion,
    RetrievalRequest,
    RetrievalResult,
    StorageRequest,
    StorageResult,
    StorageStatus,
)
from backend.storage.repository import Repository
from backend.storage.repository_registry import RepositoryRegistry
from backend.storage.storage_engine import StorageEngine
from backend.storage.versioning import (
    compute_checksum,
    create_version,
    generate_version,
    is_newer,
)

__all__ = [
    "CacheProvider",
    "DatasetNotFoundError",
    "DatasetType",
    "DatasetVersion",
    "DuplicateDatasetError",
    "Repository",
    "RepositoryNotFoundError",
    "RepositoryRegistry",
    "RetrievalRequest",
    "RetrievalResult",
    "StorageEngine",
    "StorageError",
    "StorageRequest",
    "StorageResult",
    "StorageStatus",
    "VersionConflictError",
    "compute_checksum",
    "create_version",
    "generate_version",
    "is_newer",
]
