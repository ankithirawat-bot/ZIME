"""
Fundamentals platform tests.

Covers normalization, validation, storage, retrieval, point-in-time
(as_of) correctness, version history, duplicate detection, and
aggregation.
"""

from __future__ import annotations

from datetime import date

import pytest
from sqlalchemy import create_engine, text
from sqlalchemy.orm import sessionmaker

from backend.fundamentals.exceptions import (
    DuplicateStatementError,
    InvalidFundamentalError,
    UnsupportedStatementTypeError,
)
from backend.fundamentals.models import (
    BalanceSheet,
    CashFlowStatement,
    CompanyProfile,
    FundamentalBatch,
    FundamentalSnapshot,
    IncomeStatement,
    KeyRatios,
    ShareholdingPattern,
)
from backend.fundamentals.normalizer import FundamentalNormalizer
from backend.fundamentals.repository import FundamentalRepository
from backend.fundamentals.service import FundamentalService
from backend.fundamentals.types import PeriodType, StatementType
from backend.fundamentals.validator import FundamentalValidator
from backend.storage.postgresql.connection import ConnectionManager
from backend.storage.postgresql.orm_models import (
    Base,
    IncomeStatementORM,
)


@pytest.fixture()
def normalizer():
    return FundamentalNormalizer()


@pytest.fixture()
def validator():
    return FundamentalValidator()


@pytest.fixture()
def engine():
    eng = create_engine("sqlite:///:memory:", echo=False)
    Base.metadata.create_all(eng)
    yield eng
    eng.dispose()


@pytest.fixture()
def conn_manager(engine):
    factory = sessionmaker(bind=engine)
    mgr = ConnectionManager.__new__(ConnectionManager)
    mgr._engine = engine
    mgr._session_factory = factory
    return mgr


@pytest.fixture()
def repository(conn_manager):
    return FundamentalRepository(conn_manager)


@pytest.fixture()
def service(repository):
    return FundamentalService(repository)


def _income(fy=2024, provider="screener", quarter=None, rev=1000.0, ni=100.0, eff_from=None, eff_to=None):
    return IncomeStatement(
        symbol="RELIANCE", exchange="NSE", provider=provider,
        period_type=PeriodType.ANNUAL if quarter is None else PeriodType.QUARTERLY,
        fiscal_year=fy, report_date=date(fy, 3, 31),
        filing_date=date(fy, 5, 30),
        fiscal_quarter=quarter,
        data={"revenue": rev, "net_income": ni, "ebitda": rev * 0.2},
        effective_from=eff_from,
        effective_to=eff_to,
    )


def _profile(fy=2024, provider="screener", name="Reliance Industries"):
    return CompanyProfile(
        symbol="RELIANCE", exchange="NSE", provider=provider,
        period_type=PeriodType.ANNUAL, fiscal_year=fy,
        report_date=date(fy, 3, 31), filing_date=date(fy, 5, 30),
        name=name, sector="Energy", industry="Oil & Gas",
        data={"market_cap": 1_000_000.0},
    )


def _balance(fy=2024, provider="screener", assets=5000.0):
    return BalanceSheet(
        symbol="RELIANCE", exchange="NSE", provider=provider,
        period_type=PeriodType.ANNUAL, fiscal_year=fy,
        report_date=date(fy, 3, 31), filing_date=date(fy, 5, 30),
        data={"total_assets": assets, "total_equity": assets * 0.5},
    )


def _cashflow(fy=2024, provider="screener", ocf=300.0):
    return CashFlowStatement(
        symbol="RELIANCE", exchange="NSE", provider=provider,
        period_type=PeriodType.ANNUAL, fiscal_year=fy,
        report_date=date(fy, 3, 31), filing_date=date(fy, 5, 30),
        data={"operating_cash_flow": ocf, "free_cash_flow": ocf * 0.8},
    )


def _shareholding(fy=2024, provider="screener", promoter=50.0, fii=20.0, dii=15.0, public=15.0):
    return ShareholdingPattern(
        symbol="RELIANCE", exchange="NSE", provider=provider,
        period_type=PeriodType.ANNUAL, fiscal_year=fy,
        report_date=date(fy, 3, 31), filing_date=date(fy, 5, 30),
        data={"promoter": promoter, "fii": fii, "dii": dii, "public": public},
    )


def _ratios(fy=2024, provider="screener", pe=20.0, roe=15.0):
    return KeyRatios(
        symbol="RELIANCE", exchange="NSE", provider=provider,
        period_type=PeriodType.ANNUAL, fiscal_year=fy,
        report_date=date(fy, 3, 31), filing_date=date(fy, 5, 30),
        data={"pe_ratio": pe, "roe": roe, "debt_to_equity": 0.4},
    )


