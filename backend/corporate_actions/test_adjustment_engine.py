"""
Corporate Actions tests.

Covers normalization, validation, adjustment correctness,
chronological ordering, duplicate detection and PostgreSQL
persistence.
"""

from __future__ import annotations

from datetime import date

import pytest
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker

from backend.corporate_actions.adjustment_engine import AdjustmentEngine
from backend.corporate_actions.exceptions import (
    DuplicateActionError,
    InvalidActionError,
    UnsupportedActionTypeError,
)
from backend.corporate_actions.models import (
    AdjustmentRequest,
    CorporateAction,
    CorporateActionBatch,
)
from backend.corporate_actions.normalizer import CorporateActionNormalizer
from backend.corporate_actions.repository import CorporateActionRepository
from backend.corporate_actions.types import ActionType
from backend.corporate_actions.validator import (
    CorporateActionValidator,
)
from backend.storage.postgresql.connection import ConnectionManager
from backend.storage.postgresql.orm_models import (
    Base,
    Symbol,
)
from backend.storage.postgresql.orm_models import (
    CorporateAction as CorporateActionORM,
)

# ---------------------------------------------------------------------------
# Fixtures
# ---------------------------------------------------------------------------


@pytest.fixture()
def normalizer():
    return CorporateActionNormalizer()


@pytest.fixture()
def validator():
    return CorporateActionValidator()


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
    return CorporateActionRepository(conn_manager)


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


def _split(symbol="RELIANCE", ratio=2.0, eff=date(2024, 6, 1), provider="upstox"):
    return CorporateAction(
        symbol=symbol,
        exchange="NSE",
        action_type=ActionType.SPLIT,
        effective_date=eff,
        provider=provider,
        ratio=ratio,
    )


def _bonus(symbol="RELIANCE", ratio=2.0, eff=date(2024, 6, 1), provider="upstox"):
    return CorporateAction(
        symbol=symbol,
        exchange="NSE",
        action_type=ActionType.BONUS,
        effective_date=eff,
        provider=provider,
        ratio=ratio,
    )


def _dividend(symbol="RELIANCE", amount=10.0, eff=date(2024, 6, 1), provider="upstox"):
    return CorporateAction(
        symbol=symbol,
        exchange="NSE",
        action_type=ActionType.DIVIDEND,
        effective_date=eff,
        provider=provider,
        cash_amount=amount,
        currency="INR",
    )


def _rights(symbol="RELIANCE", ratio=1.5, eff=date(2024, 6, 1), provider="upstox"):
    return CorporateAction(
        symbol=symbol,
        exchange="NSE",
        action_type=ActionType.RIGHTS,
        effective_date=eff,
        provider=provider,
        ratio=ratio,
        metadata={"issue_price": 500.0},
    )


def _buyback(symbol="RELIANCE", eff=date(2024, 6, 1), provider="upstox"):
    return CorporateAction(
        symbol=symbol,
        exchange="NSE",
        action_type=ActionType.BUYBACK,
        effective_date=eff,
        provider=provider,
        metadata={"amount": 5000.0},
    )


def _raw_prices():
    return (
        {"date": "2024-05-30", "open": 200.0, "high": 210.0, "low": 195.0, "close": 205.0, "volume": 1000},
        {"date": "2024-05-31", "open": 205.0, "high": 215.0, "low": 200.0, "close": 210.0, "volume": 1100},
        {"date": "2024-06-03", "open": 105.0, "high": 108.0, "low": 102.0, "close": 106.0, "volume": 2200},
        {"date": "2024-06-04", "open": 106.0, "high": 109.0, "low": 104.0, "close": 107.0, "volume": 2300},
    )


# ---------------------------------------------------------------------------
# Normalizer
# ---------------------------------------------------------------------------


