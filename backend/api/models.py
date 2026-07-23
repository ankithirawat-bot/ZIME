"""
Pydantic models for the Research API.

Request and response schemas for the research endpoints.
"""

from __future__ import annotations

from typing import Any

from pydantic import BaseModel, Field

from backend.core.constants import DEFAULT_DATA_INTERVAL, DEFAULT_DATA_PERIOD


class FactorRequestModel(BaseModel):
    """A single factor execution request.

    Attributes:
        factor: Registry name of the factor (e.g. "sma", "rsi").
        params: Keyword arguments to pass to the factor constructor.
    """

    factor: str = Field(
        ...,
        description="Registry name of the factor",
        examples=["sma"],
    )
    params: dict[str, Any] = Field(
        default_factory=dict,
        description="Constructor parameters for the factor",
        examples=[{"period": 20}],
    )


class ResearchRequest(BaseModel):
    """Request body for the research analysis endpoint.

    Attributes:
        symbol:          Ticker symbol (e.g. "RELIANCE.NS").
        factor_requests: List of factor requests to execute.
        period:          Historical period for data download.
        interval:        Data interval (e.g. "1d", "1h").
    """

    symbol: str = Field(
        ...,
        min_length=1,
        description="Ticker symbol to analyze",
        examples=["RELIANCE.NS"],
    )
    factor_requests: list[FactorRequestModel] = Field(
        ...,
        min_length=1,
        description="List of factor requests to execute",
        examples=[[{"factor": "sma", "params": {"period": 20}}]],
    )
    period: str = Field(
        default=DEFAULT_DATA_PERIOD,
        description="Historical period for data download",
        examples=["1y"],
    )
    interval: str = Field(
        default=DEFAULT_DATA_INTERVAL,
        description="Data interval",
        examples=["1d"],
    )


class FactorResultResponse(BaseModel):
    """Response for a single factor result.

    Attributes:
        factor_name:    Name of the factor that produced this result.
        factor_category: Category of the factor.
        symbol:         Ticker symbol.
        value:          Primary numeric result.
        signal:         Directional signal.
        as_of:          Date the data is current to.
        confidence:     Optional confidence score.
        metadata:       Additional factor-specific data.
    """

    factor_name: str
    factor_category: str
    symbol: str
    value: float | None
    signal: str
    as_of: str | None
    confidence: float | None
    metadata: dict[str, Any] | None


class EngineErrorResponse(BaseModel):
    """Error that occurred during factor execution.

    Attributes:
        factor:  The factor name that failed.
        message: Human-readable error description.
        detail:  Optional traceback or exception string.
    """

    factor: str
    message: str
    detail: str = ""


class ResearchResponse(BaseModel):
    """Response from the research analysis endpoint.

    Attributes:
        success:           Whether the analysis completed.
        symbol:            Ticker symbol analyzed.
        generated_at:      Timestamp when the result was created.
        factor_results:    Mapping of factor labels to results.
        errors:            List of errors that occurred.
        execution_time_ms: Wall-clock time for the analysis.
        metadata:          Additional context.
    """

    success: bool
    symbol: str
    generated_at: str
    factor_results: dict[str, FactorResultResponse]
    errors: list[EngineErrorResponse]
    execution_time_ms: float
    metadata: dict[str, Any] = Field(default_factory=dict)


class HealthResponse(BaseModel):
    """Health check response.

    Attributes:
        status: Service health status.
        version: API version.
    """

    status: str = "healthy"
    version: str = "1.0.0"
