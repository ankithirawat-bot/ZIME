"""
Upstox provider tests.

Covers symbol mapping, historical fetch, empty response,
invalid symbol, rate-limit handling, normalization,
validation, and provider metadata.
"""

from __future__ import annotations

from datetime import date

import pytest

from backend.data.models import (
    DataRequest,
    DataType,
    ProviderType,
    RawDataResponse,
)
from backend.data.providers.instrument_mapper import InstrumentMapper
from backend.data.providers.upstox_client import UpstoxCandle, UpstoxCandlesResponse, UpstoxClient
from backend.data.providers.upstox_provider import UpstoxProvider

# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


def _make_request(**overrides) -> DataRequest:
    defaults = {
        "symbol": "RELIANCE",
        "exchange": "NSE",
        "data_type": DataType.PRICE_DAILY,
        "start_date": date(2024, 1, 1),
        "end_date": date(2024, 12, 31),
    }
    defaults.update(overrides)
    return DataRequest(**defaults)


def _fake_candle(ts: str = "2024-06-15T00:00:00+05:30") -> UpstoxCandle:
    return UpstoxCandle(
        timestamp=ts,
        open=100.0,
        high=105.0,
        low=99.0,
        close=103.0,
        volume=50000.0,
        open_interest=0.0,
    )


class AuthenticatedClient(UpstoxClient):
    """Client that is always authenticated for testing."""

    def __init__(self) -> None:
        super().__init__(api_key="test_key", access_token="test_token")

    def get_historical_candles(self, instrument_key, interval, from_date, to_date):
        return UpstoxCandlesResponse(
            status="success",
            candles=(_fake_candle(),),
        )


class EmptyClient(UpstoxClient):
    """Client that returns empty candles."""

    def __init__(self) -> None:
        super().__init__(api_key="test_key", access_token="test_token")

    def get_historical_candles(self, instrument_key, interval, from_date, to_date):
        return UpstoxCandlesResponse(status="success", candles=())


class ErrorClient(UpstoxClient):
    """Client that returns an error."""

    def __init__(self) -> None:
        super().__init__(api_key="test_key", access_token="test_token")

    def get_historical_candles(self, instrument_key, interval, from_date, to_date):
        return UpstoxCandlesResponse(
            status="error",
            message="Rate limit exceeded",
            error_code="RATE_LIMIT",
        )


class MultiCandleClient(UpstoxClient):
    """Client that returns multiple candles."""

    def __init__(self) -> None:
        super().__init__(api_key="test_key", access_token="test_token")

    def get_historical_candles(self, instrument_key, interval, from_date, to_date):
        return UpstoxCandlesResponse(
            status="success",
            candles=(
                UpstoxCandle(timestamp="2024-01-15T00:00:00+05:30", open=100.0, high=105.0, low=99.0, close=103.0, volume=50000.0),
                UpstoxCandle(timestamp="2024-01-16T00:00:00+05:30", open=103.0, high=108.0, low=102.0, close=107.0, volume=60000.0),
                UpstoxCandle(timestamp="2024-01-17T00:00:00+05:30", open=107.0, high=110.0, low=106.0, close=109.0, volume=45000.0),
            ),
        )


# ---------------------------------------------------------------------------
# UpstoxCandle model
# ---------------------------------------------------------------------------


class TestUpstoxCandle:
    def test_creation(self):
        c = _fake_candle()
        assert c.open == 100.0
        assert c.high == 105.0
        assert c.low == 99.0
        assert c.close == 103.0
        assert c.volume == 50000.0
        assert c.open_interest == 0.0

    def test_with_open_interest(self):
        c = UpstoxCandle(
            timestamp="2024-01-15T00:00:00+05:30",
            open=100.0, high=105.0, low=99.0, close=103.0,
            volume=50000.0, open_interest=1000.0,
        )
        assert c.open_interest == 1000.0

    def test_frozen(self):
        c = _fake_candle()
        with pytest.raises(AttributeError):
            c.close = 200.0  # type: ignore[misc]


# ---------------------------------------------------------------------------
# UpstoxCandlesResponse model
# ---------------------------------------------------------------------------


class TestUpstoxCandlesResponse:
    def test_success(self):
        r = UpstoxCandlesResponse(status="success", candles=(_fake_candle(),))
        assert r.status == "success"
        assert len(r.candles) == 1
        assert r.message == ""
        assert r.error_code == ""

    def test_error(self):
        r = UpstoxCandlesResponse(status="error", message="fail", error_code="E001")
        assert r.status == "error"
        assert r.message == "fail"
        assert r.error_code == "E001"
        assert r.candles == ()

    def test_frozen(self):
        r = UpstoxCandlesResponse(status="success")
        with pytest.raises(AttributeError):
            r.status = "error"  # type: ignore[misc]


# ---------------------------------------------------------------------------
# UpstoxInstrumentResponse model
# ---------------------------------------------------------------------------


