"""
Market Data Platform architecture tests.

Covers enums, models, provider ABC, registry, validation,
exceptions, DataEngine, normalizer, schemas, adapters,
determinism, and regression.
"""

from __future__ import annotations

from dataclasses import FrozenInstanceError
from datetime import UTC, date, datetime
from typing import Any

import pytest

from backend.data.adapters import (
    CorporateActionAdapter,
    FinancialAdapter,
    NewsAdapter,
    PriceAdapter,
    ShareholdingAdapter,
)
from backend.data.data_engine import DataEngine
from backend.data.datasource import DataSource, NormalizedRecord
from backend.data.exceptions import (
    DataPlatformError,
    InvalidRequestError,
    UnsupportedDataTypeError,
    UnsupportedProviderError,
    ValidationError,
)
from backend.data.models import (
    DataRequest,
    DataResponse,
    DataStatus,
    DataType,
    NormalizedData,
    ProviderIdentity,
    ProviderType,
    RawDataResponse,
    ValidationResult,
)
from backend.data.normalizer import DataNormalizer
from backend.data.provider import MarketDataProvider
from backend.data.provider_registry import ProviderRegistry
from backend.data.schemas import (
    CorporateAction,
    DailyOHLCV,
    FinancialStatement,
    IntradayOHLCV,
    NewsRecord,
    ShareholdingRecord,
)
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
        provider_type_value: ProviderType = ProviderType.TEST,
    ) -> None:
        self._name = name
        self._version = version
        self._supported = supported
        self._should_validate = should_validate
        self._response_status = response_status
        self._provider_type = provider_type_value

    def supports(self, data_type: DataType) -> bool:
        return data_type in self._supported

    def fetch_raw(self, request: DataRequest) -> RawDataResponse:
        identity = ProviderIdentity(
            provider_type=self._provider_type,
            symbol=request.symbol,
            exchange=request.exchange,
            data_type=request.data_type,
        )
        return RawDataResponse(
            provider_type=identity,
            payload=({"close": 100.0, "volume": 1000},),
            metadata={"source": "fake"},
        )

    def validate(self, request: DataRequest) -> bool:
        return self._should_validate

    def provider_name(self) -> str:
        return self._name

    def provider_type(self) -> ProviderType:
        return self._provider_type

    def version(self) -> str:
        return self._version


class FakeDataSource(DataSource):
    """Minimal concrete DataSource for testing."""

    def __init__(self, source_name: str = "fake_source") -> None:
        self._source_name = source_name

    def source_name(self) -> str:
        return self._source_name

    def supported_types(self) -> tuple[DataType, ...]:
        return (DataType.PRICE_DAILY,)

    def normalize(self, response: RawDataResponse) -> tuple[NormalizedRecord, ...]:
        return tuple(
            DailyOHLCV(
                date=date(2024, 1, 1),
                open=99.0,
                high=101.0,
                low=98.0,
                close=r.get("close", 0.0),  # type: ignore[arg-type]
                adj_close=r.get("close", 0.0),  # type: ignore[arg-type]
                volume=r.get("volume", 0.0),  # type: ignore[arg-type]
            )
            for r in response.payload
        )

    def validate_schema(
        self,
        response: RawDataResponse,
    ) -> tuple[bool, tuple[str, ...]]:
        if not response.payload:
            return False, ("Empty payload",)
        return True, ()


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


def _make_raw_response(**overrides: Any) -> RawDataResponse:
    identity = ProviderIdentity(
        provider_type=overrides.pop("provider_type", ProviderType.TEST),
        symbol=overrides.pop("symbol", "RELIANCE"),
        exchange=overrides.pop("exchange", "NSE"),
        data_type=overrides.pop("data_type", DataType.PRICE_DAILY),
    )
    return RawDataResponse(
        provider_type=identity,
        payload=overrides.pop("payload", ({"close": 100.0, "volume": 1000},)),
        metadata=overrides.pop("metadata", {}),
    )


