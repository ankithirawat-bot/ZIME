"""
PostgreSQL Repository tests.

Uses SQLite in-memory for isolated testing.
No PostgreSQL instance required.
"""

from __future__ import annotations

from datetime import date, datetime

import pytest
from sqlalchemy import create_engine, text
from sqlalchemy.orm import sessionmaker

from backend.storage.exceptions import (
    DatasetNotFoundError,
    DuplicateDatasetError,
)
from backend.storage.models import (
    DatasetType,
    RetrievalRequest,
    StorageRequest,
)
from backend.storage.postgresql.connection import ConnectionManager, DatabaseConfig
from backend.storage.postgresql.migrations import MigrationRunner
from backend.storage.postgresql.orm_models import (
    Base,
    DailyPrice,
    DatasetVersion,
    Symbol,
    UpdateLog,
)
from backend.storage.postgresql.postgres_repository import PostgreSQLRepository
from backend.storage.postgresql.schema import ALL_DDL
from backend.storage.versioning import compute_checksum

# ---------------------------------------------------------------------------
# Fixtures
# ---------------------------------------------------------------------------


@pytest.fixture()
def engine():
    """Create an in-memory SQLite engine."""
    eng = create_engine("sqlite:///:memory:", echo=False)
    Base.metadata.create_all(eng)
    yield eng
    eng.dispose()


@pytest.fixture()
def conn_manager(engine):
    """Create a ConnectionManager backed by in-memory SQLite."""
    factory = sessionmaker(bind=engine)
    mgr = ConnectionManager.__new__(ConnectionManager)
    mgr._engine = engine
    mgr._session_factory = factory
    return mgr


@pytest.fixture()
def repo(conn_manager):
    """Create a PostgreSQLRepository with in-memory backend."""
    return PostgreSQLRepository(conn_manager)


@pytest.fixture()
def runner():
    """Create a MigrationRunner."""
    return MigrationRunner()


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


def _make_request(**overrides) -> StorageRequest:
    defaults = {
        "dataset": (
            {
                "symbol": "RELIANCE",
                "exchange": "NSE",
                "date": "2024-01-15T00:00:00",
                "open": 100.0,
                "high": 105.0,
                "low": 99.0,
                "close": 103.0,
                "volume": 50000,
            },
        ),
        "dataset_type": DatasetType.PRICE_DAILY,
        "provider": "upstox",
        "version": "upstox_price_daily_RELIANCE_20240115",
    }
    defaults.update(overrides)
    return StorageRequest(**defaults)


def _make_retrieval(**overrides) -> RetrievalRequest:
    defaults = {
        "dataset_type": DatasetType.PRICE_DAILY,
        "symbol": "RELIANCE",
        "start_date": date(2024, 1, 1),
        "end_date": date(2024, 12, 31),
    }
    defaults.update(overrides)
    return RetrievalRequest(**defaults)


# ---------------------------------------------------------------------------
# ORM Models
# ---------------------------------------------------------------------------


class TestSymbolModel:
    def test_creation(self, engine):
        from sqlalchemy.orm import Session
        with Session(engine) as session:
            s = Symbol(symbol="RELIANCE", exchange="NSE", instrument_type="EQ", provider_symbol="RELIANCE")
            session.add(s)
            session.commit()
            assert s.id is not None

    def test_unique_constraint(self, engine):
        from sqlalchemy.exc import IntegrityError
        from sqlalchemy.orm import Session
        with Session(engine) as session:
            s1 = Symbol(symbol="RELIANCE", exchange="NSE", instrument_type="EQ", provider_symbol="RELIANCE")
            session.add(s1)
            session.commit()
        with Session(engine) as session:
            s2 = Symbol(symbol="RELIANCE", exchange="NSE", instrument_type="EQ", provider_symbol="RELIANCE")
            session.add(s2)
            with pytest.raises(IntegrityError):
                session.commit()


