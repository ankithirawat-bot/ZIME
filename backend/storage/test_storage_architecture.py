"""
Storage Engine architecture tests.

Covers enums, models, repository ABC, registry, cache ABC,
versioning utilities, StorageEngine, determinism, and regression.
"""

from __future__ import annotations

from dataclasses import FrozenInstanceError
from datetime import UTC, date, datetime
from typing import Any

import pytest

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

# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


class FakeRepository(Repository):
    """Minimal concrete repository for testing."""

    def __init__(
        self,
        supported: tuple[DatasetType, ...] = (DatasetType.PRICE_DAILY,),
        should_exist: bool = False,
    ) -> None:
        self._supported = supported
        self._should_exist = should_exist
        self._store_calls: list[StorageRequest] = []
        self._retrieve_calls: list[RetrievalRequest] = []

    def store(self, request: StorageRequest) -> StorageResult:
        self._store_calls.append(request)
        return StorageResult(
            success=True,
            storage_id=f"fake_{request.dataset_type.value}",
            version=request.version,
            timestamp=datetime.now(UTC),
        )

    def retrieve(self, request: RetrievalRequest) -> RetrievalResult:
        self._retrieve_calls.append(request)
        return RetrievalResult(
            records=({"close": 100.0, "volume": 1000},),
            provider="fake_provider",
            version="v1",
        )

    def delete(self, dataset_type: DatasetType, symbol: str) -> bool:
        return True

    def exists(self, dataset_type: DatasetType, symbol: str) -> bool:
        return self._should_exist

    def supported_types(self) -> tuple[DatasetType, ...]:
        return self._supported


class FakeCache(CacheProvider):
    """Minimal concrete cache for testing."""

    def __init__(self) -> None:
        self._data: dict[str, object] = {}

    def get(self, key: str) -> object | None:
        return self._data.get(key)

    def put(self, key: str, value: object, ttl_seconds: int | None = None) -> None:
        self._data[key] = value

    def invalidate(self, key: str) -> bool:
        if key in self._data:
            del self._data[key]
            return True
        return False

    def clear(self) -> int:
        count = len(self._data)
        self._data.clear()
        return count


def _make_storage_request(**overrides: Any) -> StorageRequest:
    defaults: dict[str, object] = {
        "dataset": ({"close": 100.0, "volume": 1000},),
        "dataset_type": DatasetType.PRICE_DAILY,
        "provider": "yfinance",
        "version": "v1",
    }
    defaults.update(overrides)
    return StorageRequest(**defaults)  # type: ignore[arg-type]


def _make_retrieval_request(**overrides: Any) -> RetrievalRequest:
    defaults: dict[str, object] = {
        "dataset_type": DatasetType.PRICE_DAILY,
        "symbol": "RELIANCE",
        "start_date": date(2024, 1, 1),
        "end_date": date(2024, 12, 31),
    }
    defaults.update(overrides)
    return RetrievalRequest(**defaults)  # type: ignore[arg-type]


# ---------------------------------------------------------------------------
# DatasetType enum
# ---------------------------------------------------------------------------


class TestDatasetType:
    def test_all_values_unique(self):
        values = [dt.value for dt in DatasetType]
        assert len(values) == len(set(values))

    def test_expected_types(self):
        assert DatasetType.PRICE_DAILY == "price_daily"
        assert DatasetType.PRICE_INTRADAY == "price_intraday"
        assert DatasetType.FINANCIALS == "financials"
        assert DatasetType.CORPORATE_ACTIONS == "corporate_actions"
        assert DatasetType.SHAREHOLDING == "shareholding"
        assert DatasetType.NEWS == "news"
        assert DatasetType.EARNINGS == "earnings"

    def test_count(self):
        assert len(DatasetType) == 7

    def test_is_str_enum(self):
        assert isinstance(DatasetType.PRICE_DAILY, str)
        assert DatasetType.PRICE_DAILY == "price_daily"