# ---------------------------------------------------------------------------
# ProviderType enum
# ---------------------------------------------------------------------------


class TestProviderType:
    def test_all_values_unique(self):
        values = [pt.value for pt in ProviderType]
        assert len(values) == len(set(values))

    def test_expected_types(self):
        assert ProviderType.NSE == "nse"
        assert ProviderType.BSE == "bse"
        assert ProviderType.NSE_INDEX == "nse_index"
        assert ProviderType.YAHOO == "yahoo"
        assert ProviderType.ALPHA_VANTAGE == "alpha_vantage"
        assert ProviderType.POLYGON == "polygon"
        assert ProviderType.TICKERTAPE == "tickertape"
        assert ProviderType.SCREENER == "screener"
        assert ProviderType.CSV == "csv"
        assert ProviderType.DATABASE == "database"
        assert ProviderType.TEST == "test"

    def test_count(self):
        assert len(ProviderType) == 12

    def test_is_str_enum(self):
        assert isinstance(ProviderType.NSE, str)
        assert ProviderType.NSE == "nse"


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
# ProviderIdentity model
# ---------------------------------------------------------------------------


class TestProviderIdentity:
    def test_creation(self):
        pi = ProviderIdentity(
            provider_type=ProviderType.NSE,
            symbol="RELIANCE",
            exchange="NSE",
            data_type=DataType.PRICE_DAILY,
        )
        assert pi.provider_type == ProviderType.NSE
        assert pi.symbol == "RELIANCE"
        assert pi.exchange == "NSE"
        assert pi.data_type == DataType.PRICE_DAILY

    def test_frozen(self):
        pi = ProviderIdentity(
            provider_type=ProviderType.NSE,
            symbol="RELIANCE",
            exchange="NSE",
            data_type=DataType.PRICE_DAILY,
        )
        with pytest.raises(FrozenInstanceError):
            pi.symbol = "TCS"  # type: ignore[misc]

    def test_equality(self):
        pi1 = ProviderIdentity(
            provider_type=ProviderType.NSE,
            symbol="RELIANCE",
            exchange="NSE",
            data_type=DataType.PRICE_DAILY,
        )
        pi2 = ProviderIdentity(
            provider_type=ProviderType.NSE,
            symbol="RELIANCE",
            exchange="NSE",
            data_type=DataType.PRICE_DAILY,
        )
        assert pi1 == pi2


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
# RawDataResponse model
# ---------------------------------------------------------------------------


class TestRawDataResponse:
    def test_creation(self):
        rr = _make_raw_response()
        assert rr.provider_type.provider_type == ProviderType.TEST
        assert rr.provider_type.symbol == "RELIANCE"
        assert len(rr.payload) == 1
        assert rr.metadata == {}

    def test_with_metadata(self):
        rr = _make_raw_response(metadata={"key": "val"})
        assert rr.metadata == {"key": "val"}

    def test_frozen(self):
        rr = _make_raw_response()
        with pytest.raises(FrozenInstanceError):
            rr.payload = ()  # type: ignore[misc]

    def test_empty_payload(self):
        rr = _make_raw_response(payload=())
        assert rr.payload == ()


# ---------------------------------------------------------------------------
# NormalizedData model
# ---------------------------------------------------------------------------


class TestNormalizedData:
    def test_creation(self):
        nd = NormalizedData(
            symbol="RELIANCE",
            exchange="NSE",
            data_type=DataType.PRICE_DAILY,
            records=(DailyOHLCV(
                date=date(2024, 1, 1),
                open=99.0,
                high=101.0,
                low=98.0,
                close=100.0,
                adj_close=100.0,
                volume=1000.0,
            ),),
            metadata={"source": "test"},
        )
        assert nd.symbol == "RELIANCE"
        assert nd.exchange == "NSE"
        assert nd.data_type == DataType.PRICE_DAILY
        assert len(nd.records) == 1
        assert nd.metadata == {"source": "test"}

    def test_defaults(self):
        nd = NormalizedData(
            symbol="RELIANCE",
            exchange="NSE",
            data_type=DataType.PRICE_DAILY,
        )
        assert nd.records == ()
        assert nd.metadata == {}

    def test_frozen(self):
        nd = NormalizedData(
            symbol="RELIANCE",
            exchange="NSE",
            data_type=DataType.PRICE_DAILY,
        )
        with pytest.raises(FrozenInstanceError):
            nd.symbol = "TCS"  # type: ignore[misc]


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
# Schemas
# ---------------------------------------------------------------------------