class TestDailyPriceModel:
    def test_creation(self, engine):
        from sqlalchemy.orm import Session
        with Session(engine) as session:
            s = Symbol(symbol="TCS", exchange="NSE", instrument_type="EQ", provider_symbol="TCS")
            session.add(s)
            session.flush()
            p = DailyPrice(
                symbol_id=s.id,
                trade_date=datetime(2024, 1, 15),
                open=100.0, high=105.0, low=99.0, close=103.0,
                volume=50000, provider="upstox",
            )
            session.add(p)
            session.commit()
            assert p.id is not None

    def test_unique_constraint_on_symbol_date_provider(self, engine):
        from sqlalchemy.exc import IntegrityError
        from sqlalchemy.orm import Session
        with Session(engine) as session:
            s = Symbol(symbol="TCS", exchange="NSE", instrument_type="EQ", provider_symbol="TCS")
            session.add(s)
            session.flush()
            symbol_id = s.id
            p1 = DailyPrice(
                symbol_id=symbol_id,
                trade_date=datetime(2024, 1, 15),
                open=100.0, high=105.0, low=99.0, close=103.0,
                volume=50000, provider="upstox",
            )
            session.add(p1)
            session.commit()
        with Session(engine) as session:
            p2 = DailyPrice(
                symbol_id=symbol_id,
                trade_date=datetime(2024, 1, 15),
                open=101.0, high=106.0, low=100.0, close=104.0,
                volume=55000, provider="upstox",
            )
            session.add(p2)
            with pytest.raises(IntegrityError):
                session.commit()

    def test_different_provider_allowed_same_date(self, engine):
        from sqlalchemy.orm import Session
        with Session(engine) as session:
            s = Symbol(symbol="TCS", exchange="NSE", instrument_type="EQ", provider_symbol="TCS")
            session.add(s)
            session.flush()
            p1 = DailyPrice(
                symbol_id=s.id,
                trade_date=datetime(2024, 1, 15),
                open=100.0, high=105.0, low=99.0, close=103.0,
                volume=50000, provider="upstox",
            )
            p2 = DailyPrice(
                symbol_id=s.id,
                trade_date=datetime(2024, 1, 15),
                open=101.0, high=106.0, low=100.0, close=104.0,
                volume=55000, provider="yfinance",
            )
            session.add(p1)
            session.add(p2)
            session.commit()
            assert session.query(DailyPrice).count() == 2


class TestDatasetVersionModel:
    def test_creation(self, engine):
        from sqlalchemy.orm import Session
        with Session(engine) as session:
            v = DatasetVersion(
                symbol="RELIANCE", exchange="NSE",
                dataset_type="price_daily", provider="upstox",
                version="v1", checksum="abc", record_count=10,
            )
            session.add(v)
            session.commit()
            assert v.id is not None


class TestUpdateLogModel:
    def test_creation_with_new_fields(self, engine):
        from sqlalchemy.orm import Session
        with Session(engine) as session:
            log_entry = UpdateLog(
                symbol="RELIANCE", exchange="NSE",
                dataset_type="price_daily", provider="upstox",
                version="v1",
                start_date=datetime(2024, 1, 1),
                end_date=datetime(2024, 1, 31),
                records_inserted=10,
                status="success",
                started_at=datetime(2024, 2, 1, 10, 0),
                completed_at=datetime(2024, 2, 1, 10, 1),
            )
            session.add(log_entry)
            session.commit()
            assert log_entry.id is not None
            assert log_entry.records_inserted == 10
            assert log_entry.status == "success"
            assert log_entry.started_at is not None
            assert log_entry.completed_at is not None

    def test_optional_date_fields(self, engine):
        from sqlalchemy.orm import Session
        with Session(engine) as session:
            log_entry = UpdateLog(
                symbol="TCS", exchange="NSE",
                dataset_type="price_daily", provider="upstox",
                version="v2",
                records_inserted=0,
                status="pending",
            )
            session.add(log_entry)
            session.commit()
            assert log_entry.start_date is None
            assert log_entry.end_date is None
            assert log_entry.started_at is None
            assert log_entry.completed_at is None


