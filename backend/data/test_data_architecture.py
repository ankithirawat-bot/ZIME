"""
Market Data Platform architecture tests.

Covers enums, models, provider ABC, registry, validation,
exceptions, DataEngine, determinism, and regression.
"""

from __future__ import annotations

from dataclasses import FrozenInstanceError
from datetime import UTC, date, datetime
from typing import Any

import pytest

from backend.data.data_engine import DataEngine
from backend.data.exceptions import (
    DataPlatformError,
    InvalidRequestError,
    UnsupportedDataTypeError,
    UnsupportedProviderError,
    ValidationError,
)
from backend.data.models import DataRequest, DataResponse, DataStatus, DataType, ValidationResult
from backend.data.provider import MarketDataProvider
from backend.data.provider_registry import ProviderRegistry
from backend.data.validation import validate_request, validate_response_data, validate_status

# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


class FakeProvider(MarketDataProvider):
    """Minimal concrete provider for testing."""

    def __init__(
        self,
        name: str = "fake",
        version: str = "1.0.0",
        supported: tuple[DataType, ...] = (DataType.PRICE_DAILY,),
        should_validate: bool = True,
        response_status: DataStatus = DataStatus.SUCCESS,
    ) -> None:
        self._name = name
        self._version = version
        self._supported = supported
        self._should_validate = should_validate
        self._response_status = response_status

    def supports(self, data_type: DataType) -> bool:
        return data_type in self._supported

    def fetch(self, request: DataRequest) -> DataResponse:
        return DataResponse(
            request=request,
            provider=self._name,
            timestamp=datetime.now(UTC),
            status=self._response_status,
            payload=({"close": 100.0, "volume": 1000},),
            metadata={"source": "fake"},
        )

    def validate(self, request: DataRequest) -> bool:
        return self._should_validate

    def provider_name(self) -> str:
        return self._name

    def version(self) -> str:
        return self._version


def _make_request(**overrides: Any) -> DataRequest:
    defaults = {
        "symbol": "RELIANCE",
        "exchange": "NSE",
        "data_type": DataType.PRICE_DAILY,
        "start_date": date(2024, 1, 1),
        "end_date": date(2024, 12, 31),
    }
    defaults.update(overrides)
    return DataRequest(**defaults)


# ---------------------------------------------------------------------------
# DataType enum
# ---------------------------------------------------------------------------


class TestDataType:
    def test_all_values_unique(self):
        values = [dt.value for dt in DataType]
        assert len(values) == len(set(values))

    def test_expected_types_exist(self):
        assert DataType.PRICE_DAILY == "price_daily"
        assert DataType.PRICE_INTRADAY == "price_intraday"
        assert DataType.CORPORATE_ACTIONS == "corporate_actions"
        assert DataType.FINANCIALS == "financials"
        assert DataType.RATIOS == "ratios"
        assert DataType.SHAREHOLDING == "shareholding"
        assert DataType.DIVIDENDS == "dividends"
        assert DataType.SPLITS == "splits"
        assert DataType.BONUS == "bonus"
        assert DataType.BUYBACKS == "buybacks"
        assert DataType.RIGHTS == "rights"
        assert DataType.EARNINGS == "earnings"
        assert DataType.NEWS == "news"
        assert DataType.BLOCK_DEALS == "block_deals"
        assert DataType.BULK_DEALS == "bulk_deals"
        assert DataType.INSIDER_TRADES == "insider_trades"

    def test_count(self):
        assert len(DataType) == 16

    def test_is_str_enum(self):
        assert isinstance(DataType.PRICE_DAILY, str)
        assert DataType.PRICE_DAILY == "price_daily"


# ---------------------------------------------------------------------------
# DataStatus enum
# ---------------------------------------------------------------------------


class TestDataStatus:
    def test_all_statuses(self):
        assert DataStatus.SUCCESS == "success"
        assert DataStatus.PARTIAL == "partial"
        assert DataStatus.FAILED == "failed"
        assert DataStatus.CACHED == "cached"

    def test_count(self):
        assert len(DataStatus) == 4


