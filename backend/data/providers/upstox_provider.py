"""
Upstox Market Data Provider.

First production MarketDataProvider implementation.
Fetches historical daily OHLCV from Upstox API.
"""

from __future__ import annotations

from backend.data.models import (
    DataRequest,
    DataType,
    ProviderIdentity,
    ProviderType,
    RawDataResponse,
)
from backend.data.provider import MarketDataProvider
from backend.data.providers.instrument_mapper import InstrumentMapper
from backend.data.providers.price_validator import PriceValidator, ValidationResult
from backend.data.providers.upstox_client import UpstoxClient


class UpstoxProvider(MarketDataProvider):
    """MarketDataProvider for Upstox.

    Fetches historical daily OHLCV candles from Upstox API.
    Normalization is handled by the DataEngine layer.
    """

    def __init__(
        self,
        client: UpstoxClient | None = None,
        mapper: InstrumentMapper | None = None,
        validator: PriceValidator | None = None,
    ) -> None:
        self._client = client or UpstoxClient()
        self._mapper = mapper or InstrumentMapper()
        self._validator = validator or PriceValidator()

    def supports(self, data_type: DataType) -> bool:
        """Return True if this provider can supply *data_type*.

        Only PRICE_DAILY is supported.
        """
        return data_type == DataType.PRICE_DAILY

    def fetch_raw(self, request: DataRequest) -> RawDataResponse:
        """Fetch raw daily OHLCV data from Upstox.

        Args:
            request: Validated data request.

        Returns:
            RawDataResponse with Upstox candle payload.
        """
        identity = ProviderIdentity(
            provider_type=ProviderType.UPSTOX,
            symbol=request.symbol,
            exchange=request.exchange,
            data_type=request.data_type,
        )

        instrument_key = self._mapper.resolve(request.symbol)
        if instrument_key is None:
            return RawDataResponse(
                provider_type=identity,
                payload=(),
                metadata={"error": f"Unknown symbol: {request.symbol}"},
            )

        exchange_segment = self._mapper.exchange_segment(request.exchange)
        response = self._client.get_historical_candles(
            instrument_key=instrument_key,
            interval="1d",
            from_date=request.start_date,
            to_date=request.end_date,
        )

        if response.status == "error":
            return RawDataResponse(
                provider_type=identity,
                payload=(),
                metadata={
                    "error": response.message,
                    "error_code": response.error_code,
                },
            )

        payload = tuple(
            {
                "timestamp": candle.timestamp,
                "open": candle.open,
                "high": candle.high,
                "low": candle.low,
                "close": candle.close,
                "volume": candle.volume,
                "open_interest": candle.open_interest,
            }
            for candle in response.candles
        )

        validation = self._validator.validate(payload)
        metadata: dict[str, str] = {
            "instrument_key": instrument_key,
            "exchange_segment": exchange_segment,
            "interval": "1d",
        }
        if validation.errors:
            metadata["validation_errors"] = "; ".join(validation.errors)
        if validation.warnings:
            metadata["validation_warnings"] = "; ".join(validation.warnings)

        return RawDataResponse(
            provider_type=identity,
            payload=payload,
            metadata=metadata,
        )

    def validate(self, request: DataRequest) -> bool:
        """Pre-flight validation for Upstox requests.

        Checks:
            - Symbol is mappable.
            - Exchange is supported.
            - Data type is supported.

        Args:
            request: The request to validate.

        Returns:
            True when the request is valid for Upstox.
        """
        if not self.supports(request.data_type):
            return False
        if not self._mapper.has_symbol(request.symbol):
            return False
        if request.exchange.upper() not in ("NSE", "BSE"):
            return False
        return True

    def validate_data(
        self, candles: tuple[dict[str, object], ...]
    ) -> ValidationResult:
        """Validate candle data quality.

        Args:
            candles: Candle records.

        Returns:
            ValidationResult with errors and warnings.
        """
        return self._validator.validate(candles)

    def provider_name(self) -> str:
        """Unique identifier for this provider."""
        return "upstox"

    def provider_type(self) -> ProviderType:
        """Return the ProviderType for this provider."""
        return ProviderType.UPSTOX

    def version(self) -> str:
        """Semantic version of this provider implementation."""
        return "1.0.0"