# ---------------------------------------------------------------------------
# StorageStatus enum
# ---------------------------------------------------------------------------


class TestStorageStatus:
    def test_all_statuses(self):
        assert StorageStatus.SUCCESS == "success"
        assert StorageStatus.PARTIAL == "partial"
        assert StorageStatus.FAILED == "failed"
        assert StorageStatus.DUPLICATE == "duplicate"

    def test_count(self):
        assert len(StorageStatus) == 4


# ---------------------------------------------------------------------------
# StorageRequest model
# ---------------------------------------------------------------------------


class TestStorageRequest:
    def test_creation(self):
        sr = _make_storage_request()
        assert sr.dataset_type == DatasetType.PRICE_DAILY
        assert sr.provider == "yfinance"
        assert sr.version == "v1"
        assert len(sr.dataset) == 1
        assert sr.metadata == {}

    def test_with_metadata(self):
        sr = _make_storage_request(metadata={"key": "val"})
        assert sr.metadata == {"key": "val"}

    def test_frozen(self):
        sr = _make_storage_request()
        with pytest.raises(FrozenInstanceError):
            sr.version = "v2"  # type: ignore[misc]

    def test_equality(self):
        sr1 = _make_storage_request()
        sr2 = _make_storage_request()
        assert sr1 == sr2


# ---------------------------------------------------------------------------
# StorageResult model
# ---------------------------------------------------------------------------


class TestStorageResult:
    def test_creation(self):
        now = datetime.now(UTC)
        result = StorageResult(
            success=True,
            storage_id="abc123",
            version="v1",
            timestamp=now,
            warnings=("warn",),
        )
        assert result.success is True
        assert result.storage_id == "abc123"
        assert result.version == "v1"
        assert result.warnings == ("warn",)

    def test_defaults(self):
        now = datetime.now(UTC)
        result = StorageResult(
            success=False,
            storage_id="",
            version="",
            timestamp=now,
        )
        assert result.warnings == ()

    def test_frozen(self):
        now = datetime.now(UTC)
        result = StorageResult(success=True, storage_id="x", version="v1", timestamp=now)
        with pytest.raises(FrozenInstanceError):
            result.success = False  # type: ignore[misc]


# ---------------------------------------------------------------------------
# RetrievalRequest model
# ---------------------------------------------------------------------------


class TestRetrievalRequest:
    def test_creation(self):
        rr = _make_retrieval_request()
        assert rr.dataset_type == DatasetType.PRICE_DAILY
        assert rr.symbol == "RELIANCE"
        assert rr.start_date == date(2024, 1, 1)
        assert rr.end_date == date(2024, 12, 31)
        assert rr.version is None

    def test_with_version(self):
        rr = _make_retrieval_request(version="v2")
        assert rr.version == "v2"

    def test_frozen(self):
        rr = _make_retrieval_request()
        with pytest.raises(FrozenInstanceError):
            rr.symbol = "TCS"  # type: ignore[misc]


# ---------------------------------------------------------------------------
# RetrievalResult model
# ---------------------------------------------------------------------------


class TestRetrievalResult:
    def test_creation(self):
        rr = RetrievalResult(
            records=({"close": 100.0},),
            provider="yfinance",
            version="v1",
            metadata={"key": "val"},
        )
        assert len(rr.records) == 1
        assert rr.provider == "yfinance"
        assert rr.version == "v1"

    def test_defaults(self):
        rr = RetrievalResult(
            records=(),
            provider="yfinance",
            version="v1",
        )
        assert rr.metadata == {}

    def test_frozen(self):
        rr = RetrievalResult(records=(), provider="yfinance", version="v1")
        with pytest.raises(FrozenInstanceError):
            rr.provider = "other"  # type: ignore[misc]


# ---------------------------------------------------------------------------
# DatasetVersion model
# ---------------------------------------------------------------------------