class TestSchemas:
    def test_daily_ohlcv(self):
        bar = DailyOHLCV(
            date=date(2024, 1, 15),
            open=100.0,
            high=105.0,
            low=99.0,
            close=103.0,
            adj_close=103.0,
            volume=50000.0,
        )
        assert bar.open == 100.0
        assert bar.close == 103.0
        assert bar.volume == 50000.0

    def test_daily_ohlcv_frozen(self):
        bar = DailyOHLCV(
            date=date(2024, 1, 15),
            open=100.0,
            high=105.0,
            low=99.0,
            close=103.0,
            adj_close=103.0,
            volume=50000.0,
        )
        with pytest.raises(FrozenInstanceError):
            bar.close = 200.0  # type: ignore[misc]

    def test_intraday_ohlcv(self):
        bar = IntradayOHLCV(
            datetime=datetime(2024, 1, 15, 10, 30, tzinfo=UTC),
            open=100.0,
            high=102.0,
            low=99.5,
            close=101.0,
            volume=5000.0,
        )
        assert bar.close == 101.0

    def test_financial_statement(self):
        fs = FinancialStatement(
            symbol="RELIANCE",
            report_date=date(2024, 3, 31),
            period="Q4 FY24",
            revenue=200000.0,
            net_profit=15000.0,
            eps=22.0,
        )
        assert fs.revenue == 200000.0
        assert fs.period == "Q4 FY24"
        assert fs.total_assets is None

    def test_corporate_action(self):
        ca = CorporateAction(
            symbol="RELIANCE",
            action_type="dividend",
            ex_date=date(2024, 6, 15),
            value=8.0,
        )
        assert ca.action_type == "dividend"
        assert ca.value == 8.0

    def test_news_record(self):
        nr = NewsRecord(
            symbol="RELIANCE",
            headline="Reliance reports record profits",
            source="Economic Times",
        )
        assert nr.headline == "Reliance reports record profits"
        assert nr.sentiment is None

    def test_shareholding_record(self):
        sr = ShareholdingRecord(
            symbol="RELIANCE",
            report_date=date(2024, 3, 31),
            category="promoter",
            shares_held=500000000.0,
            percentage=50.2,
        )
        assert sr.category == "promoter"
        assert sr.percentage == 50.2


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
        assert p.provider_type() == ProviderType.TEST
        assert p.supports(DataType.PRICE_DAILY) is True
        assert p.supports(DataType.FINANCIALS) is False

    def test_validate_delegates(self):
        p = FakeProvider(should_validate=False)
        r = _make_request()
        assert p.validate(r) is False

    def test_fetch_raw_returns_raw_response(self):
        p = FakeProvider()
        r = _make_request()
        raw = p.fetch_raw(r)
        assert isinstance(raw, RawDataResponse)
        assert raw.provider_type.provider_type == ProviderType.TEST
        assert len(raw.payload) == 1


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

    def test_resolve_by_provider_type(self):
        reg = ProviderRegistry()
        p = FakeProvider(name="yfinance", provider_type_value=ProviderType.YAHOO)
        reg.register(p, (DataType.PRICE_DAILY,))
        resolved = reg.resolve_by_provider_type(ProviderType.YAHOO)
        assert resolved is p

    def test_resolve_unregistered_type(self):
        reg = ProviderRegistry()
        with pytest.raises(UnsupportedDataTypeError):
            reg.resolve(DataType.FINANCIALS)

    def test_resolve_unregistered_provider(self):
        reg = ProviderRegistry()
        with pytest.raises(UnsupportedProviderError):
            reg.resolve_by_name("nonexistent")

    def test_resolve_unregistered_provider_type(self):
        reg = ProviderRegistry()
        with pytest.raises(UnsupportedProviderError):
            reg.resolve_by_provider_type(ProviderType.NSE)

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
# DataSource ABC
# ---------------------------------------------------------------------------


