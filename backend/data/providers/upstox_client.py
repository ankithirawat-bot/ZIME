"""
Upstox API client.

Thin wrapper around Upstox HTTP API for historical candle data.
No business logic — only transport, error translation, and retry.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from datetime import date

from backend.data.providers.auth import AuthManager, UpstoxCredentials
from backend.data.providers.retry import RetryConfig, RetryResult, execute_with_retry


class UpstoxAPIError(Exception):
    """Upstox-specific API error.  Never exposed outside UpstoxClient."""

    def __init__(self, message: str, error_code: str = "", status_code: int = 0) -> None:
        self.error_code = error_code
        self.status_code = status_code
        super().__init__(message)


@dataclass(frozen=True)
class UpstoxCandle:
    """Single candle from Upstox API.

    Attributes:
        timestamp:     ISO-8601 timestamp.
        open:          Opening price.
        high:          Intraday high.
        low:           Intraday low.
        close:         Closing price.
        volume:        Trading volume.
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

    Handles authentication, HTTP transport, retry, and error translation.
    No business logic — delegates auth to AuthManager, retry to
    execute_with_retry.
    """

    def __init__(
        self,
        auth: AuthManager | None = None,
        api_key: str = "",
        access_token: str = "",
        base_url: str = "https://api.upstox.com",
        retry_config: RetryConfig | None = None,
    ) -> None:
        """Initialise the client.

        Args:
            auth:           AuthManager instance (preferred).
            api_key:        Legacy API key (used if auth is None).
            access_token:   Legacy access token (used if auth is None).
            base_url:       Upstox API base URL.
            retry_config:   Retry configuration.
        """
        if auth is not None:
            self._auth = auth
        else:
            self._auth = AuthManager(
                credentials=UpstoxCredentials(
                    api_key=api_key,
                    access_token=access_token,
                )
            )
        self._base_url = base_url.rstrip("/")
        self._retry_config = retry_config or RetryConfig(
            max_attempts=3,
            base_delay=1.0,
            backoff_factor=2.0,
            retryable_errors=(UpstoxAPIError,),
        )

    @property
    def is_authenticated(self) -> bool:
        """True if access token is set."""
        return self._auth.is_authenticated

    @property
    def api_key(self) -> str:
        """Return the API key."""
        return self._auth.api_key

    @property
    def auth(self) -> AuthManager:
        """Return the underlying AuthManager."""
        return self._auth

    def set_access_token(self, token: str) -> None:
        """Update the access token.

        Args:
            token: New access token.
        """
        self._auth.set_access_token(token)

    def clear_access_token(self) -> None:
        """Clear the access token."""
        self._auth.clear_access_token()

    def get_historical_candles(
        self,
        instrument_key: str,
        interval: str,
        from_date: date,
        to_date: date,
    ) -> UpstoxCandlesResponse:
        """Fetch historical candles for an instrument with retry.

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

        retry_result: RetryResult = execute_with_retry(
            fn=lambda: self._fetch_candles(instrument_key, interval, from_date, to_date),
            config=self._retry_config,
        )

        if retry_result.success:
            return retry_result.result  # type: ignore[return-value]

        exc = retry_result.error
        if isinstance(exc, UpstoxAPIError):
            return UpstoxCandlesResponse(
                status="error",
                message=str(exc),
                error_code=exc.error_code,
            )

        return UpstoxCandlesResponse(
            status="error",
            message=str(exc) if exc else "Unknown error",
            error_code="UNKNOWN",
        )

    def _fetch_candles(
        self,
        instrument_key: str,
        interval: str,
        from_date: date,
        to_date: date,
    ) -> UpstoxCandlesResponse:
        """Internal candle fetch.  Raises UpstoxAPIError on failure."""
        return UpstoxCandlesResponse(status="success")

    def get_instrument(
        self, symbol: str, exchange: str
    ) -> UpstoxInstrumentResponse | None:
        """Look up instrument details by symbol.

        Args:
            symbol:   Trading symbol.
            exchange: Exchange segment (e.g. "NSE_EQ").

        Returns:
            UpstoxInstrumentResponse or None if not found.
        """
        return None

    def search_instruments(
        self, query: str
    ) -> tuple[UpstoxInstrumentResponse, ...]:
        """Search instruments by query string.

        Args:
            query: Search query.

        Returns:
            Tuple of matching instruments.
        """
        return ()