class TestDatasetVersion:
    def test_creation(self):
        now = datetime.now(UTC)
        dv = DatasetVersion(
            provider="yfinance",
            version="v1",
            created_at=now,
            checksum="abc123",
            record_count=100,
        )
        assert dv.provider == "yfinance"
        assert dv.version == "v1"
        assert dv.checksum == "abc123"
        assert dv.record_count == 100

    def test_frozen(self):
        now = datetime.now(UTC)
        dv = DatasetVersion(
            provider="yfinance", version="v1", created_at=now, checksum="", record_count=0
        )
        with pytest.raises(FrozenInstanceError):
            dv.version = "v2"  # type: ignore[misc]

    def test_equality(self):
        now = datetime.now(UTC)
        dv1 = DatasetVersion(provider="x", version="v1", created_at=now, checksum="", record_count=0)
        dv2 = DatasetVersion(provider="x", version="v1", created_at=now, checksum="", record_count=0)
        assert dv1 == dv2


# ---------------------------------------------------------------------------
# Exceptions
# ---------------------------------------------------------------------------


class TestExceptions:
    def test_storage_error(self):
        exc = StorageError("test")
        assert str(exc) == "test"
        assert isinstance(exc, Exception)

    def test_repository_not_found(self):
        exc = RepositoryNotFoundError("price_daily")
        assert exc.dataset_type == "price_daily"
        assert "price_daily" in str(exc)
        assert isinstance(exc, StorageError)

    def test_duplicate_dataset(self):
        exc = DuplicateDatasetError("ds_001")
        assert exc.dataset_id == "ds_001"
        assert isinstance(exc, StorageError)

    def test_dataset_not_found(self):
        exc = DatasetNotFoundError("ds_002")
        assert exc.dataset_id == "ds_002"
        assert isinstance(exc, StorageError)

    def test_version_conflict(self):
        exc = VersionConflictError("v1", "v2")
        assert exc.expected == "v1"
        assert exc.actual == "v2"
        assert isinstance(exc, StorageError)


# ---------------------------------------------------------------------------
# Repository ABC
# ---------------------------------------------------------------------------


class TestRepositoryABC:
    def test_cannot_instantiate_abc(self):
        with pytest.raises(TypeError):
            Repository()  # type: ignore[abstract]

    def test_fake_repository_implements_interface(self):
        repo = FakeRepository()
        assert isinstance(repo, Repository)
        assert DatasetType.PRICE_DAILY in repo.supported_types()

    def test_store_returns_result(self):
        repo = FakeRepository()
        req = _make_storage_request()
        result = repo.store(req)
        assert isinstance(result, StorageResult)
        assert result.success is True

    def test_retrieve_returns_result(self):
        repo = FakeRepository()
        req = _make_retrieval_request()
        result = repo.retrieve(req)
        assert isinstance(result, RetrievalResult)
        assert len(result.records) == 1

    def test_delete_returns_bool(self):
        repo = FakeRepository()
        assert repo.delete(DatasetType.PRICE_DAILY, "RELIANCE") is True

    def test_exists_returns_bool(self):
        repo = FakeRepository(should_exist=True)
        assert repo.exists(DatasetType.PRICE_DAILY, "RELIANCE") is True

    def test_exists_false(self):
        repo = FakeRepository(should_exist=False)
        assert repo.exists(DatasetType.PRICE_DAILY, "RELIANCE") is False


# ---------------------------------------------------------------------------
# RepositoryRegistry
# ---------------------------------------------------------------------------


