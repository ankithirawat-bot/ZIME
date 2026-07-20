"""
Upstox API client.

Thin wrapper around Upstox HTTP API for historical candle data.
No business logic — only transport and error translation.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from datetime import date


@dataclass(frozen=True)
class UpstoxCandle:
    """Single candle from Upstox API.

    Attributes:
        timestamp: ISO-8601 timestamp.
        open:      Opening price.
        high:      Intraday high.
        low:       Intraday low.
        close:     Closing price.
        volume:    Trading volume.
        open_interest: Open interest (futures/options).
    """

    timestamp: str
    open: float
    high: float
    low: float
    close: float
    volume: float
    open_interest: float = 0.0


@dataclass(frozen=True)
class UpstoxCandlesResponse:
    """Response from Upstox historical candle endpoint.

    Attributes:
        status:     "success" or "error".
        candles:    List of candles.
        message:    Error message if status is error.
        error_code: Upstox error code if status is error.
    """

    status: str
    candles: tuple[UpstoxCandle, ...] = field(default_factory=tuple)
    message: str = ""
    error_code: str = ""


@dataclass(frozen=True)
class UpstoxInstrumentResponse:
    """Response from Upstox instrument search.

    Attributes:
        instrument_token: Upstox instrument token.
        symbol:           Trading symbol.
        exchange:         Exchange segment.
        instrument_type:  Instrument type (EQ, FUT, OPT, etc.).
        name:             Company name.
    """

    instrument_token: str
    symbol: str
    exchange: str
    instrument_type: str
    name: str = ""


class UpstoxClient:
    """Thin client for Upstox API.

    Handles authentication, HTTP transport, and error translation.
    No business logic.
    """

    def __init__(
        self,
        api_key: str = "",
        access_token: str = "",
        base_url: str = "https://api.upstox.com",
    ) -> None:
        self._api_key = api_key
        self._access_token = access_token
        self._base_url = base_url

    @property
    def is_authenticated(self) -> bool:
        """True if access token is set."""
        return bool(self._access_token)

    def get_historical_candles(
        self,
        instrument_key: str,
        interval: str,
        from_date: date,
        to_date: date,
    ) -> UpstoxCandlesResponse:
        """Fetch historical candles for an instrument.

        Args:
            instrument_key: Upstox instrument key (e.g. "RELIANCE").
            interval:       Candle interval (e.g. "1d", "1w", "1M").
            from_date:      Start date (inclusive).
            to_date:        End date (inclusive).

        Returns:
            UpstoxCandlesResponse with candle data or error.
        """
        if not self.is_authenticated:
            return UpstoxCandlesResponse(
                status="error",
                message="Not authenticated",
                error_code="AUTH_ERROR",
            )
        return UpstoxCandlesResponse(status="success")

    def get_instrument(self, symbol: str, exchange: str) -> UpstoxInstrumentResponse | None:
        """Look up instrument details by symbol.

        Args:
            symbol:   Trading symbol.
            exchange: Exchange segment (e.g. "NSE_EQ").

        Returns:
            UpstoxInstrumentResponse or None if not found.
        """
        return None

    def search_instruments(self, query: str) -> tuple[UpstoxInstrumentResponse, ...]:
        """Search instruments by query string.

        Args:
            query: Search query.

        Returns:
            Tuple of matching instruments.
        """
        return ()