class TestDataSourceABC:
    def test_cannot_instantiate_abc(self):
        with pytest.raises(TypeError):
            DataSource()  # type: ignore[abstract]

    def test_fake_source_implements_interface(self):
        ds = FakeDataSource()
        assert isinstance(ds, DataSource)
        assert ds.source_name() == "fake_source"
        assert DataType.PRICE_DAILY in ds.supported_types()

    def test_normalize_returns_records(self):
        ds = FakeDataSource()
        rr = _make_raw_response()
        records = ds.normalize(rr)
        assert len(records) == 1
        assert isinstance(records[0], DailyOHLCV)

    def test_validate_schema_valid(self):
        ds = FakeDataSource()
        rr = _make_raw_response()
        valid, errors = ds.validate_schema(rr)
        assert valid is True
        assert errors == ()

    def test_validate_schema_empty_payload(self):
        ds = FakeDataSource()
        rr = _make_raw_response(payload=())
        valid, errors = ds.validate_schema(rr)
        assert valid is False
        assert len(errors) > 0


# ---------------------------------------------------------------------------
# DataNormalizer
# ---------------------------------------------------------------------------


class TestDataNormalizer:
    def test_register_and_normalize(self):
        norm = DataNormalizer()
        ds = FakeDataSource()
        norm.register(ds, (DataType.PRICE_DAILY,))
        rr = _make_raw_response()
        nd = norm.normalize(rr)
        assert nd.symbol == "RELIANCE"
        assert nd.exchange == "NSE"
        assert nd.data_type == DataType.PRICE_DAILY
        assert len(nd.records) == 1

    def test_unregistered_type_raises(self):
        norm = DataNormalizer()
        rr = _make_raw_response()
        with pytest.raises(UnsupportedDataTypeError):
            norm.normalize(rr)

    def test_has_source(self):
        norm = DataNormalizer()
        ds = FakeDataSource()
        norm.register(ds, (DataType.PRICE_DAILY,))
        assert norm.has_source(DataType.PRICE_DAILY) is True
        assert norm.has_source(DataType.FINANCIALS) is False

    def test_registered_types(self):
        norm = DataNormalizer()
        ds = FakeDataSource()
        norm.register(ds, (DataType.PRICE_DAILY, DataType.FINANCIALS))
        types = norm.registered_types()
        assert DataType.PRICE_DAILY in types
        assert DataType.FINANCIALS in types


# ---------------------------------------------------------------------------
# Adapters ABC
# ---------------------------------------------------------------------------