class TestRepositoryRegistry:
    def test_register_and_resolve(self):
        reg = RepositoryRegistry()
        repo = FakeRepository()
        reg.register(repo, (DatasetType.PRICE_DAILY,))
        resolved = reg.resolve(DatasetType.PRICE_DAILY)
        assert resolved is repo

    def test_resolve_by_name(self):
        reg = RepositoryRegistry()
        repo = FakeRepository()
        reg.register(repo, (DatasetType.PRICE_DAILY,))
        resolved = reg.resolve_by_name("FakeRepository")
        assert resolved is repo

    def test_resolve_unregistered_type(self):
        reg = RepositoryRegistry()
        with pytest.raises(RepositoryNotFoundError):
            reg.resolve(DatasetType.FINANCIALS)

    def test_resolve_unregistered_name(self):
        reg = RepositoryRegistry()
        with pytest.raises(RepositoryNotFoundError):
            reg.resolve_by_name("NonexistentRepo")

    def test_supported_dataset_types(self):
        reg = RepositoryRegistry()
        repo = FakeRepository()
        reg.register(repo, (DatasetType.PRICE_DAILY, DatasetType.FINANCIALS))
        types = reg.supported_dataset_types("FakeRepository")
        assert DatasetType.PRICE_DAILY in types
        assert DatasetType.FINANCIALS in types

    def test_supported_dataset_types_unknown(self):
        reg = RepositoryRegistry()
        with pytest.raises(RepositoryNotFoundError):
            reg.supported_dataset_types("Unknown")

    def test_available_repositories(self):
        reg = RepositoryRegistry()
        repo1 = FakeRepository()
        repo2 = FakeRepository()
        reg.register(repo1, (DatasetType.PRICE_DAILY,))
        reg.register(repo2, (DatasetType.FINANCIALS,))
        names = reg.available_repositories()
        assert "FakeRepository" in names

    def test_has_repository(self):
        reg = RepositoryRegistry()
        repo = FakeRepository()
        reg.register(repo, (DatasetType.PRICE_DAILY,))
        assert reg.has_repository("FakeRepository") is True
        assert reg.has_repository("Nope") is False

    def test_has_type(self):
        reg = RepositoryRegistry()
        repo = FakeRepository()
        reg.register(repo, (DatasetType.PRICE_DAILY,))
        assert reg.has_type(DatasetType.PRICE_DAILY) is True
        assert reg.has_type(DatasetType.FINANCIALS) is False


# ---------------------------------------------------------------------------
# CacheProvider ABC
# ---------------------------------------------------------------------------


class TestCacheProviderABC:
    def test_cannot_instantiate_abc(self):
        with pytest.raises(TypeError):
            CacheProvider()  # type: ignore[abstract]

    def test_fake_cache_implements_interface(self):
        cache = FakeCache()
        assert isinstance(cache, CacheProvider)

    def test_put_and_get(self):
        cache = FakeCache()
        cache.put("key1", "value1")
        assert cache.get("key1") == "value1"

    def test_get_missing(self):
        cache = FakeCache()
        assert cache.get("missing") is None

    def test_invalidate(self):
        cache = FakeCache()
        cache.put("key1", "value1")
        assert cache.invalidate("key1") is True
        assert cache.get("key1") is None

    def test_invalidate_missing(self):
        cache = FakeCache()
        assert cache.invalidate("missing") is False

    def test_clear(self):
        cache = FakeCache()
        cache.put("a", 1)
        cache.put("b", 2)
        count = cache.clear()
        assert count == 2
        assert cache.get("a") is None


# ---------------------------------------------------------------------------
# Versioning utilities
# ---------------------------------------------------------------------------


