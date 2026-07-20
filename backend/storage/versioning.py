"""
Versioning utilities.

Pure functions for generating and validating dataset versions.
"""

from __future__ import annotations

import hashlib
import json
from datetime import UTC, datetime

from backend.storage.models import DatasetVersion


def generate_version(
    provider: str,
    dataset_type: str,
    symbol: str,
    timestamp: datetime | None = None,
) -> str:
    """Generate a deterministic version identifier.

    Version format: {provider}_{dataset_type}_{symbol}_{timestamp}.

    Args:
        provider:     Provider name.
        dataset_type: Dataset type string.
        symbol:       Ticker symbol.
        timestamp:    Optional timestamp (defaults to now UTC).

    Returns:
        Version string.
    """
    ts = timestamp or datetime.now(UTC)
    ts_str = ts.strftime("%Y%m%d%H%M%S")
    return f"{provider}_{dataset_type}_{symbol}_{ts_str}"


def compute_checksum(records: tuple[dict[str, object], ...]) -> str:
    """Compute a deterministic checksum for a dataset.

    Uses SHA-256 of the JSON-serialized records.

    Args:
        records: Data records.

    Returns:
        Hex digest string.
    """
    serialized = json.dumps(records, sort_keys=True, default=str)
    return hashlib.sha256(serialized.encode()).hexdigest()


def create_version(
    provider: str,
    version: str,
    record_count: int,
    records: tuple[dict[str, object], ...] | None = None,
    created_at: datetime | None = None,
) -> DatasetVersion:
    """Create a DatasetVersion with optional automatic checksum.

    Args:
        provider:     Provider name.
        version:      Version identifier.
        record_count: Number of records.
        records:      Optional records for checksum computation.
        created_at:   Optional creation timestamp.

    Returns:
        DatasetVersion instance.
    """
    ts = created_at or datetime.now(UTC)
    checksum = compute_checksum(records) if records is not None else ""
    return DatasetVersion(
        provider=provider,
        version=version,
        created_at=ts,
        checksum=checksum,
        record_count=record_count,
    )


def is_newer(existing: DatasetVersion, candidate: DatasetVersion) -> bool:
    """Check if candidate version is newer than existing.

    Compares by created_at timestamp, then by version string.

    Args:
        existing:  Current version.
        candidate: New version to compare.

    Returns:
        True if candidate is newer.
    """
    if candidate.created_at > existing.created_at:
        return True
    if candidate.created_at == existing.created_at:
        return candidate.version > existing.version
    return False