# ---------------------------------------------------------------------------
# DataRequest model
# ---------------------------------------------------------------------------


class TestDataRequest:
    def test_creation(self):
        r = _make_request()
        assert r.symbol == "RELIANCE"
        assert r.exchange == "NSE"
        assert r.data_type == DataType.PRICE_DAILY
        assert r.start_date == date(2024, 1, 1)
        assert r.end_date == date(2024, 12, 31)
        assert r.provider_preference is None

    def test_with_provider_preference(self):
        r = _make_request(provider_preference="yfinance")
        assert r.provider_preference == "yfinance"

    def test_frozen(self):
        r = _make_request()
        with pytest.raises(FrozenInstanceError):
            r.symbol = "TCS"  # type: ignore[misc]

    def test_equality(self):
        r1 = _make_request()
        r2 = _make_request()
        assert r1 == r2

    def test_inequality(self):
        r1 = _make_request()
        r2 = _make_request(symbol="TCS")
        assert r1 != r2


# ---------------------------------------------------------------------------
# ValidationResult model
# ---------------------------------------------------------------------------


class TestValidationResult:
    def test_valid_default(self):
        vr = ValidationResult(valid=True)
        assert vr.valid is True
        assert vr.errors == ()
        assert vr.warnings == ()
        assert vr.missing_fields == ()

    def test_invalid(self):
        vr = ValidationResult(
            valid=False,
            errors=("bad symbol",),
            warnings=("low volume",),
            missing_fields=("symbol",),
        )
        assert vr.valid is False
        assert vr.errors == ("bad symbol",)
        assert vr.warnings == ("low volume",)
        assert vr.missing_fields == ("symbol",)

    def test_frozen(self):
        vr = ValidationResult(valid=True)
        with pytest.raises(FrozenInstanceError):
            vr.valid = False  # type: ignore[misc]


# ---------------------------------------------------------------------------
# DataResponse model
# ---------------------------------------------------------------------------


class TestDataResponse:
    def test_creation(self):
        r = _make_request()
        now = datetime.now(UTC)
        resp = DataResponse(
            request=r,
            provider="fake",
            timestamp=now,
            status=DataStatus.SUCCESS,
            payload=({"close": 100.0},),
            metadata={"key": "val"},
            validation_result=ValidationResult(valid=True),
        )
        assert resp.request == r
        assert resp.provider == "fake"
        assert resp.status == DataStatus.SUCCESS
        assert len(resp.payload) == 1

    def test_defaults(self):
        r = _make_request()
        now = datetime.now(UTC)
        resp = DataResponse(
            request=r,
            provider="fake",
            timestamp=now,
            status=DataStatus.SUCCESS,
        )
        assert resp.payload == ()
        assert resp.metadata == {}
        assert resp.validation_result.valid is True

    def test_frozen(self):
        r = _make_request()
        now = datetime.now(UTC)
        resp = DataResponse(
            request=r, provider="fake", timestamp=now, status=DataStatus.SUCCESS
        )
        with pytest.raises(FrozenInstanceError):
            resp.status = DataStatus.FAILED  # type: ignore[misc]


# ---------------------------------------------------------------------------
# Exceptions
# ---------------------------------------------------------------------------


class TestExceptions:
    def test_base_exception(self):
        exc = DataPlatformError("test")
        assert str(exc) == "test"
        assert isinstance(exc, Exception)

    def test_unsupported_provider(self):
        exc = UnsupportedProviderError("nope")
        assert exc.provider == "nope"
        assert "nope" in str(exc)
        assert isinstance(exc, DataPlatformError)

    def test_unsupported_data_type(self):
        exc = UnsupportedDataTypeError("news", "yfinance")
        assert exc.data_type == "news"
        assert exc.provider == "yfinance"
        assert isinstance(exc, DataPlatformError)

    def test_invalid_request(self):
        exc = InvalidRequestError("bad request", fields=("symbol",))
        assert exc.fields == ("symbol",)
        assert isinstance(exc, DataPlatformError)

    def test_validation_error(self):
        exc = ValidationError("invalid", errors=("e1",), warnings=("w1",))
        assert exc.errors == ("e1",)
        assert exc.warnings == ("w1",)
        assert isinstance(exc, DataPlatformError)