class TestVersioning:
    def test_generate_version(self):
        v = generate_version("yfinance", "price_daily", "RELIANCE")
        assert v.startswith("yfinance_price_daily_RELIANCE_")
        assert len(v) > 30

    def test_generate_version_deterministic(self):
        ts = datetime(2024, 6, 15, 12, 0, 0, tzinfo=UTC)
        v1 = generate_version("yfinance", "price_daily", "RELIANCE", ts)
        v2 = generate_version("yfinance", "price_daily", "RELIANCE", ts)
        assert v1 == v2

    def test_generate_version_different_providers(self):
        v1 = generate_version("yfinance", "price_daily", "RELIANCE")
        v2 = generate_version("nse", "price_daily", "RELIANCE")
        assert v1 != v2

    def test_compute_checksum(self):
        records = ({"close": 100.0, "volume": 1000},)
        cs1 = compute_checksum(records)
        cs2 = compute_checksum(records)
        assert cs1 == cs2
        assert len(cs1) == 64

    def test_compute_checksum_different_data(self):
        r1 = ({"close": 100.0},)
        r2 = ({"close": 200.0},)
        assert compute_checksum(r1) != compute_checksum(r2)

    def test_create_version(self):
        ts = datetime(2024, 6, 15, tzinfo=UTC)
        records = ({"close": 100.0},)
        dv = create_version(
            provider="yfinance",
            version="v1",
            record_count=1,
            records=records,
            created_at=ts,
        )
        assert dv.provider == "yfinance"
        assert dv.version == "v1"
        assert dv.record_count == 1
        assert dv.created_at == ts
        assert len(dv.checksum) == 64

    def test_create_version_no_records(self):
        ts = datetime(2024, 6, 15, tzinfo=UTC)
        dv = create_version(
            provider="yfinance",
            version="v1",
            record_count=0,
            created_at=ts,
        )
        assert dv.checksum == ""

    def test_is_newer_by_timestamp(self):
        t1 = datetime(2024, 1, 1, tzinfo=UTC)
        t2 = datetime(2024, 6, 1, tzinfo=UTC)
        existing = DatasetVersion(provider="x", version="v1", created_at=t1, checksum="", record_count=0)
        candidate = DatasetVersion(provider="x", version="v1", created_at=t2, checksum="", record_count=0)
        assert is_newer(existing, candidate) is True
        assert is_newer(candidate, existing) is False

    def test_is_newer_same_timestamp(self):
        t = datetime(2024, 6, 1, tzinfo=UTC)
        existing = DatasetVersion(provider="x", version="v1", created_at=t, checksum="", record_count=0)
        candidate = DatasetVersion(provider="x", version="v2", created_at=t, checksum="", record_count=0)
        assert is_newer(existing, candidate) is True


# ---------------------------------------------------------------------------
# StorageEngine
# ---------------------------------------------------------------------------


class TestStorageEngine:
    def test_store(self):
        reg = RepositoryRegistry()
        repo = FakeRepository()
        reg.register(repo, (DatasetType.PRICE_DAILY,))
        engine = StorageEngine(reg)
        req = _make_storage_request()
        result = engine.store(req)
        assert result.success is True
        assert result.storage_id == "fake_price_daily"
        assert len(repo._store_calls) == 1

    def test_retrieve(self):
        reg = RepositoryRegistry()
        repo = FakeRepository()
        reg.register(repo, (DatasetType.PRICE_DAILY,))
        engine = StorageEngine(reg)
        req = _make_retrieval_request()
        result = engine.retrieve(req)
        assert len(result.records) == 1
        assert result.provider == "fake_provider"
        assert len(repo._retrieve_calls) == 1

    def test_delete(self):
        reg = RepositoryRegistry()
        repo = FakeRepository()
        reg.register(repo, (DatasetType.PRICE_DAILY,))
        engine = StorageEngine(reg)
        assert engine.delete(DatasetType.PRICE_DAILY, "RELIANCE") is True

    def test_exists(self):
        reg = RepositoryRegistry()
        repo = FakeRepository(should_exist=True)
        reg.register(repo, (DatasetType.PRICE_DAILY,))
        engine = StorageEngine(reg)
        assert engine.exists(DatasetType.PRICE_DAILY, "RELIANCE") is True

    def test_store_no_repository(self):
        reg = RepositoryRegistry()
        engine = StorageEngine(reg)
        req = _make_storage_request()
        with pytest.raises(RepositoryNotFoundError):
            engine.store(req)

    def test_retrieve_no_repository(self):
        reg = RepositoryRegistry()
        engine = StorageEngine(reg)
        req = _make_retrieval_request()
        with pytest.raises(RepositoryNotFoundError):
            engine.retrieve(req)