# ---------------------------------------------------------------------------
# DatabaseConfig
# ---------------------------------------------------------------------------


class TestDatabaseConfig:
    def test_default_url(self):
        c = DatabaseConfig()
        assert "localhost" in c.url
        assert "5432" in c.url

    def test_url_with_password(self):
        c = DatabaseConfig(password="secret")
        assert "secret" in c.url

    def test_url_without_password(self):
        c = DatabaseConfig()
        assert "psycopg://" in c.url


# ---------------------------------------------------------------------------
# ConnectionManager
# ---------------------------------------------------------------------------


class TestConnectionManager:
    def test_init_requires_something(self):
        with pytest.raises(ValueError):
            ConnectionManager()

    def test_session_context(self, conn_manager):
        with conn_manager.session() as session:
            result = session.execute(text("SELECT 1"))
            assert result.scalar() == 1

    def test_transaction_context(self, conn_manager):
        with conn_manager.transaction() as session:
            s = Symbol(symbol="TEST", exchange="NSE", instrument_type="EQ", provider_symbol="TEST")
            session.add(s)
        with conn_manager.session() as session:
            assert session.query(Symbol).filter(Symbol.symbol == "TEST").count() == 1

    def test_transaction_rollback(self, conn_manager):
        with pytest.raises(RuntimeError):
            with conn_manager.transaction() as session:
                s = Symbol(symbol="FAIL", exchange="NSE", instrument_type="EQ", provider_symbol="FAIL")
                session.add(s)
                raise RuntimeError("simulated failure")

        with conn_manager.session() as session:
            assert session.query(Symbol).filter(Symbol.symbol == "FAIL").count() == 0

    def test_dispose(self, conn_manager):
        conn_manager.dispose()


# ---------------------------------------------------------------------------
# MigrationRunner
# ---------------------------------------------------------------------------


class TestMigrationRunner:
    def test_apply_all(self, runner):
        executed = runner.apply_all()
        assert len(executed) == len(ALL_DDL)

    def test_get_pending(self, runner):
        pending = runner.get_pending()
        assert len(pending) == len(ALL_DDL)

    def test_rollback(self, runner):
        dropped = runner.rollback()
        assert len(dropped) == 5
        assert any("symbols" in s for s in dropped)


# ---------------------------------------------------------------------------
# PostgreSQLRepository.store
# ---------------------------------------------------------------------------