class TestNormalizer:
    def test_normalize_split(self, normalizer):
        payload = {"symbol": "RELIANCE", "action_type": "split", "ratio": 2.0, "effective_date": "2024-06-01"}
        action = normalizer.normalize(payload, "upstox")
        assert action.action_type is ActionType.SPLIT
        assert action.ratio == 2.0
        assert action.provider == "upstox"
        assert action.effective_date == date(2024, 6, 1)

    def test_normalize_alias_type(self, normalizer):
        payload = {"symbol": "TCS", "type": "bonus", "ratio": 1.5, "effective_date": "2024-03-01"}
        action = normalizer.normalize(payload, "csv")
        assert action.action_type is ActionType.BONUS

    def test_normalize_case_insensitive(self, normalizer):
        payload = {"symbol": "TCS", "action_type": "DIVIDEND", "amount": 5.0, "effective_date": "2024-03-01"}
        action = normalizer.normalize(payload, "csv")
        assert action.action_type is ActionType.DIVIDEND

    def test_normalize_unsupported(self, normalizer):
        payload = {"symbol": "TCS", "action_type": "merger", "effective_date": "2024-03-01"}
        with pytest.raises(UnsupportedActionTypeError):
            normalizer.normalize(payload, "csv")

    def test_normalize_missing_type(self, normalizer):
        payload = {"symbol": "TCS", "effective_date": "2024-03-01"}
        with pytest.raises(ValueError):
            normalizer.normalize(payload, "csv")

    def test_normalize_missing_date(self, normalizer):
        payload = {"symbol": "TCS", "action_type": "split", "ratio": 2.0}
        with pytest.raises(ValueError):
            normalizer.normalize(payload, "csv")

    def test_normalize_batch(self, normalizer):
        payloads = [
            {"symbol": "RELIANCE", "action_type": "split", "ratio": 2.0, "effective_date": "2024-06-01"},
            {"symbol": "TCS", "action_type": "dividend", "amount": 5.0, "effective_date": "2024-03-01"},
        ]
        batch = normalizer.normalize_batch(payloads, "upstox", source="file.json")
        assert len(batch.actions) == 2
        assert batch.source == "file.json"

    def test_normalize_metadata_preserved(self, normalizer):
        payload = {
            "symbol": "RELIANCE",
            "action_type": "rights",
            "ratio": 1.5,
            "effective_date": "2024-06-01",
            "metadata": {"issue_price": 500.0},
        }
        action = normalizer.normalize(payload, "upstox")
        assert action.metadata == {"issue_price": 500.0}

    def test_immutable_model(self, normalizer):
        payload = {"symbol": "RELIANCE", "action_type": "split", "ratio": 2.0, "effective_date": "2024-06-01"}
        action = normalizer.normalize(payload, "upstox")
        with pytest.raises(Exception):
            action.ratio = 3.0

    def test_normalize_datetime_date(self, normalizer):
        from datetime import datetime as _dt

        payload = {
            "symbol": "RELIANCE", "action_type": "split", "ratio": 2.0,
            "effective_date": _dt(2024, 6, 1, 10, 0),
        }
        action = normalizer.normalize(payload, "upstox")
        assert action.effective_date == date(2024, 6, 1)

    def test_normalize_bad_date_type(self, normalizer):
        payload = {"symbol": "RELIANCE", "action_type": "split", "ratio": 2.0, "effective_date": 12345}
        with pytest.raises(ValueError):
            normalizer.normalize(payload, "upstox")

    def test_normalize_non_dict_metadata(self, normalizer):
        payload = {
            "symbol": "RELIANCE", "action_type": "split", "ratio": 2.0,
            "effective_date": "2024-06-01", "metadata": "not-a-dict",
        }
        action = normalizer.normalize(payload, "upstox")
        assert action.metadata == {}

    def test_resolve_type_unsupported_direct(self, normalizer):
        from backend.corporate_actions.exceptions import UnsupportedActionTypeError

        with pytest.raises(UnsupportedActionTypeError):
            normalizer._resolve_type("merger")


# ---------------------------------------------------------------------------
# Validator
# ---------------------------------------------------------------------------