class TestNormalizer:
    def test_normalize_income(self, normalizer):
        payload = {
            "symbol": "RELIANCE", "statement_type": "income_statement",
            "period_type": "annual", "fiscal_year": 2024,
            "report_date": "2024-03-31", "filing_date": "2024-05-30",
            "data": {"revenue": 1000.0},
        }
        model = normalizer.normalize(payload, "screener")
        assert isinstance(model, IncomeStatement)
        assert model.fiscal_year == 2024
        assert model.data["revenue"] == 1000.0

    def test_normalize_profile(self, normalizer):
        payload = {
            "symbol": "RELIANCE", "statement_type": "company_profile",
            "period_type": "annual", "fiscal_year": 2024,
            "report_date": "2024-03-31", "filing_date": "2024-05-30",
            "name": "Reliance Industries", "sector": "Energy",
        }
        model = normalizer.normalize(payload, "screener")
        assert isinstance(model, CompanyProfile)
        assert model.name == "Reliance Industries"

    def test_normalize_aliases(self, normalizer):
        payload = {
            "symbol": "TCS", "type": "balance_sheet",
            "period_type": "quarterly", "fiscal_year": 2024, "fiscal_quarter": 1,
            "period_end": "2024-06-30", "published_date": "2024-07-15",
        }
        model = normalizer.normalize(payload, "csv")
        assert isinstance(model, BalanceSheet)
        assert model.period_type is PeriodType.QUARTERLY
        assert model.fiscal_quarter == 1

    def test_normalize_missing_type(self, normalizer):
        payload = {"symbol": "TCS", "fiscal_year": 2024}
        with pytest.raises(ValueError):
            normalizer.normalize(payload, "csv")

    def test_normalize_missing_symbol(self, normalizer):
        payload = {"statement_type": "income_statement", "fiscal_year": 2024}
        with pytest.raises(ValueError):
            normalizer.normalize(payload, "csv")

    def test_normalize_invalid_fy(self, normalizer):
        payload = {
            "symbol": "TCS", "statement_type": "income_statement",
            "period_type": "annual", "fiscal_year": 0,
            "report_date": "2024-03-31", "filing_date": "2024-05-30",
        }
        with pytest.raises(ValueError):
            normalizer.normalize(payload, "csv")

    def test_normalize_unsupported_type(self, normalizer):
        payload = {
            "symbol": "TCS", "statement_type": "mystery", "fiscal_year": 2024,
            "report_date": "2024-03-31", "filing_date": "2024-05-30",
        }
        with pytest.raises(UnsupportedStatementTypeError):
            normalizer.normalize(payload, "csv")

    def test_normalize_extra_fields_to_data(self, normalizer):
        payload = {
            "symbol": "TCS", "statement_type": "key_ratios",
            "period_type": "annual", "fiscal_year": 2024,
            "report_date": "2024-03-31", "filing_date": "2024-05-30",
            "pe_ratio": 22.0, "custom_metric": 1.5,
        }
        model = normalizer.normalize(payload, "csv")
        assert model.data["pe_ratio"] == 22.0
        assert model.data["custom_metric"] == 1.5