class TestRepositoryStore:
    def test_store_single_record(self, repo):
        req = _make_request()
        result = repo.store(req)
        assert result.success is True
        assert result.storage_id != ""
        assert result.version == req.version

    def test_store_multiple_records(self, repo):
        records = (
            {"symbol": "TCS", "exchange": "NSE", "date": "2024-01-15T00:00:00", "open": 100.0, "high": 105.0, "low": 99.0, "close": 103.0, "volume": 50000},
            {"symbol": "TCS", "exchange": "NSE", "date": "2024-01-16T00:00:00", "open": 103.0, "high": 108.0, "low": 102.0, "close": 107.0, "volume": 60000},
        )
        req = _make_request(dataset=records, version="v_multi")
        result = repo.store(req)
        assert result.success is True

    def test_store_duplicate_raises(self, repo):
        req = _make_request()
        repo.store(req)
        with pytest.raises(DuplicateDatasetError):
            repo.store(req)

    def test_store_creates_symbol(self, repo):
        req = _make_request()
        repo.store(req)
        with repo._conn.session() as session:
            assert session.query(Symbol).filter(Symbol.symbol == "RELIANCE").count() == 1

    def test_store_creates_version(self, repo):
        req = _make_request()
        repo.store(req)
        with repo._conn.session() as session:
            v = session.query(DatasetVersion).filter(DatasetVersion.version == req.version).first()
            assert v is not None
            assert v.record_count == 1

    def test_store_creates_update_log(self, repo):
        req = _make_request()
        repo.store(req)
        with repo._conn.session() as session:
            log = session.query(UpdateLog).filter(UpdateLog.version == req.version).first()
            assert log is not None
            assert log.status == "success"
            assert log.records_inserted == 1
            assert log.started_at is not None
            assert log.completed_at is not None

    def test_store_update_log_date_range(self, repo):
        records = (
            {"symbol": "RELIANCE", "exchange": "NSE", "date": "2024-01-15T00:00:00", "open": 100.0, "high": 105.0, "low": 99.0, "close": 103.0, "volume": 50000},
            {"symbol": "RELIANCE", "exchange": "NSE", "date": "2024-01-20T00:00:00", "open": 103.0, "high": 108.0, "low": 102.0, "close": 107.0, "volume": 60000},
        )
        req = _make_request(dataset=records, version="v_dates")
        repo.store(req)
        with repo._conn.session() as session:
            log = session.query(UpdateLog).filter(UpdateLog.version == "v_dates").first()
            assert log is not None
            assert log.start_date is not None
            assert log.end_date is not None
            assert log.start_date <= log.end_date

    def test_store_reuses_existing_symbol(self, repo):
        req1 = _make_request()
        repo.store(req1)
        req2 = _make_request(
            version="v2",
            dataset=({"symbol": "RELIANCE", "exchange": "NSE", "date": "2024-01-16T00:00:00", "open": 103.0, "high": 108.0, "low": 102.0, "close": 107.0, "volume": 60000},),
        )
        result = repo.store(req2)
        assert result.success is True
        with repo._conn.session() as session:
            assert session.query(Symbol).filter(Symbol.symbol == "RELIANCE").count() == 1

    def test_store_atomic(self, repo):
        req = _make_request()
        result = repo.store(req)
        assert result.success is True

    def test_store_writes_price_data(self, repo):
        req = _make_request()
        repo.store(req)
        with repo._conn.session() as session:
            prices = session.query(DailyPrice).all()
            assert len(prices) == 1
            assert prices[0].open == 100.0
            assert prices[0].close == 103.0
            assert prices[0].trade_date is not None

    def test_store_with_metadata(self, repo):
        req = _make_request(metadata={"symbol": "RELIANCE", "exchange": "NSE"})
        result = repo.store(req)
        assert result.success is True


# ---------------------------------------------------------------------------
# PostgreSQLRepository.retrieve
# ---------------------------------------------------------------------------


class TestRepositoryRetrieve:
    def _store_reliance(self, repo):
        records = (
            {"symbol": "RELIANCE", "exchange": "NSE", "date": "2024-01-15T00:00:00", "open": 100.0, "high": 105.0, "low": 99.0, "close": 103.0, "volume": 50000},
            {"symbol": "RELIANCE", "exchange": "NSE", "date": "2024-01-16T00:00:00", "open": 103.0, "high": 108.0, "low": 102.0, "close": 107.0, "volume": 60000},
            {"symbol": "RELIANCE", "exchange": "NSE", "date": "2024-01-17T00:00:00", "open": 107.0, "high": 110.0, "low": 106.0, "close": 109.0, "volume": 45000},
        )
        repo.store(_make_request(dataset=records, version="v_retrieve"))

    def test_retrieve_existing(self, repo):
        self._store_reliance(repo)
        req = _make_retrieval()
        result = repo.retrieve(req)
        assert len(result.records) == 3
        assert result.provider == "upstox"

    def test_retrieve_date_filtered(self, repo):
        self._store_reliance(repo)
        req = _make_retrieval(
            start_date=date(2024, 1, 15),
            end_date=date(2024, 1, 16),
        )
        result = repo.retrieve(req)
        assert len(result.records) == 2

    def test_retrieve_not_found(self, repo):
        req = _make_retrieval(symbol="UNKNOWN")
        with pytest.raises(DatasetNotFoundError):
            repo.retrieve(req)

    def test_retrieve_records_ordered_by_date(self, repo):
        self._store_reliance(repo)
        req = _make_retrieval()
        result = repo.retrieve(req)
        dates = [r["date"] for r in result.records]
        assert dates == sorted(dates)

    def test_retrieve_record_fields(self, repo):
        self._store_reliance(repo)
        req = _make_retrieval()
        result = repo.retrieve(req)
        record = result.records[0]
        assert "date" in record
        assert "open" in record
        assert "high" in record
        assert "low" in record
        assert "close" in record
        assert "volume" in record
        assert "provider" in record