class TestValidator:
    def test_valid_split(self, validator):
        report = validator.validate_batch(CorporateActionBatch(actions=(_split(),)))
        assert report.valid is True
        assert len(report.valid_actions) == 1

    def test_buyback_requires_metadata(self, validator):
        bad = _buyback()
        report = validator.validate_batch(CorporateActionBatch(actions=(bad,)))
        assert report.valid is False

    def test_invalid_ratio_zero(self, validator):
        bad = _split(ratio=0.0)
        report = validator.validate_batch(CorporateActionBatch(actions=(bad,)))
        assert report.valid is False

    def test_invalid_ratio_one(self, validator):
        bad = _split(ratio=1.0)
        report = validator.validate_batch(CorporateActionBatch(actions=(bad,)))
        assert report.valid is False

    def test_negative_cash_dividend(self, validator):
        bad = _dividend(amount=-5.0)
        report = validator.validate_batch(CorporateActionBatch(actions=(bad,)))
        assert report.valid is False

    def test_duplicate_detection(self, validator):
        actions = (_split(), _split())
        report = validator.validate_batch(CorporateActionBatch(actions=actions))
        assert report.valid is False
        assert len(report.duplicate_keys) == 1

    def test_detect_duplicates_helper(self, validator):
        dups = validator.detect_duplicates((_split(), _split()))
        assert len(dups) == 1

    def test_overlapping_not_blocked_for_different_type(self, validator):
        actions = (_split(), _dividend())
        report = validator.validate_batch(CorporateActionBatch(actions=actions))
        assert report.valid is True

    def test_missing_symbol(self, validator):
        bad = CorporateAction(
            symbol="", exchange="NSE", action_type=ActionType.SPLIT,
            effective_date=date(2024, 1, 1), provider="p", ratio=2.0,
        )
        report = validator.validate_batch(CorporateActionBatch(actions=(bad,)))
        assert report.valid is False

    def test_rights_valid_with_ratio(self, validator):
        report = validator.validate_batch(CorporateActionBatch(actions=(_rights(),)))
        assert report.valid is True

    def test_rights_requires_metadata(self, validator):
        bad = CorporateAction(
            symbol="X", exchange="NSE", action_type=ActionType.RIGHTS,
            effective_date=date(2024, 1, 1), provider="p",
            ratio=None, cash_amount=None,
        )
        report = validator.validate_batch(CorporateActionBatch(actions=(bad,)))
        assert report.valid is False

    def test_validate_single_raises(self, validator):
        with pytest.raises(InvalidActionError):
            validator.validate(_split(ratio=0.0))


# ---------------------------------------------------------------------------
# Adjustment Engine
# ---------------------------------------------------------------------------