class TestValidator:
    def test_valid_income(self, validator):
        report = validator.validate_batch(FundamentalBatch(statements=(_income(),)))
        assert report.valid is True
        assert len(report.valid_records) == 1

    def test_missing_symbol(self, validator):
        bad = IncomeStatement(
            symbol="", exchange="NSE", provider="p",
            period_type=PeriodType.ANNUAL, fiscal_year=2024,
            report_date=date(2024, 3, 31), filing_date=date(2024, 5, 30),
        )
        report = validator.validate_batch(FundamentalBatch(statements=(bad,)))
        assert report.valid is False

    def test_filing_before_report(self, validator):
        bad = IncomeStatement(
            symbol="RELIANCE", exchange="NSE", provider="p",
            period_type=PeriodType.ANNUAL, fiscal_year=2024,
            report_date=date(2024, 5, 30), filing_date=date(2024, 3, 31),
        )
        report = validator.validate_batch(FundamentalBatch(statements=(bad,)))
        assert report.valid is False

    def test_invalid_fiscal_year(self, validator):
        bad = IncomeStatement(
            symbol="RELIANCE", exchange="NSE", provider="p",
            period_type=PeriodType.ANNUAL, fiscal_year=0,
            report_date=date(2024, 3, 31), filing_date=date(2024, 5, 30),
        )
        report = validator.validate_batch(FundamentalBatch(statements=(bad,)))
        assert report.valid is False

    def test_invalid_quarter(self, validator):
        bad = _income(quarter=9)
        report = validator.validate_batch(FundamentalBatch(statements=(bad,)))
        assert report.valid is False

    def test_duplicate_detection(self, validator):
        report = validator.validate_batch(FundamentalBatch(statements=(_income(), _income())))
        assert report.valid is False
        assert len(report.duplicate_keys) == 1

    def test_detect_duplicates_helper(self, validator):
        dups = validator.detect_duplicates((_income(), _income()))
        assert len(dups) == 1

    def test_shareholding_over_100(self, validator):
        bad = _shareholding(promoter=60, fii=30, dii=20, public=10)
        report = validator.validate_batch(FundamentalBatch(statements=(bad,)))
        assert report.valid is False

    def test_shareholding_valid(self, validator):
        report = validator.validate_batch(FundamentalBatch(statements=(_shareholding(),)))
        assert report.valid is True

    def test_nan_value_rejected(self, validator):
        import math

        bad = _income()
        object.__setattr__(bad, "data", {"revenue": math.nan})
        report = validator.validate_batch(FundamentalBatch(statements=(bad,)))
        assert report.valid is False

    def test_effective_to_before_from(self, validator):
        bad = _income()
        object.__setattr__(bad, "effective_from", date(2024, 1, 1))
        object.__setattr__(bad, "effective_to", date(2023, 1, 1))
        report = validator.validate_batch(FundamentalBatch(statements=(bad,)))
        assert report.valid is False

    def test_validate_single_raises(self, validator):
        bad = IncomeStatement(
            symbol="RELIANCE", exchange="NSE", provider="p",
            period_type=PeriodType.ANNUAL, fiscal_year=0,
            report_date=date(2024, 3, 31), filing_date=date(2024, 5, 30),
        )
        with pytest.raises(InvalidFundamentalError):
            validator.validate(bad)


class TestRepositoryStorage:
    def test_store_and_retrieve(self, repository):
        repository.store(_income())
        rows = repository.retrieve("RELIANCE", "NSE", StatementType.INCOME_STATEMENT)
        assert len(rows) == 1
        assert rows[0].data["revenue"] == 1000.0

    def test_store_batch(self, repository):
        batch = FundamentalBatch(statements=(_income(), _balance(), _profile()))
        stored = repository.store_batch(batch)
        assert stored == 3
        assert repository.exists("RELIANCE", "NSE", StatementType.INCOME_STATEMENT)
        assert repository.exists("RELIANCE", "NSE", StatementType.BALANCE_SHEET)
        assert repository.exists("RELIANCE", "NSE", StatementType.PROFILE)

    def test_retrieve_unknown_symbol(self, repository):
        assert repository.retrieve("UNKNOWN", "NSE", StatementType.INCOME_STATEMENT) == ()

    def test_duplicate_raises(self, repository):
        repository.store(_income())
        with pytest.raises(DuplicateStatementError):
            repository.store(_income())

    def test_exists_false(self, repository):
        assert repository.exists("UNKNOWN", "NSE", StatementType.INCOME_STATEMENT) is False

    def test_delete(self, repository):
        repository.store(_income())
        deleted = repository.delete("RELIANCE", "NSE", StatementType.INCOME_STATEMENT)
        assert deleted == 1
        assert repository.exists("RELIANCE", "NSE", StatementType.INCOME_STATEMENT) is False

    def test_delete_unknown(self, repository):
        assert repository.delete("UNKNOWN", "NSE", StatementType.INCOME_STATEMENT) == 0

    def test_profile_specific_fields(self, repository):
        repository.store(_profile(name="Reliance Industries"))
        rows = repository.retrieve("RELIANCE", "NSE", StatementType.PROFILE)
        assert rows[0].name == "Reliance Industries"
        assert rows[0].sector == "Energy"

    def test_orm_persisted(self, repository):
        repository.store(_income())
        with repository._conn.session() as session:
            rows = session.query(IncomeStatementORM).all()
            assert len(rows) == 1
            assert rows[0].period_type == "annual"

    def test_metadata_json_fallback(self, repository):
        repository.store(_income())
        with repository._conn.session() as session:
            session.execute(
                text("UPDATE income_statements SET metadata_json = 'BAD' WHERE id = 1")
            )
            session.commit()
        rows = repository.retrieve("RELIANCE", "NSE", StatementType.INCOME_STATEMENT)
        assert rows[0].metadata == {}

    def test_data_json_fallback(self, repository):
        repository.store(_income())
        with repository._conn.session() as session:
            session.execute(
                text("UPDATE income_statements SET data_json = 'BAD' WHERE id = 1")
            )
            session.commit()
        rows = repository.retrieve("RELIANCE", "NSE", StatementType.INCOME_STATEMENT)
        assert rows[0].data == {}