# ---------------------------------------------------------------------------
# Provider ABC
# ---------------------------------------------------------------------------


class TestProviderABC:
    def test_cannot_instantiate_abc(self):
        with pytest.raises(TypeError):
            MarketDataProvider()  # type: ignore[abstract]

    def test_fake_provider_implements_interface(self):
        p = FakeProvider()
        assert isinstance(p, MarketDataProvider)
        assert p.provider_name() == "fake"
        assert p.version() == "1.0.0"
        assert p.supports(DataType.PRICE_DAILY) is True
        assert p.supports(DataType.FINANCIALS) is False

    def test_validate_delegates(self):
        p = FakeProvider(should_validate=False)
        r = _make_request()
        assert p.validate(r) is False

    def test_fetch_returns_response(self):
        p = FakeProvider()
        r = _make_request()
        resp = p.fetch(r)
        assert isinstance(resp, DataResponse)
        assert resp.status == DataStatus.SUCCESS


# ---------------------------------------------------------------------------
# ProviderRegistry
# ---------------------------------------------------------------------------


class TestProviderRegistry:
    def test_register_and_resolve(self):
        reg = ProviderRegistry()
        p = FakeProvider(name="yfinance")
        reg.register(p, (DataType.PRICE_DAILY, DataType.PRICE_INTRADAY))
        resolved = reg.resolve(DataType.PRICE_DAILY)
        assert resolved is p

    def test_resolve_by_name(self):
        reg = ProviderRegistry()
        p = FakeProvider(name="yfinance")
        reg.register(p, (DataType.PRICE_DAILY,))
        resolved = reg.resolve_by_name("yfinance")
        assert resolved is p

    def test_resolve_unregistered_type(self):
        reg = ProviderRegistry()
        with pytest.raises(UnsupportedDataTypeError):
            reg.resolve(DataType.FINANCIALS)

    def test_resolve_unregistered_provider(self):
        reg = ProviderRegistry()
        with pytest.raises(UnsupportedProviderError):
            reg.resolve_by_name("nonexistent")

    def test_supported_types(self):
        reg = ProviderRegistry()
        p = FakeProvider(name="yfinance")
        reg.register(p, (DataType.PRICE_DAILY, DataType.PRICE_INTRADAY))
        types = reg.supported_types("yfinance")
        assert DataType.PRICE_DAILY in types
        assert DataType.PRICE_INTRADAY in types

    def test_supported_types_unknown_provider(self):
        reg = ProviderRegistry()
        with pytest.raises(UnsupportedProviderError):
            reg.supported_types("unknown")

    def test_available_providers(self):
        reg = ProviderRegistry()
        p1 = FakeProvider(name="yfinance")
        p2 = FakeProvider(name="alpha")
        reg.register(p1, (DataType.PRICE_DAILY,))
        reg.register(p2, (DataType.FINANCIALS,))
        names = reg.available_providers()
        assert "yfinance" in names
        assert "alpha" in names

    def test_has_provider(self):
        reg = ProviderRegistry()
        p = FakeProvider(name="yfinance")
        reg.register(p, (DataType.PRICE_DAILY,))
        assert reg.has_provider("yfinance") is True
        assert reg.has_provider("nope") is False

    def test_has_type(self):
        reg = ProviderRegistry()
        p = FakeProvider(name="yfinance")
        reg.register(p, (DataType.PRICE_DAILY,))
        assert reg.has_type(DataType.PRICE_DAILY) is True
        assert reg.has_type(DataType.FINANCIALS) is False

    def test_multiple_providers_different_types(self):
        reg = ProviderRegistry()
        p1 = FakeProvider(name="yfinance")
        p2 = FakeProvider(name="alpha")
        reg.register(p1, (DataType.PRICE_DAILY,))
        reg.register(p2, (DataType.FINANCIALS,))
        assert reg.resolve(DataType.PRICE_DAILY) is p1
        assert reg.resolve(DataType.FINANCIALS) is p2