class TestAdjustmentEngine:
    def test_engine_initialization(self):
        engine = AdjustmentEngine()
        assert len(engine._handlers) == 5

    def test_apply_split_factor(self):
        engine = AdjustmentEngine()
        factor = engine.apply_split(_split(ratio=2.0))
        assert factor == 0.5

    def test_apply_bonus_factor(self):
        engine = AdjustmentEngine()
        factor = engine.apply_bonus(_bonus(ratio=2.0))
        assert factor == 0.5

    def test_apply_dividend_factor(self):
        engine = AdjustmentEngine()
        factor = engine.apply_dividend(_dividend(amount=10.0))
        assert factor == 10.0

    def test_apply_rights_neutral(self):
        engine = AdjustmentEngine()
        assert engine.apply_rights(_rights()) == 1.0

    def test_apply_buyback_neutral(self):
        engine = AdjustmentEngine()
        assert engine.apply_buyback(_buyback()) == 1.0

    def test_split_adjustment(self):
        engine = AdjustmentEngine()
        req = AdjustmentRequest(
            symbol="RELIANCE", exchange="NSE",
            raw_prices=_raw_prices(), actions=(_split(ratio=2.0),),
        )
        result = engine.adjust_prices(req)
        pre = next(p for p in result.prices if p.trade_date == date(2024, 5, 30))
        post = next(p for p in result.prices if p.trade_date == date(2024, 6, 3))
        assert pre.close == 102.5
        assert pre.volume == 2000
        assert post.close == 106.0
        assert post.volume == 2200
        assert result.raw_preserved is True

    def test_raw_preserved(self):
        engine = AdjustmentEngine()
        req = AdjustmentRequest(
            symbol="RELIANCE", exchange="NSE",
            raw_prices=_raw_prices(), actions=(_split(ratio=2.0),),
        )
        result = engine.adjust_prices(req)
        for p in result.prices:
            assert p.raw_close == pytest.approx(p.close / p.factor)

    def test_bonus_adjustment(self):
        engine = AdjustmentEngine()
        req = AdjustmentRequest(
            symbol="RELIANCE", exchange="NSE",
            raw_prices=_raw_prices(), actions=(_bonus(ratio=1.5),),
        )
        result = engine.adjust_prices(req)
        pre = next(p for p in result.prices if p.trade_date == date(2024, 5, 30))
        assert pre.close == pytest.approx(205.0 / 1.5)

    def test_dividend_adjustment_close_only(self):
        engine = AdjustmentEngine()
        req = AdjustmentRequest(
            symbol="RELIANCE", exchange="NSE",
            raw_prices=_raw_prices(), actions=(_dividend(amount=10.0),),
        )
        result = engine.adjust_prices(req)
        pre = next(p for p in result.prices if p.trade_date == date(2024, 5, 30))
        assert pre.close == 205.0
        assert pre.open == 200.0
        assert pre.adjusted_close == 195.0
        assert pre.volume == 1000

    def test_multiple_events(self):
        engine = AdjustmentEngine()
        actions = (_split(ratio=2.0), _dividend(amount=10.0))
        req = AdjustmentRequest(
            symbol="RELIANCE", exchange="NSE",
            raw_prices=_raw_prices(), actions=actions,
        )
        result = engine.adjust_prices(req)
        pre = next(p for p in result.prices if p.trade_date == date(2024, 5, 30))
        post = next(p for p in result.prices if p.trade_date == date(2024, 6, 3))
        assert pre.close == 102.5
        assert pre.adjusted_close == pytest.approx(102.5 - 10.0)
        assert post.close == 106.0
        assert post.adjusted_close == 106.0

    def test_chronological_ordering(self):
        engine = AdjustmentEngine()
        earlier = AdjustmentRequest(
            symbol="RELIANCE", exchange="NSE",
            raw_prices=_raw_prices(), actions=(_split(ratio=2.0, eff=date(2024, 6, 1)),),
        )
        result = engine.adjust_prices(earlier)
        dates = sorted(p.trade_date for p in result.prices)
        assert dates[0] < date(2024, 6, 1) < dates[-1]

    def test_rights_no_adjustment(self):
        engine = AdjustmentEngine()
        req = AdjustmentRequest(
            symbol="RELIANCE", exchange="NSE",
            raw_prices=_raw_prices(), actions=(_rights(),),
        )
        result = engine.adjust_prices(req)
        pre = next(p for p in result.prices if p.trade_date == date(2024, 5, 30))
        assert pre.close == 205.0

    def test_buyback_no_adjustment(self):
        engine = AdjustmentEngine()
        req = AdjustmentRequest(
            symbol="RELIANCE", exchange="NSE",
            raw_prices=_raw_prices(), actions=(_buyback(),),
        )
        result = engine.adjust_prices(req)
        pre = next(p for p in result.prices if p.trade_date == date(2024, 5, 30))
        assert pre.close == 205.0

    def test_as_of_filter(self):
        engine = AdjustmentEngine()
        req = AdjustmentRequest(
            symbol="RELIANCE", exchange="NSE",
            raw_prices=_raw_prices(), actions=(_split(ratio=2.0),),
            as_of=date(2024, 5, 31),
        )
        result = engine.adjust_prices(req)
        pre = next(p for p in result.prices if p.trade_date == date(2024, 5, 30))
        assert pre.close == 205.0

    def test_actions_applied_reported(self):
        engine = AdjustmentEngine()
        req = AdjustmentRequest(
            symbol="RELIANCE", exchange="NSE",
            raw_prices=_raw_prices(), actions=(_split(ratio=2.0), _dividend(amount=5.0)),
        )
        result = engine.adjust_prices(req)
        assert len(result.actions_applied) == 2

    def test_split_without_ratio_neutral(self):
        engine = AdjustmentEngine()
        bad = _split(ratio=None)
        req = AdjustmentRequest(
            symbol="RELIANCE", exchange="NSE",
            raw_prices=_raw_prices(), actions=(bad,),
        )
        result = engine.adjust_prices(req)
        pre = next(p for p in result.prices if p.trade_date == date(2024, 5, 30))
        assert pre.close == 205.0

    def test_dividend_negative_cash_neutral(self):
        engine = AdjustmentEngine()
        bad = _dividend(amount=-5.0)
        req = AdjustmentRequest(
            symbol="RELIANCE", exchange="NSE",
            raw_prices=_raw_prices(), actions=(bad,),
        )
        result = engine.adjust_prices(req)
        pre = next(p for p in result.prices if p.trade_date == date(2024, 5, 30))
        assert pre.adjusted_close == 205.0

    def test_parse_date_datetime_object(self):
        engine = AdjustmentEngine()
        from datetime import datetime as _dt

        req = AdjustmentRequest(
            symbol="RELIANCE", exchange="NSE",
            raw_prices=(
                {"date": _dt(2024, 5, 30), "open": 200.0, "high": 210.0, "low": 195.0, "close": 205.0, "volume": 1000},
            ),
            actions=(_split(ratio=2.0),),
        )
        result = engine.adjust_prices(req)
        assert result.prices[0].trade_date == date(2024, 5, 30)
        assert result.prices[0].close == 102.5

    def test_as_of_excludes_dividend(self):
        engine = AdjustmentEngine()
        req = AdjustmentRequest(
            symbol="RELIANCE", exchange="NSE",
            raw_prices=_raw_prices(), actions=(_dividend(amount=10.0),),
            as_of=date(2024, 5, 31),
        )
        result = engine.adjust_prices(req)
        pre = next(p for p in result.prices if p.trade_date == date(2024, 5, 30))
        assert pre.adjusted_close == 205.0

    def test_full_lifecycle_immutability(self):
        engine = AdjustmentEngine()
        raw = list(_raw_prices())
        original_close = raw[0]["close"]
        req = AdjustmentRequest(
            symbol="RELIANCE", exchange="NSE",
            raw_prices=tuple(raw), actions=(_split(ratio=2.0),),
        )
        engine.adjust_prices(req)
        assert raw[0]["close"] == original_close