# ---------------------------------------------------------------------------
# PostgreSQLRepository.delete
# ---------------------------------------------------------------------------


class TestRepositoryDelete:
    def test_delete_existing(self, repo):
        req = _make_request()
        repo.store(req)
        assert repo.delete(DatasetType.PRICE_DAILY, "RELIANCE") is True

    def test_delete_nonexistent(self, repo):
        assert repo.delete(DatasetType.PRICE_DAILY, "UNKNOWN") is False

    def test_delete_removes_prices(self, repo):
        req = _make_request()
        repo.store(req)
        repo.delete(DatasetType.PRICE_DAILY, "RELIANCE")
        with repo._conn.session() as session:
            count = session.query(DailyPrice).count()
            assert count == 0

    def test_delete_creates_log(self, repo):
        req = _make_request()
        repo.store(req)
        repo.delete(DatasetType.PRICE_DAILY, "RELIANCE")
        with repo._conn.session() as session:
            logs = session.query(UpdateLog).filter(UpdateLog.status == "deleted").all()
            assert len(logs) >= 1


# ---------------------------------------------------------------------------
# PostgreSQLRepository.exists
# ---------------------------------------------------------------------------


class TestRepositoryExists:
    def test_exists_after_store(self, repo):
        req = _make_request()
        repo.store(req)
        assert repo.exists(DatasetType.PRICE_DAILY, "RELIANCE") is True

    def test_not_exists(self, repo):
        assert repo.exists(DatasetType.PRICE_DAILY, "UNKNOWN") is False


# ---------------------------------------------------------------------------
# PostgreSQLRepository.supported_dataset_types
# ---------------------------------------------------------------------------


class TestRepositorySupportedTypes:
    def test_supported_dataset_types(self, repo):
        types = repo.supported_dataset_types()
        assert DatasetType.PRICE_DAILY in types
        assert len(types) == 1


# ---------------------------------------------------------------------------
# Transaction integrity
# ---------------------------------------------------------------------------


class TestTransactionIntegrity:
    def test_partial_failure_no_side_effects(self, repo):
        records = (
            {"symbol": "ROLLBACK", "exchange": "NSE", "date": "2024-01-15T00:00:00", "open": 100.0, "high": 105.0, "low": 99.0, "close": 103.0, "volume": 50000},
        )
        req = _make_request(dataset=records, version="v_rollback")
        result = repo.store(req)
        assert result.success is True
        with repo._conn.session() as session:
            assert session.query(Symbol).filter(Symbol.symbol == "ROLLBACK").count() == 1

    def test_multiple_stores_different_versions(self, repo):
        req1 = _make_request(version="v1")
        req2 = _make_request(version="v2", dataset=({"symbol": "RELIANCE", "exchange": "NSE", "date": "2024-01-16T00:00:00", "open": 103.0, "high": 108.0, "low": 102.0, "close": 107.0, "volume": 60000},))
        assert repo.store(req1).success is True
        assert repo.store(req2).success is True
        with repo._conn.session() as session:
            assert session.query(DailyPrice).count() == 2


# ---------------------------------------------------------------------------
# Indexes
# ---------------------------------------------------------------------------