class TestAdaptersABC:
    def test_price_adapter_cannot_instantiate(self):
        with pytest.raises(TypeError):
            PriceAdapter()  # type: ignore[abstract]

    def test_financial_adapter_cannot_instantiate(self):
        with pytest.raises(TypeError):
            FinancialAdapter()  # type: ignore[abstract]

    def test_news_adapter_cannot_instantiate(self):
        with pytest.raises(TypeError):
            NewsAdapter()  # type: ignore[abstract]

    def test_shareholding_adapter_cannot_instantiate(self):
        with pytest.raises(TypeError):
            ShareholdingAdapter()  # type: ignore[abstract]

    def test_corporate_action_adapter_cannot_instantiate(self):
        with pytest.raises(TypeError):
            CorporateActionAdapter()  # type: ignore[abstract]


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
        norm = DataNormalizer()
        ds = FakeDataSource()
        norm.register(ds, (DataType.PRICE_DAILY,))
        engine = DataEngine(reg, norm)
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
        norm = DataNormalizer()
        ds = FakeDataSource()
        norm.register(ds, (DataType.PRICE_DAILY,))
        engine = DataEngine(reg, norm)
        req = _make_request(provider_preference="alpha")
        resp = engine.get_data(req)
        assert resp.provider == "alpha"

    def test_provider_preference_fallback(self):
        reg = ProviderRegistry()
        p = FakeProvider(name="yfinance")
        reg.register(p, (DataType.PRICE_DAILY,))
        norm = DataNormalizer()
        ds = FakeDataSource()
        norm.register(ds, (DataType.PRICE_DAILY,))
        engine = DataEngine(reg, norm)
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
        norm = DataNormalizer()
        ds = FakeDataSource()
        norm.register(ds, (DataType.PRICE_DAILY,))
        engine = DataEngine(reg, norm)
        req = _make_request()
        resp = engine.get_data(req)
        assert resp.request is req
        assert resp.provider == "test_provider"

    def test_engine_default_normalizer(self):
        reg = ProviderRegistry()
        p = FakeProvider(name="yfinance")
        reg.register(p, (DataType.PRICE_DAILY,))
        engine = DataEngine(reg)
        assert engine._normalizer is not None


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

    def test_raw_response_equality(self):
        rr1 = _make_raw_response()
        rr2 = _make_raw_response()
        assert rr1 == rr2

    def test_normalized_data_equality(self):
        nd1 = NormalizedData(symbol="X", exchange="NSE", data_type=DataType.PRICE_DAILY)
        nd2 = NormalizedData(symbol="X", exchange="NSE", data_type=DataType.PRICE_DAILY)
        assert nd1 == nd2


# ---------------------------------------------------------------------------
# Regression
# ---------------------------------------------------------------------------


class TestRegression:
    def test_full_workflow(self):
        reg = ProviderRegistry()
        p = FakeProvider(name="yfinance")
        reg.register(p, (DataType.PRICE_DAILY, DataType.FINANCIALS))
        norm = DataNormalizer()
        ds = FakeDataSource()
        norm.register(ds, (DataType.PRICE_DAILY,))
        engine = DataEngine(reg, norm)

        req = _make_request(data_type=DataType.PRICE_DAILY)
        resp = engine.get_data(req)
        assert resp.status == DataStatus.SUCCESS
        assert resp.provider == "yfinance"
        assert resp.request.data_type == DataType.PRICE_DAILY

    def test_all_data_types_represented(self):
        for dt in DataType:
            assert dt.value
            assert isinstance(dt.value, str)

    def test_all_provider_types_represented(self):
        for pt in ProviderType:
            assert pt.value
            assert isinstance(pt.value, str)

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

    def test_provider_type_drives_normalization(self):
        reg = ProviderRegistry()
        p = FakeProvider(
            name="nse_provider",
            provider_type_value=ProviderType.NSE,
        )
        reg.register(p, (DataType.PRICE_DAILY,))
        norm = DataNormalizer()
        ds = FakeDataSource()
        norm.register(ds, (DataType.PRICE_DAILY,))
        engine = DataEngine(reg, norm)
        req = _make_request()
        resp = engine.get_data(req)
        assert resp.status == DataStatus.SUCCESS

    def test_raw_to_normalized_to_response_roundtrip(self):
        reg = ProviderRegistry()
        p = FakeProvider(name="test_roundtrip")
        reg.register(p, (DataType.PRICE_DAILY,))
        norm = DataNormalizer()
        ds = FakeDataSource()
        norm.register(ds, (DataType.PRICE_DAILY,))
        engine = DataEngine(reg, norm)
        req = _make_request()
        resp = engine.get_data(req)
        assert "close" in resp.payload[0]
        assert resp.payload[0]["close"] == 100.0