# ---------------------------------------------------------------------------
# Repository persistence
# ---------------------------------------------------------------------------


class TestCorporateActionRepository:
    def test_store_and_get(self, repository):
        repository.store(_split())
        actions = repository.get_for_symbol("RELIANCE", "NSE")
        assert len(actions) == 1
        assert actions[0].action_type is ActionType.SPLIT
        assert actions[0].ratio == 2.0

    def test_store_batch(self, repository):
        batch = CorporateActionBatch(actions=(_split(), _dividend(), _bonus()))
        stored = repository.store_batch(batch)
        assert stored == 3
        actions = repository.get_for_symbol("RELIANCE", "NSE")
        assert len(actions) == 3

    def test_get_unknown_symbol(self, repository):
        assert repository.get_for_symbol("UNKNOWN", "NSE") == ()

    def test_duplicate_raises(self, repository):
        repository.store(_split())
        with pytest.raises(DuplicateActionError):
            repository.store(_split())

    def test_exists(self, repository):
        repository.store(_split())
        assert repository.exists("RELIANCE", ActionType.SPLIT, date(2024, 6, 1), "upstox") is True
        assert repository.exists("RELIANCE", ActionType.BONUS, date(2024, 6, 1), "upstox") is False

    def test_metadata_preserved(self, repository):
        repository.store(_rights())
        actions = repository.get_for_symbol("RELIANCE", "NSE")
        assert actions[0].metadata.get("issue_price") == 500.0

    def test_symbol_reuse(self, repository):
        repository.store(_split())
        repository.store(_dividend())
        with repository._conn.session() as session:
            count = session.query(Symbol).filter(Symbol.symbol == "RELIANCE").count()
            assert count == 1

    def test_orm_persisted(self, repository):
        repository.store(_bonus())
        with repository._conn.session() as session:
            rows = session.query(CorporateActionORM).all()
            assert len(rows) == 1
            assert rows[0].action_type == "bonus"

    def test_metadata_json_fallback(self, repository):
        from sqlalchemy import text

        repository.store(_split())
        # corrupt the stored json to verify graceful fallback
        with repository._conn.session() as session:
            session.execute(
                text("UPDATE corporate_actions SET metadata_json = 'NOT_JSON' WHERE id = 1")
            )
            session.commit()
        actions = repository.get_for_symbol("RELIANCE", "NSE")
        assert actions[0].metadata == {}