# ---------------------------------------------------------------------------
# Validation helpers
# ---------------------------------------------------------------------------


class TestValidateRequest:
    def test_valid_request(self):
        r = _make_request()
        vr = validate_request(r)
        assert vr.valid is True
        assert vr.errors == ()

    def test_empty_symbol(self):
        r = _make_request(symbol="")
        vr = validate_request(r)
        assert vr.valid is False
        assert any("Symbol" in e for e in vr.errors)
        assert "symbol" in vr.missing_fields

    def test_whitespace_symbol(self):
        r = _make_request(symbol="   ")
        vr = validate_request(r)
        assert vr.valid is False

    def test_empty_exchange(self):
        r = _make_request(exchange="")
        vr = validate_request(r)
        assert vr.valid is False
        assert any("Exchange" in e for e in vr.errors)
        assert "exchange" in vr.missing_fields

    def test_start_after_end(self):
        r = _make_request(start_date=date(2024, 12, 31), end_date=date(2024, 1, 1))
        vr = validate_request(r)
        assert vr.valid is False
        assert any("start_date" in e for e in vr.errors)

    def test_start_equals_end(self):
        r = _make_request(start_date=date(2024, 6, 15), end_date=date(2024, 6, 15))
        vr = validate_request(r)
        assert vr.valid is True


class TestValidateResponseData:
    def test_valid_data(self):
        payload = ({"close": 100.0, "volume": 1000},)
        vr = validate_response_data(payload, required_fields=("close", "volume"))
        assert vr.valid is True

    def test_empty_payload(self):
        vr = validate_response_data(())
        assert vr.valid is True
        assert len(vr.warnings) > 0

    def test_missing_required_field(self):
        payload = ({"close": 100.0},)
        vr = validate_response_data(payload, required_fields=("close", "volume"))
        assert vr.valid is False
        assert "volume" in vr.missing_fields

    def test_no_required_fields(self):
        payload = ({"close": 100.0},)
        vr = validate_response_data(payload)
        assert vr.valid is True


class TestValidateStatus:
    def test_success(self):
        assert validate_status(DataStatus.SUCCESS) is True

    def test_cached(self):
        assert validate_status(DataStatus.CACHED) is True

    def test_partial(self):
        assert validate_status(DataStatus.PARTIAL) is False

    def test_failed(self):
        assert validate_status(DataStatus.FAILED) is False


# ---------------------------------------------------------------------------
# DataEngine
# ---------------------------------------------------------------------------


class TestDataEngine:
    def test_successful_fetch(self):
        reg = ProviderRegistry()
        p = FakeProvider(name="yfinance")
        reg.register(p, (DataType.PRICE_DAILY,))
        engine = DataEngine(reg)
        req = _make_request()
        resp = engine.get_data(req)
        assert resp.status == DataStatus.SUCCESS
        assert resp.provider == "yfinance"
        assert len(resp.payload) == 1

    def test_invalid_request_raises(self):
        reg = ProviderRegistry()
        p = FakeProvider(name="yfinance")
        reg.register(p, (DataType.PRICE_DAILY,))
        engine = DataEngine(reg)
        req = _make_request(symbol="")
        with pytest.raises(InvalidRequestError) as exc_info:
            engine.get_data(req)
        assert "symbol" in exc_info.value.fields

    def test_provider_preference_overrides(self):
        reg = ProviderRegistry()
        p1 = FakeProvider(name="yfinance")
        p2 = FakeProvider(name="alpha")
        reg.register(p1, (DataType.PRICE_DAILY,))
        reg.register(p2, (DataType.PRICE_DAILY,))
        engine = DataEngine(reg)
        req = _make_request(provider_preference="alpha")
        resp = engine.get_data(req)
        assert resp.provider == "alpha"

    def test_provider_preference_fallback(self):
        reg = ProviderRegistry()
        p = FakeProvider(name="yfinance")
        reg.register(p, (DataType.PRICE_DAILY,))
        engine = DataEngine(reg)
        req = _make_request(provider_preference="nonexistent")
        resp = engine.get_data(req)
        assert resp.provider == "yfinance"

    def test_provider_rejection(self):
        reg = ProviderRegistry()
        p = FakeProvider(name="yfinance", should_validate=False)
        reg.register(p, (DataType.PRICE_DAILY,))
        engine = DataEngine(reg)
        req = _make_request()
        resp = engine.get_data(req)
        assert resp.status == DataStatus.FAILED

    def test_no_provider_for_type(self):
        reg = ProviderRegistry()
        engine = DataEngine(reg)
        req = _make_request()
        with pytest.raises(UnsupportedDataTypeError):
            engine.get_data(req)

    def test_engine_uses_registry(self):
        reg = ProviderRegistry()
        p = FakeProvider(name="test_provider")
        reg.register(p, (DataType.PRICE_DAILY,))
        engine = DataEngine(reg)
        req = _make_request()
        resp = engine.get_data(req)
        assert resp.request is req
        assert resp.provider == "test_provider"