class TestIndexes:
    def test_schema_has_all_ddl(self):
        from backend.storage.postgresql.schema import (
            INDEX_PRICES_PROVIDER,
            INDEX_PRICES_SYMBOL_DATE,
            INDEX_VERSIONS_PROVIDER,
            INDEX_VERSIONS_SYMBOL,
            INDEX_VERSIONS_TYPE,
        )
        assert "idx_prices_symbol_date" in INDEX_PRICES_SYMBOL_DATE
        assert "idx_prices_provider" in INDEX_PRICES_PROVIDER
        assert "idx_versions_symbol" in INDEX_VERSIONS_SYMBOL
        assert "idx_versions_provider" in INDEX_VERSIONS_PROVIDER
        assert "idx_versions_type" in INDEX_VERSIONS_TYPE

    def test_ddl_count(self):
        assert len(ALL_DDL) == 30


# ---------------------------------------------------------------------------
# Duplicate protection
# ---------------------------------------------------------------------------


class TestDuplicateProtection:
    def test_same_version_rejected(self, repo):
        req = _make_request()
        repo.store(req)
        with pytest.raises(DuplicateDatasetError):
            repo.store(req)

    def test_different_version_accepted(self, repo):
        req1 = _make_request(version="v1")
        req2 = _make_request(version="v2", dataset=({"symbol": "RELIANCE", "exchange": "NSE", "date": "2024-01-16T00:00:00", "open": 103.0, "high": 108.0, "low": 102.0, "close": 107.0, "volume": 60000},))
        assert repo.store(req1).success is True
        assert repo.store(req2).success is True


# ---------------------------------------------------------------------------
# Regression
# ---------------------------------------------------------------------------


class TestRegression:
    def test_full_lifecycle(self, repo):
        req = _make_request()
        store_result = repo.store(req)
        assert store_result.success is True
        assert repo.exists(DatasetType.PRICE_DAILY, "RELIANCE") is True
        retrieval = repo.retrieve(_make_retrieval())
        assert len(retrieval.records) == 1
        assert repo.delete(DatasetType.PRICE_DAILY, "RELIANCE") is True
        assert repo.exists(DatasetType.PRICE_DAILY, "RELIANCE") is False

    def test_version_persistence(self, repo):
        req = _make_request(version="v_persist")
        repo.store(req)
        with repo._conn.session() as session:
            v = session.query(DatasetVersion).filter(DatasetVersion.version == "v_persist").first()
            assert v is not None
            assert v.record_count == 1

    def test_checksum_computed(self, repo):
        records = ({"symbol": "X", "exchange": "NSE", "date": "2024-01-15T00:00:00", "open": 100.0, "high": 105.0, "low": 99.0, "close": 103.0, "volume": 50000},)
        checksum = compute_checksum(records)
        assert len(checksum) == 64

    def test_multiple_symbols(self, repo):
        for sym in ["RELIANCE", "TCS", "INFY"]:
            req = _make_request(
                dataset=({"symbol": sym, "exchange": "NSE", "date": "2024-01-15T00:00:00", "open": 100.0, "high": 105.0, "low": 99.0, "close": 103.0, "volume": 50000},),
                version=f"v_{sym}",
            )
            result = repo.store(req)
            assert result.success is True
        with repo._conn.session() as session:
            assert session.query(Symbol).count() == 3

    def test_update_log_records_inserted(self, repo):
        records = (
            {"symbol": "RELIANCE", "exchange": "NSE", "date": "2024-01-15T00:00:00", "open": 100.0, "high": 105.0, "low": 99.0, "close": 103.0, "volume": 50000},
            {"symbol": "RELIANCE", "exchange": "NSE", "date": "2024-01-16T00:00:00", "open": 103.0, "high": 108.0, "low": 102.0, "close": 107.0, "volume": 60000},
            {"symbol": "RELIANCE", "exchange": "NSE", "date": "2024-01-17T00:00:00", "open": 107.0, "high": 110.0, "low": 106.0, "close": 109.0, "volume": 45000},
        )
        req = _make_request(dataset=records, version="v_log_count")
        repo.store(req)
        with repo._conn.session() as session:
            log = session.query(UpdateLog).filter(UpdateLog.version == "v_log_count").first()
            assert log is not None
            assert log.records_inserted == 3