class TestRepositoryPointInTime:
    def test_as_of_excludes_future(self, repository):
        repository.store(_income())
        rows = repository.retrieve_as_of(
            "RELIANCE", "NSE", StatementType.INCOME_STATEMENT, date(2024, 1, 1)
        )
        assert rows == ()

    def test_as_of_includes_published(self, repository):
        repository.store(_income())
        rows = repository.retrieve_as_of(
            "RELIANCE", "NSE", StatementType.INCOME_STATEMENT, date(2024, 6, 1)
        )
        assert len(rows) == 1

    def test_version_history_picks_latest(self, repository):
        original = _income(rev=1000.0, eff_from=date(2024, 5, 30))
        restated = _income(rev=1100.0, eff_from=date(2024, 9, 1))
        repository.store(original)
        repository.store(restated)
        early = repository.retrieve_as_of(
            "RELIANCE", "NSE", StatementType.INCOME_STATEMENT, date(2024, 6, 1)
        )
        assert early[0].data["revenue"] == 1000.0
        late = repository.retrieve_as_of(
            "RELIANCE", "NSE", StatementType.INCOME_STATEMENT, date(2024, 10, 1)
        )
        assert late[0].data["revenue"] == 1100.0

    def test_effective_to_expiry(self, repository):
        expired = _income(rev=1000.0, eff_from=date(2024, 5, 30), eff_to=date(2024, 8, 1))
        repository.store(expired)
        rows = repository.retrieve_as_of(
            "RELIANCE", "NSE", StatementType.INCOME_STATEMENT, date(2024, 9, 1)
        )
        assert rows == ()


class TestService:
    def test_retrieve(self, service):
        service._repo.store(_income())
        rows = service.retrieve("RELIANCE", "NSE", StatementType.INCOME_STATEMENT)
        assert len(rows) == 1

    def test_retrieve_as_of(self, service):
        service._repo.store(_income())
        rows = service.retrieve_as_of(
            "RELIANCE", "NSE", StatementType.INCOME_STATEMENT, date(2024, 6, 1)
        )
        assert len(rows) == 1

    def test_latest_snapshot(self, service):
        service._repo.store_batch(
            FundamentalBatch(statements=(_income(fy=2023), _income(fy=2024), _balance(fy=2024)))
        )
        snap = service.latest_snapshot("RELIANCE", "NSE")
        assert isinstance(snap, FundamentalSnapshot)
        assert StatementType.INCOME_STATEMENT in snap.statements
        assert StatementType.BALANCE_SHEET in snap.statements
        assert snap.statements[StatementType.INCOME_STATEMENT].fiscal_year == 2024

    def test_latest_snapshot_as_of(self, service):
        service._repo.store(_income(fy=2023, eff_from=date(2023, 5, 30)))
        service._repo.store(_income(fy=2024, eff_from=date(2024, 5, 30)))
        snap = service.latest_snapshot("RELIANCE", "NSE", as_of=date(2023, 12, 1))
        assert snap.statements[StatementType.INCOME_STATEMENT].fiscal_year == 2023

    def test_aggregate(self, service):
        service._repo.store_batch(
            FundamentalBatch(statements=(_income(fy=2023, rev=900.0), _income(fy=2024, rev=1000.0)))
        )
        result = service.aggregate(
            "RELIANCE", "NSE", StatementType.INCOME_STATEMENT, "revenue"
        )
        assert result == {2023: 900.0, 2024: 1000.0}

    def test_aggregate_as_of(self, service):
        service._repo.store(_income(fy=2024, rev=1000.0, eff_from=date(2024, 5, 30)))
        service._repo.store(_income(fy=2024, rev=1100.0, eff_from=date(2024, 9, 1)))
        result = service.aggregate(
            "RELIANCE", "NSE", StatementType.INCOME_STATEMENT, "revenue",
            as_of=date(2024, 6, 1),
        )
        assert result == {2024: 1000.0}

    def test_aggregate_empty(self, service):
        result = service.aggregate(
            "UNKNOWN", "NSE", StatementType.INCOME_STATEMENT, "revenue"
        )
        assert result == {}

    def test_latest_snapshot_no_data(self, service):
        snap = service.latest_snapshot("UNKNOWN", "NSE")
        assert snap.statements == {}


class TestImmutability:
    def test_model_frozen(self):
        model = _income()
        with pytest.raises(Exception):
            model.symbol = "X"

    def test_profile_frozen(self):
        model = _profile()
        with pytest.raises(Exception):
            model.name = "X"