# ---------------------------------------------------------------------------
# Determinism
# ---------------------------------------------------------------------------


class TestDeterminism:
    def test_request_equality(self):
        r1 = _make_request()
        r2 = _make_request()
        assert r1 == r2
        assert hash(r1) == hash(r2)

    def test_validation_result_equality(self):
        v1 = ValidationResult(valid=True, warnings=("w",))
        v2 = ValidationResult(valid=True, warnings=("w",))
        assert v1 == v2

    def test_validate_request_deterministic(self):
        r = _make_request()
        v1 = validate_request(r)
        v2 = validate_request(r)
        assert v1 == v2

    def test_validate_response_data_deterministic(self):
        payload = ({"close": 100.0},)
        v1 = validate_response_data(payload, ("close",))
        v2 = validate_response_data(payload, ("close",))
        assert v1 == v2

    def test_registry_deterministic(self):
        reg = ProviderRegistry()
        p = FakeProvider(name="yfinance")
        reg.register(p, (DataType.PRICE_DAILY,))
        r1 = reg.resolve(DataType.PRICE_DAILY)
        r2 = reg.resolve(DataType.PRICE_DAILY)
        assert r1 is r2


# ---------------------------------------------------------------------------
# Regression
# ---------------------------------------------------------------------------


class TestRegression:
    def test_full_workflow(self):
        reg = ProviderRegistry()
        p = FakeProvider(name="yfinance")
        reg.register(p, (DataType.PRICE_DAILY, DataType.FINANCIALS))
        engine = DataEngine(reg)

        req = _make_request(data_type=DataType.PRICE_DAILY)
        resp = engine.get_data(req)
        assert resp.status == DataStatus.SUCCESS
        assert resp.provider == "yfinance"
        assert resp.request.data_type == DataType.PRICE_DAILY

    def test_all_data_types_represented(self):
        for dt in DataType:
            assert dt.value
            assert isinstance(dt.value, str)

    def test_provider_version_accessible(self):
        p = FakeProvider(version="2.1.0")
        assert p.version() == "2.1.0"

    def test_empty_registry_no_providers(self):
        reg = ProviderRegistry()
        assert reg.available_providers() == ()

    def test_multiple_data_types_per_provider(self):
        reg = ProviderRegistry()
        types = (DataType.PRICE_DAILY, DataType.FINANCIALS, DataType.RATIOS)
        p = FakeProvider(name="comprehensive")
        reg.register(p, types)
        assert reg.supported_types("comprehensive") == types

    def test_validation_preserves_type_safety(self):
        r = _make_request()
        vr = validate_request(r)
        assert isinstance(vr.valid, bool)
        assert isinstance(vr.errors, tuple)
        assert isinstance(vr.warnings, tuple)
        assert isinstance(vr.missing_fields, tuple)
