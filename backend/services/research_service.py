"""
Research Service.

Orchestrates market data retrieval and factor execution to provide
end-to-end research capabilities for a single instrument.

This is an application service, NOT an API endpoint.
"""

from __future__ import annotations

import time
from dataclasses import dataclass, field
from datetime import date, datetime
from typing import Any

import backend.factors.momentum  # noqa: F401 — triggers factor registration
import backend.factors.price  # noqa: F401 — triggers factor registration
from backend.core.constants import DEFAULT_DATA_INTERVAL, DEFAULT_DATA_PERIOD
from backend.core.factor_result import FactorResult
from backend.engines.factor_engine import EngineError, FactorEngine, FactorRequest
from backend.providers.base import MarketDataProvider
from backend.providers.yfinance_provider import YFinanceProvider

VALID_PERIODS = {"1d", "5d", "1mo", "3mo", "6mo", "1y", "2y", "5y", "10y", "ytd", "max"}
VALID_INTERVALS = {"1m", "2m", "5m", "15m", "30m", "60m", "90m", "1h", "1d", "5d", "1wk", "1mo", "3mo"}
REQUIRED_COLUMNS = {"Open", "High", "Low", "Close", "Volume"}


@dataclass(frozen=True)
class ResearchResult:
    """Immutable output from a research analysis.

    Attributes:
        symbol:           Ticker symbol analyzed.
        period:           Time period requested (e.g. "1y").
        interval:         Data interval (e.g. "1d").
        generated_at:     Timestamp when this result was created.
        data_start:       Start date of the fetched data.
        data_end:         End date of the fetched data.
        rows:             Number of data rows fetched.
        execution_time_ms: Wall-clock time for the entire analysis.
        factor_results:   Mapping of factor labels to FactorResult.
        engine_errors:    List of EngineError for any factors that failed.
        metadata:         Additional context (e.g. validation warnings).
    """

    symbol: str
    period: str
    interval: str
    generated_at: datetime
    data_start: date | None
    data_end: date | None
    rows: int
    execution_time_ms: float
    factor_results: dict[str, FactorResult]
    engine_errors: list[EngineError]
    metadata: dict[str, Any] = field(default_factory=dict)


