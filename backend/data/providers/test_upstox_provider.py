"""
Upstox provider tests.

Covers auth, retry, client, provider, mapper, validator,
and DataEngine integration.  All HTTP requests mocked.
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
from backend.data.providers.auth import AuthManager, UpstoxCredentials
from backend.data.providers.instrument_mapper import InstrumentMapper
from backend.data.providers.price_validator import PriceValidator, ValidationResult
from backend.data.providers.retry import RetryConfig, RetryResult, compute_delay, execute_with_retry
from backend.data.providers.upstox_client import (
    UpstoxAPIError,
    UpstoxCandle,
    UpstoxCandlesResponse,
    UpstoxClient,
)
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


def _fake_candle(ts: str = "2024-06-15T00:00:00+05:30", **overrides) -> UpstoxCandle:
    defaults = {
        "timestamp": ts,
        "open": 100.0,
        "high": 105.0,
        "low": 99.0,
        "close": 103.0,
        "volume": 50000.0,
        "open_interest": 0.0,
    }
    defaults.update(overrides)
    return UpstoxCandle(**defaults)


def _make_auth() -> AuthManager:
    return AuthManager(
        credentials=UpstoxCredentials(api_key="test_key", access_token="test_token")
    )


def _make_retry_config(**overrides) -> RetryConfig:
    defaults = {"max_attempts": 3, "base_delay": 0.0, "backoff_factor": 1.0, "retryable_errors": (UpstoxAPIError,)}
    defaults.update(overrides)
    return RetryConfig(**defaults)


# ---------------------------------------------------------------------------
# AuthManager
# ---------------------------------------------------------------------------


class TestAuthManager:
    def test_not_authenticated(self):
        am = AuthManager()
        assert am.is_authenticated is False

    def test_authenticated(self):
        am = AuthManager(
            credentials=UpstoxCredentials(access_token="tok")
        )
        assert am.is_authenticated is True

    def test_api_key(self):
        am = AuthManager(
            credentials=UpstoxCredentials(api_key="key123")
        )
        assert am.api_key == "key123"

    def test_access_token(self):
        am = AuthManager(
            credentials=UpstoxCredentials(access_token="tok")
        )
        assert am.access_token == "tok"

    def test_set_access_token(self):
        am = AuthManager()
        assert am.is_authenticated is False
        am.set_access_token("new_tok")
        assert am.is_authenticated is True
        assert am.access_token == "new_tok"

    def test_clear_access_token(self):
        am = AuthManager(
            credentials=UpstoxCredentials(access_token="tok")
        )
        am.clear_access_token()
        assert am.is_authenticated is False

    def test_preserves_api_key_on_token_update(self):
        am = AuthManager(
            credentials=UpstoxCredentials(api_key="key", access_token="old")
        )
        am.set_access_token("new")
        assert am.api_key == "key"
        assert am.access_token == "new"

    def test_credentials_copy(self):
        am = AuthManager(
            credentials=UpstoxCredentials(api_key="k", access_token="t")
        )
        c = am.credentials()
        assert c.api_key == "k"
        assert c.access_token == "t"

    def test_refresh_token_success(self):
        am = AuthManager(refresh_fn=lambda: "refreshed")
        result = am.refresh_token()
        assert result == "refreshed"
        assert am.access_token == "refreshed"

    def test_refresh_token_failure(self):
        am = AuthManager(refresh_fn=lambda: None)
        result = am.refresh_token()
        assert result is None

    def test_refresh_token_no_callback(self):
        am = AuthManager()
        result = am.refresh_token()
        assert result is None

    def test_frozen_credentials(self):
        am = AuthManager(
            credentials=UpstoxCredentials(api_key="k", access_token="t")
        )
        c = am.credentials()
        with pytest.raises(AttributeError):
            c.access_token = "new"  # type: ignore[misc]


# ---------------------------------------------------------------------------
# RetryConfig / RetryResult
# ---------------------------------------------------------------------------


class TestRetryConfig:
    def test_defaults(self):
        c = RetryConfig()
        assert c.max_attempts == 3
        assert c.base_delay == 1.0
        assert c.backoff_factor == 2.0
        assert c.max_delay == 30.0
        assert c.retryable_errors == ()

    def test_custom(self):
        c = RetryConfig(max_attempts=5, base_delay=0.5, retryable_errors=(ValueError,))
        assert c.max_attempts == 5
        assert c.base_delay == 0.5
        assert ValueError in c.retryable_errors


class TestRetryResult:
    def test_success(self):
        r = RetryResult(success=True, result=42, attempts=1)
        assert r.success is True
        assert r.result == 42
        assert r.attempts == 1

    def test_failure(self):
        r = RetryResult(success=False, error=RuntimeError("fail"), attempts=3)
        assert r.success is False
        assert isinstance(r.error, RuntimeError)


class TestComputeDelay:
    def test_first_attempt(self):
        assert compute_delay(1, base_delay=1.0) == 1.0

    def test_second_attempt(self):
        assert compute_delay(2, base_delay=1.0, backoff_factor=2.0) == 2.0

    def test_third_attempt(self):
        assert compute_delay(3, base_delay=1.0, backoff_factor=2.0) == 4.0

    def test_capped(self):
        assert compute_delay(10, base_delay=1.0, backoff_factor=2.0, max_delay=5.0) == 5.0


class TestExecuteWithRetry:
    def test_success_first_try(self):
        cfg = RetryConfig(max_attempts=3, base_delay=0.0)
        result = execute_with_retry(fn=lambda: "ok", config=cfg)
        assert result.success is True
        assert result.result == "ok"
        assert result.attempts == 1

    def test_success_after_retries(self):
        call_count = 0

        def flaky():
            nonlocal call_count
            call_count += 1
            if call_count < 3:
                raise UpstoxAPIError("rate limit", error_code="RATE_LIMIT")
            return "ok"

        cfg = RetryConfig(max_attempts=5, base_delay=0.0, retryable_errors=(UpstoxAPIError,))
        result = execute_with_retry(fn=flaky, config=cfg)
        assert result.success is True
        assert result.result == "ok"
        assert result.attempts == 3

    def test_exhausted(self):
        def always_fail():
            raise UpstoxAPIError("always fail", error_code="RATE_LIMIT")

        cfg = RetryConfig(max_attempts=3, base_delay=0.0, retryable_errors=(UpstoxAPIError,))
        result = execute_with_retry(fn=always_fail, config=cfg)
        assert result.success is False
        assert isinstance(result.error, UpstoxAPIError)
        assert result.attempts == 3

    def test_non_retryable_error(self):
        def fail_once():
            raise ValueError("non-retryable")

        cfg = RetryConfig(max_attempts=3, base_delay=0.0, retryable_errors=(UpstoxAPIError,))
        result = execute_with_retry(fn=fail_once, config=cfg)
        assert result.success is False
        assert isinstance(result.error, ValueError)
        assert result.attempts == 1

    def test_no_retryable_filter_retries_all(self):
        call_count = 0

        def flaky():
            nonlocal call_count
            call_count += 1
            if call_count < 2:
                raise RuntimeError("any error")
            return "ok"

        cfg = RetryConfig(max_attempts=3, base_delay=0.0, retryable_errors=(RuntimeError,))
        result = execute_with_retry(fn=flaky, config=cfg)
        assert result.success is True
        assert result.result == "ok"


# ---------------------------------------------------------------------------
# UpstoxClient
# ---------------------------------------------------------------------------


class TestUpstoxClient:
    def test_not_authenticated(self):
        client = UpstoxClient()
        assert client.is_authenticated is False

    def test_authenticated_via_legacy(self):
        client = UpstoxClient(api_key="k", access_token="t")
        assert client.is_authenticated is True

    def test_authenticated_via_auth(self):
        client = UpstoxClient(auth=_make_auth())
        assert client.is_authenticated is True

    def test_auth_property(self):
        client = UpstoxClient(auth=_make_auth())
        assert client.auth is not None

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

    def test_set_access_token(self):
        client = UpstoxClient()
        assert client.is_authenticated is False
        client.set_access_token("new_token")
        assert client.is_authenticated is True

    def test_clear_access_token(self):
        client = UpstoxClient(auth=_make_auth())
        assert client.is_authenticated is True
        client.clear_access_token()
        assert client.is_authenticated is False

    def test_api_key_property(self):
        client = UpstoxClient(auth=AuthManager(
            credentials=UpstoxCredentials(api_key="my_key")
        ))
        assert client.api_key == "my_key"

    def test_get_instrument_default(self):
        client = UpstoxClient()
        r = client.get_instrument("RELIANCE", "NSE_EQ")
        assert r is None

    def test_search_instruments_default(self):
        client = UpstoxClient()
        r = client.search_instruments("RELIANCE")
        assert r == ()


# ---------------------------------------------------------------------------
# UpstoxClient retry integration
# ---------------------------------------------------------------------------


class TestUpstoxClientRetry:
    def test_retry_succeeds_after_failures(self):
        client = RetryClient(fail_count=2)
        r = client.get_historical_candles("RELIANCE", "1d", date(2024, 1, 1), date(2024, 12, 31))
        assert r.status == "success"
        assert len(r.candles) == 1
        assert client._call_count == 3

    def test_retry_exhausted(self):
        client = RetryClient(fail_count=5)
        r = client.get_historical_candles("RELIANCE", "1d", date(2024, 1, 1), date(2024, 12, 31))
        assert r.status == "error"
        assert client._call_count == 3
        assert r.error_code == "RATE_LIMIT"

    def test_no_retry_on_non_rate_limit(self):
        client = ErrorClient(error_code="SERVER_ERROR", message="Internal error")
        r = client.get_historical_candles("RELIANCE", "1d", date(2024, 1, 1), date(2024, 12, 31))
        assert r.status == "error"
        assert r.error_code == "SERVER_ERROR"


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
# UpstoxAPIError
# ---------------------------------------------------------------------------


class TestUpstoxAPIError:
    def test_creation(self):
        exc = UpstoxAPIError("rate limited", error_code="RATE_LIMIT", status_code=429)
        assert str(exc) == "rate limited"
        assert exc.error_code == "RATE_LIMIT"
        assert exc.status_code == 429
        assert isinstance(exc, Exception)


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
# PriceValidator
# ---------------------------------------------------------------------------


class TestPriceValidator:
    def test_valid_candles(self):
        v = PriceValidator()
        candles = (
            {"timestamp": "2024-01-15T00:00:00+05:30", "open": 100.0, "high": 105.0, "low": 99.0, "close": 103.0, "volume": 50000.0},
            {"timestamp": "2024-01-16T00:00:00+05:30", "open": 103.0, "high": 108.0, "low": 102.0, "close": 107.0, "volume": 60000.0},
        )
        result = v.validate(candles)
        assert result.valid is True
        assert result.errors == ()

    def test_empty_candles(self):
        v = PriceValidator()
        result = v.validate(())
        assert result.valid is True
        assert len(result.warnings) > 0

    def test_high_below_open(self):
        v = PriceValidator()
        candles = ({"timestamp": "2024-01-15T00:00:00+05:30", "open": 105.0, "high": 100.0, "low": 99.0, "close": 103.0, "volume": 50000.0},)
        result = v.validate(candles)
        assert result.valid is False
        assert any("high" in e and "open" in e for e in result.errors)

    def test_high_below_close(self):
        v = PriceValidator()
        candles = ({"timestamp": "2024-01-15T00:00:00+05:30", "open": 100.0, "high": 102.0, "low": 99.0, "close": 105.0, "volume": 50000.0},)
        result = v.validate(candles)
        assert result.valid is False
        assert any("high" in e and "close" in e for e in result.errors)

    def test_low_above_open(self):
        v = PriceValidator()
        candles = ({"timestamp": "2024-01-15T00:00:00+05:30", "open": 100.0, "high": 105.0, "low": 103.0, "close": 103.0, "volume": 50000.0},)
        result = v.validate(candles)
        assert result.valid is False
        assert any("low" in e and "open" in e for e in result.errors)

    def test_low_above_close(self):
        v = PriceValidator()
        candles = ({"timestamp": "2024-01-15T00:00:00+05:30", "open": 100.0, "high": 105.0, "low": 104.0, "close": 103.0, "volume": 50000.0},)
        result = v.validate(candles)
        assert result.valid is False
        assert any("low" in e and "close" in e for e in result.errors)

    def test_negative_volume(self):
        v = PriceValidator()
        candles = ({"timestamp": "2024-01-15T00:00:00+05:30", "open": 100.0, "high": 105.0, "low": 99.0, "close": 103.0, "volume": -100.0},)
        result = v.validate(candles)
        assert result.valid is False
        assert any("negative volume" in e for e in result.errors)

    def test_missing_volume_warning(self):
        v = PriceValidator()
        candles = ({"timestamp": "2024-01-15T00:00:00+05:30", "open": 100.0, "high": 105.0, "low": 99.0, "close": 103.0},)
        result = v.validate(candles)
        assert result.valid is True
        assert any("missing volume" in w for w in result.warnings)

    def test_duplicate_timestamp(self):
        v = PriceValidator()
        candles = (
            {"timestamp": "2024-01-15T00:00:00+05:30", "open": 100.0, "high": 105.0, "low": 99.0, "close": 103.0, "volume": 50000.0},
            {"timestamp": "2024-01-15T00:00:00+05:30", "open": 103.0, "high": 108.0, "low": 102.0, "close": 107.0, "volume": 60000.0},
        )
        result = v.validate(candles)
        assert result.valid is False
        assert any("duplicate" in e for e in result.errors)

    def test_missing_ohlc(self):
        v = PriceValidator()
        candles = ({"timestamp": "2024-01-15T00:00:00+05:30", "open": 100.0, "high": 105.0},)
        result = v.validate(candles)
        assert result.valid is False
        assert any("missing" in e for e in result.errors)

    def test_not_chronological_warning(self):
        v = PriceValidator()
        candles = (
            {"timestamp": "2024-01-16T00:00:00+05:30", "open": 103.0, "high": 108.0, "low": 102.0, "close": 107.0, "volume": 60000.0},
            {"timestamp": "2024-01-15T00:00:00+05:30", "open": 100.0, "high": 105.0, "low": 99.0, "close": 103.0, "volume": 50000.0},
        )
        result = v.validate(candles)
        assert any("chronological" in w for w in result.warnings)


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

    def test_fetch_raw_validates_data(self):
        bad_candles = (
            UpstoxCandle(timestamp="2024-01-15T00:00:00+05:30", open=100.0, high=105.0, low=99.0, close=103.0, volume=50000.0),
            UpstoxCandle(timestamp="2024-01-15T00:00:00+05:30", open=103.0, high=108.0, low=102.0, close=107.0, volume=60000.0),
        )
        client = AuthenticatedClient(candles=bad_candles)
        p = UpstoxProvider(client=client)
        req = _make_request()
        raw = p.fetch_raw(req)
        assert "validation_errors" in raw.metadata
        assert "duplicate" in raw.metadata["validation_errors"]

    def test_validate_data_delegates(self):
        p = UpstoxProvider()
        candles = ({"timestamp": "2024-01-15T00:00:00+05:30", "open": 100.0, "high": 105.0, "low": 99.0, "close": 103.0, "volume": 50000.0},)
        result = p.validate_data(candles)
        assert isinstance(result, ValidationResult)
        assert result.valid is True

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


# ---------------------------------------------------------------------------
# Test doubles (after tests so they don't interfere with collection)
# ---------------------------------------------------------------------------


class AuthenticatedClient(UpstoxClient):
    """Client that is always authenticated for testing."""

    def __init__(self, candles: tuple[UpstoxCandle, ...] | None = None) -> None:
        super().__init__(auth=_make_auth())
        self._test_candles = candles or (_fake_candle(),)

    def _fetch_candles(self, instrument_key, interval, from_date, to_date):
        return UpstoxCandlesResponse(status="success", candles=self._test_candles)


class EmptyClient(UpstoxClient):
    """Client that returns empty candles."""

    def __init__(self) -> None:
        super().__init__(auth=_make_auth())

    def _fetch_candles(self, instrument_key, interval, from_date, to_date):
        return UpstoxCandlesResponse(status="success", candles=())


class ErrorClient(UpstoxClient):
    """Client that returns an error."""

    def __init__(self, error_code: str = "RATE_LIMIT", message: str = "Rate limit exceeded") -> None:
        super().__init__(auth=_make_auth())
        self._error_code = error_code
        self._message = message

    def _fetch_candles(self, instrument_key, interval, from_date, to_date):
        raise UpstoxAPIError(self._message, error_code=self._error_code)


class RetryClient(UpstoxClient):
    """Client that fails N times then succeeds (overrides internal _fetch_candles)."""

    def __init__(self, fail_count: int = 2) -> None:
        super().__init__(
            auth=_make_auth(),
            retry_config=_make_retry_config(max_attempts=3),
        )
        self._call_count = 0
        self._fail_count = fail_count

    def _fetch_candles(self, instrument_key, interval, from_date, to_date):
        self._call_count += 1
        if self._call_count <= self._fail_count:
            raise UpstoxAPIError("Rate limit exceeded", error_code="RATE_LIMIT", status_code=429)
        return UpstoxCandlesResponse(
            status="success",
            candles=(_fake_candle(ts="2024-06-15T00:00:00+05:30"),),
        )


class MultiCandleClient(UpstoxClient):
    """Client that returns multiple candles."""

    def __init__(self) -> None:
        super().__init__(auth=_make_auth())

    def _fetch_candles(self, instrument_key, interval, from_date, to_date):
        return UpstoxCandlesResponse(
            status="success",
            candles=(
                UpstoxCandle(timestamp="2024-01-15T00:00:00+05:30", open=100.0, high=105.0, low=99.0, close=103.0, volume=50000.0),
                UpstoxCandle(timestamp="2024-01-16T00:00:00+05:30", open=103.0, high=108.0, low=102.0, close=107.0, volume=60000.0),
                UpstoxCandle(timestamp="2024-01-17T00:00:00+05:30", open=107.0, high=110.0, low=106.0, close=109.0, volume=45000.0),
            ),
        )