class TestUpstoxInstrumentResponse:
    def test_creation(self):
        from backend.data.providers.upstox_client import UpstoxInstrumentResponse
        ir = UpstoxInstrumentResponse(
            instrument_token="1234",
            symbol="RELIANCE",
            exchange="NSE_EQ",
            instrument_type="EQ",
            name="Reliance Industries",
        )
        assert ir.instrument_token == "1234"
        assert ir.symbol == "RELIANCE"
        assert ir.name == "Reliance Industries"


# ---------------------------------------------------------------------------
# UpstoxClient
# ---------------------------------------------------------------------------


class TestUpstoxClient:
    def test_not_authenticated(self):
        client = UpstoxClient()
        assert client.is_authenticated is False

    def test_authenticated(self):
        client = UpstoxClient(api_key="key", access_token="token")
        assert client.is_authenticated is True

    def test_unauthenticated_fetch(self):
        client = UpstoxClient()
        r = client.get_historical_candles("RELIANCE", "1d", date(2024, 1, 1), date(2024, 12, 31))
        assert r.status == "error"
        assert r.error_code == "AUTH_ERROR"

    def test_authenticated_fetch(self):
        client = AuthenticatedClient()
        r = client.get_historical_candles("RELIANCE", "1d", date(2024, 1, 1), date(2024, 12, 31))
        assert r.status == "success"
        assert len(r.candles) == 1

    def test_get_instrument_default(self):
        client = UpstoxClient()
        r = client.get_instrument("RELIANCE", "NSE_EQ")
        assert r is None

    def test_search_instruments_default(self):
        client = UpstoxClient()
        r = client.search_instruments("RELIANCE")
        assert r == ()


# ---------------------------------------------------------------------------
# InstrumentMapper
# ---------------------------------------------------------------------------


class TestInstrumentMapper:
    def test_resolve_known(self):
        mapper = InstrumentMapper()
        assert mapper.resolve("RELIANCE") == "RELIANCE"
        assert mapper.resolve("reliance") == "RELIANCE"
        assert mapper.resolve("TCS") == "TCS"
        assert mapper.resolve("INFY") == "INFY"
        assert mapper.resolve("infosys") == "INFY"

    def test_resolve_unknown(self):
        mapper = InstrumentMapper()
        assert mapper.resolve("UNKNOWNXYZ") is None

    def test_exchange_segment(self):
        mapper = InstrumentMapper()
        assert mapper.exchange_segment("NSE") == "NSE_EQ"
        assert mapper.exchange_segment("BSE") == "BSE_EQ"
        assert mapper.exchange_segment("nse") == "NSE_EQ"
        assert mapper.exchange_segment("UNKNOWN") == "NSE_EQ"

    def test_has_symbol(self):
        mapper = InstrumentMapper()
        assert mapper.has_symbol("RELIANCE") is True
        assert mapper.has_symbol("reliance") is True
        assert mapper.has_symbol("UNKNOWN") is False

    def test_supported_symbols(self):
        mapper = InstrumentMapper()
        symbols = mapper.supported_symbols()
        assert "RELIANCE" in symbols
        assert "TCS" in symbols
        assert len(symbols) > 10


# ---------------------------------------------------------------------------
# UpstoxProvider
# ---------------------------------------------------------------------------