class ResearchService:
    """Orchestrates data retrieval and factor execution.

    Downloads historical OHLCV data for a symbol and runs the
    requested factors through the FactorEngine. Returns a structured
    ResearchResult with all factor outputs and any errors.

    The data provider is injected via the ``provider`` parameter.
    Defaults to YFinanceProvider. Any MarketDataProvider implementation
    can be used.

    This service never crashes. All errors are captured in the result.

    Usage::

        service = ResearchService()
        result = service.analyze(
            symbol="RELIANCE.NS",
            factor_requests=[
                FactorRequest("sma", {"period": 20}),
                FactorRequest("rsi", {"period": 14}),
            ],
            period="1y",
            interval="1d",
        )
        for label, fr in result.factor_results.items():
            print(f"{label}: {fr.value}")
    """

    def __init__(self, provider: MarketDataProvider | None = None) -> None:
        """Initialize the research service.

        Args:
            provider: Market data provider instance. Defaults to YFinanceProvider.
        """
        self._provider = provider if provider is not None else YFinanceProvider()

    def analyze(
        self,
        symbol: str,
        factor_requests: list[FactorRequest],
        period: str = DEFAULT_DATA_PERIOD,
        interval: str = DEFAULT_DATA_INTERVAL,
    ) -> ResearchResult:
        """Run a full research analysis for a symbol.

        Args:
            symbol:          Ticker symbol (e.g. "RELIANCE.NS").
            factor_requests: List of FactorRequest instances to execute.
            period:          Historical period for data download.
            interval:        Data interval (e.g. "1d", "1h").

        Returns:
            A ResearchResult with factor outputs and metadata.
            Always returns a result — never raises exceptions.
        """
        start_time = time.perf_counter()
        generated_at = datetime.now()
        metadata: dict[str, Any] = {}

        # Validate symbol
        if not symbol or not isinstance(symbol, str) or not symbol.strip():
            return self._error_result(
                symbol=symbol or "",
                period=period,
                interval=interval,
                start_time=start_time,
                generated_at=generated_at,
                metadata=metadata,
                error_factor="(input)",
                error_message="Symbol must be a non-empty string",
            )

        symbol = symbol.strip()

        # Validate period
        if period not in VALID_PERIODS:
            return self._error_result(
                symbol=symbol,
                period=period,
                interval=interval,
                start_time=start_time,
                generated_at=generated_at,
                metadata=metadata,
                error_factor="(input)",
                error_message=f"Invalid period '{period}'. Valid: {sorted(VALID_PERIODS)}",
            )

        # Validate interval
        if interval not in VALID_INTERVALS:
            return self._error_result(
                symbol=symbol,
                period=period,
                interval=interval,
                start_time=start_time,
                generated_at=generated_at,
                metadata=metadata,
                error_factor="(input)",
                error_message=f"Invalid interval '{interval}'. Valid: {sorted(VALID_INTERVALS)}",
            )

        # Validate factor_requests type
        if not isinstance(factor_requests, list):
            return self._error_result(
                symbol=symbol,
                period=period,
                interval=interval,
                start_time=start_time,
                generated_at=generated_at,
                metadata=metadata,
                error_factor="(input)",
                error_message=f"factor_requests must be a list, got {type(factor_requests).__name__}",
            )

        # Detect duplicates
        seen: set[str] = set()
        for req in factor_requests:
            label = FactorEngine._make_label(req.factor, req.params)
            if label in seen:
                metadata["warnings"] = metadata.get("warnings", [])
                metadata["warnings"].append(f"Duplicate factor request '{label}' — first occurrence used")
                break
            seen.add(label)

        # Download data
        try:
            data = self._provider.get_history(symbol, period, interval)
        except Exception as exc:
            return self._error_result(
                symbol=symbol,
                period=period,
                interval=interval,
                start_time=start_time,
                generated_at=generated_at,
                metadata=metadata,
                error_factor="(download)",
                error_message=f"Download failed for '{symbol}': {exc}",
            )

        # Validate data is not None
        if data is None:
            return self._error_result(
                symbol=symbol,
                period=period,
                interval=interval,
                start_time=start_time,
                generated_at=generated_at,
                metadata=metadata,
                error_factor="(data)",
                error_message=f"No data returned for '{symbol}'",
            )

        # Validate data is not empty
        if data.empty:
            return self._error_result(
                symbol=symbol,
                period=period,
                interval=interval,
                start_time=start_time,
                generated_at=generated_at,
                metadata=metadata,
                error_factor="(data)",
                error_message=f"Empty dataframe for '{symbol}'",
            )

        # Validate required columns
        missing_cols = REQUIRED_COLUMNS - set(data.columns)
        if missing_cols:
            return self._error_result(
                symbol=symbol,
                period=period,
                interval=interval,
                start_time=start_time,
                generated_at=generated_at,
                metadata=metadata,
                error_factor="(data)",
                error_message=f"Missing columns: {sorted(missing_cols)}. Found: {list(data.columns)}",
                rows=len(data),
            )

        # Normalize column names (lowercase) — copy to avoid mutating input
        data = data.copy()
        data.columns = [c.lower() for c in data.columns]

        # Compute metadata
        data_start = data.index[0].date() if len(data) > 0 else None
        data_end = data.index[-1].date() if len(data) > 0 else None

        # Execute factors via engine
        engine = FactorEngine()
        requests = [{"factor": f.factor, "params": f.params} for f in factor_requests]
        engine_result = engine.calculate(data=data, requests=requests, symbol=symbol)

        execution_time_ms = (time.perf_counter() - start_time) * 1000

        return ResearchResult(
            symbol=symbol,
            period=period,
            interval=interval,
            generated_at=generated_at,
            data_start=data_start,
            data_end=data_end,
            rows=len(data),
            execution_time_ms=execution_time_ms,
            factor_results=engine_result.results,
            engine_errors=engine_result.errors,
            metadata=metadata,
        )

    def _error_result(
        self,
        symbol: str,
        period: str,
        interval: str,
        start_time: float,
        generated_at: datetime,
        metadata: dict[str, Any],
        error_factor: str,
        error_message: str,
        rows: int = 0,
    ) -> ResearchResult:
        """Build a ResearchResult for an error condition.

        Centralizes error result construction to avoid repetition.
        """
        return ResearchResult(
            symbol=symbol,
            period=period,
            interval=interval,
            generated_at=generated_at,
            data_start=None,
            data_end=None,
            rows=rows,
            execution_time_ms=(time.perf_counter() - start_time) * 1000,
            factor_results={},
            engine_errors=[EngineError(factor=error_factor, message=error_message)],
            metadata=metadata,
        )