# ---------------------------------------------------------------------------
# Determinism
# ---------------------------------------------------------------------------


class TestDeterminism:
    def test_storage_request_equality(self):
        sr1 = _make_storage_request()
        sr2 = _make_storage_request()
        assert sr1 == sr2

    def test_retrieval_request_equality(self):
        rr1 = _make_retrieval_request()
        rr2 = _make_retrieval_request()
        assert rr1 == rr2
        assert hash(rr1) == hash(rr2)

    def test_version_generation_deterministic(self):
        ts = datetime(2024, 6, 15, 12, 0, 0, tzinfo=UTC)
        v1 = generate_version("yfinance", "price_daily", "RELIANCE", ts)
        v2 = generate_version("yfinance", "price_daily", "RELIANCE", ts)
        assert v1 == v2

    def test_checksum_deterministic(self):
        records = ({"close": 100.0},)
        cs1 = compute_checksum(records)
        cs2 = compute_checksum(records)
        assert cs1 == cs2

    def test_dataset_version_equality(self):
        now = datetime.now(UTC)
        dv1 = DatasetVersion(provider="x", version="v1", created_at=now, checksum="", record_count=0)
        dv2 = DatasetVersion(provider="x", version="v1", created_at=now, checksum="", record_count=0)
        assert dv1 == dv2

    def test_registry_deterministic(self):
        reg = RepositoryRegistry()
        repo = FakeRepository()
        reg.register(repo, (DatasetType.PRICE_DAILY,))
        r1 = reg.resolve(DatasetType.PRICE_DAILY)
        r2 = reg.resolve(DatasetType.PRICE_DAILY)
        assert r1 is r2


# ---------------------------------------------------------------------------
# Regression
# ---------------------------------------------------------------------------


class TestRegression:
    def test_full_store_workflow(self):
        reg = RepositoryRegistry()
        repo = FakeRepository()
        reg.register(repo, (DatasetType.PRICE_DAILY,))
        engine = StorageEngine(reg)
        req = _make_storage_request()
        result = engine.store(req)
        assert result.success is True
        assert result.storage_id == "fake_price_daily"

    def test_full_retrieve_workflow(self):
        reg = RepositoryRegistry()
        repo = FakeRepository()
        reg.register(repo, (DatasetType.PRICE_DAILY,))
        engine = StorageEngine(reg)
        req = _make_retrieval_request()
        result = engine.retrieve(req)
        assert len(result.records) == 1
        assert result.version == "v1"

    def test_all_dataset_types_represented(self):
        for dt in DatasetType:
            assert dt.value
            assert isinstance(dt.value, str)

    def test_cache_round_trip(self):
        cache = FakeCache()
        cache.put("key1", {"data": [1, 2, 3]})
        val = cache.get("key1")
        assert val == {"data": [1, 2, 3]}

    def test_version_lifecycle(self):
        ts1 = datetime(2024, 1, 1, tzinfo=UTC)
        ts2 = datetime(2024, 6, 1, tzinfo=UTC)
        v1 = DatasetVersion(provider="x", version="v1", created_at=ts1, checksum="", record_count=100)
        v2 = DatasetVersion(provider="x", version="v2", created_at=ts2, checksum="", record_count=200)
        assert is_newer(v1, v2) is True
        assert is_newer(v2, v1) is False

    def test_repository_multiple_types(self):
        reg = RepositoryRegistry()
        repo = FakeRepository(supported=(DatasetType.PRICE_DAILY, DatasetType.FINANCIALS))
        reg.register(repo, (DatasetType.PRICE_DAILY, DatasetType.FINANCIALS))
        assert reg.has_type(DatasetType.PRICE_DAILY) is True
        assert reg.has_type(DatasetType.FINANCIALS) is True
        assert reg.has_type(DatasetType.NEWS) is False