class TestUpstoxProvider:
    def test_provider_metadata(self):
        p = UpstoxProvider()
        assert p.provider_name() == "upstox"
        assert p.provider_type() == ProviderType.UPSTOX
        assert p.version() == "1.0.0"

    def test_supports_price_daily(self):
        p = UpstoxProvider()
        assert p.supports(DataType.PRICE_DAILY) is True

    def test_does_not_support_intraday(self):
        p = UpstoxProvider()
        assert p.supports(DataType.PRICE_INTRADAY) is False

    def test_does_not_support_financials(self):
        p = UpstoxProvider()
        assert p.supports(DataType.FINANCIALS) is False

    def test_validate_valid(self):
        p = UpstoxProvider()
        req = _make_request()
        assert p.validate(req) is True

    def test_validate_wrong_data_type(self):
        p = UpstoxProvider()
        req = _make_request(data_type=DataType.FINANCIALS)
        assert p.validate(req) is False

    def test_validate_unknown_symbol(self):
        p = UpstoxProvider()
        req = _make_request(symbol="UNKNOWNXYZ")
        assert p.validate(req) is False

    def test_validate_unsupported_exchange(self):
        p = UpstoxProvider()
        req = _make_request(exchange="LSE")
        assert p.validate(req) is False

    def test_fetch_raw_success(self):
        client = AuthenticatedClient()
        p = UpstoxProvider(client=client)
        req = _make_request()
        raw = p.fetch_raw(req)
        assert isinstance(raw, RawDataResponse)
        assert raw.provider_type.provider_type == ProviderType.UPSTOX
        assert raw.provider_type.symbol == "RELIANCE"
        assert len(raw.payload) == 1
        assert raw.payload[0]["close"] == 103.0
        assert raw.metadata["instrument_key"] == "RELIANCE"
        assert raw.metadata["interval"] == "1d"

    def test_fetch_raw_unknown_symbol(self):
        client = AuthenticatedClient()
        p = UpstoxProvider(client=client)
        req = _make_request(symbol="UNKNOWNXYZ")
        raw = p.fetch_raw(req)
        assert len(raw.payload) == 0
        assert "error" in raw.metadata

    def test_fetch_raw_empty_response(self):
        client = EmptyClient()
        p = UpstoxProvider(client=client)
        req = _make_request()
        raw = p.fetch_raw(req)
        assert len(raw.payload) == 0
        assert raw.provider_type.provider_type == ProviderType.UPSTOX

    def test_fetch_raw_error_response(self):
        client = ErrorClient()
        p = UpstoxProvider(client=client)
        req = _make_request()
        raw = p.fetch_raw(req)
        assert len(raw.payload) == 0
        assert raw.metadata["error"] == "Rate limit exceeded"
        assert raw.metadata["error_code"] == "RATE_LIMIT"

    def test_fetch_raw_multiple_candles(self):
        client = MultiCandleClient()
        p = UpstoxProvider(client=client)
        req = _make_request()
        raw = p.fetch_raw(req)
        assert len(raw.payload) == 3
        assert raw.payload[0]["close"] == 103.0
        assert raw.payload[1]["close"] == 107.0
        assert raw.payload[2]["close"] == 109.0

    def test_fetch_raw_metadata_fields(self):
        client = AuthenticatedClient()
        p = UpstoxProvider(client=client)
        req = _make_request()
        raw = p.fetch_raw(req)
        assert raw.metadata["instrument_key"] == "RELIANCE"
        assert raw.metadata["exchange_segment"] == "NSE_EQ"
        assert raw.metadata["interval"] == "1d"

    def test_fetch_raw_candle_fields(self):
        client = AuthenticatedClient()
        p = UpstoxProvider(client=client)
        req = _make_request()
        raw = p.fetch_raw(req)
        candle = raw.payload[0]
        assert "timestamp" in candle
        assert "open" in candle
        assert "high" in candle
        assert "low" in candle
        assert "close" in candle
        assert "volume" in candle
        assert "open_interest" in candle

    def test_provider_type_upstox(self):
        assert ProviderType.UPSTOX == "upstox"


# ---------------------------------------------------------------------------
# Integration with DataEngine
# ---------------------------------------------------------------------------


class TestUpstoxIntegration:
    def test_register_with_provider_registry(self):
        from backend.data.provider_registry import ProviderRegistry
        reg = ProviderRegistry()
        p = UpstoxProvider()
        reg.register(p, (DataType.PRICE_DAILY,))
        assert reg.has_type(DataType.PRICE_DAILY) is True
        assert reg.has_provider("upstox") is True

    def test_resolve_through_registry(self):
        from backend.data.provider_registry import ProviderRegistry
        reg = ProviderRegistry()
        p = UpstoxProvider()
        reg.register(p, (DataType.PRICE_DAILY,))
        resolved = reg.resolve(DataType.PRICE_DAILY)
        assert resolved is p

    def test_engine_end_to_end(self):
        from backend.data.data_engine import DataEngine
        from backend.data.datasource import DataSource
        from backend.data.normalizer import DataNormalizer
        from backend.data.provider_registry import ProviderRegistry
        from backend.data.schemas import DailyOHLCV

        class PriceDataSource(DataSource):
            def source_name(self):
                return "upstox_price"

            def supported_types(self):
                return (DataType.PRICE_DAILY,)

            def normalize(self, response):
                return tuple(
                    DailyOHLCV(
                        date=date(2024, 1, 15),
                        open=r.get("open", 0.0),  # type: ignore[arg-type]
                        high=r.get("high", 0.0),  # type: ignore[arg-type]
                        low=r.get("low", 0.0),  # type: ignore[arg-type]
                        close=r.get("close", 0.0),  # type: ignore[arg-type]
                        adj_close=r.get("close", 0.0),  # type: ignore[arg-type]
                        volume=r.get("volume", 0.0),  # type: ignore[arg-type]
                    )
                    for r in response.payload
                )

            def validate_schema(self, response):
                return True, ()

        reg = ProviderRegistry()
        client = AuthenticatedClient()
        p = UpstoxProvider(client=client)
        reg.register(p, (DataType.PRICE_DAILY,))

        norm = DataNormalizer()
        ds = PriceDataSource()
        norm.register(ds, (DataType.PRICE_DAILY,))

        engine = DataEngine(reg, norm)
        req = _make_request()
        resp = engine.get_data(req)
        assert resp.status.value == "success"
        assert resp.provider == "upstox"
        assert len(resp.payload) == 1


# ---------------------------------------------------------------------------
# Regression
# ---------------------------------------------------------------------------


class TestRegression:
    def test_all_provider_types_includes_upstox(self):
        assert ProviderType.UPSTOX == "upstox"
        assert len(ProviderType) > 10

    def test_mapper_has_all_expected_symbols(self):
        mapper = InstrumentMapper()
        for sym in ["RELIANCE", "TCS", "INFY", "HDFCBANK", "ICICIBANK", "SBIN"]:
            assert mapper.has_symbol(sym) is True
            assert mapper.resolve(sym) is not None
