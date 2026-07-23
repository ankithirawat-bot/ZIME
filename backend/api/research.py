"""
Research API Router.

Exposes the ResearchService through FastAPI endpoints.
"""

from __future__ import annotations

from fastapi import APIRouter, HTTPException

from backend.api.models import (
    EngineErrorResponse,
    FactorResultResponse,
    HealthResponse,
    ResearchRequest,
    ResearchResponse,
)
from backend.core.api_constants import HEALTH_ENDPOINT, ROUTE_RESEARCH
from backend.engines.factor_engine import FactorRequest
from backend.services.research_service import VALID_INTERVALS, VALID_PERIODS, ResearchService

router = APIRouter(prefix=ROUTE_RESEARCH, tags=["research"])

# Valid periods and intervals for request validation
VALID_PERIODS_LIST = sorted(VALID_PERIODS)
VALID_INTERVALS_LIST = sorted(VALID_INTERVALS)


@router.get(
    HEALTH_ENDPOINT,
    response_model=HealthResponse,
    summary="Health check",
    description="Returns the health status of the research service.",
)
def research_health() -> HealthResponse:
    """Health check endpoint for the research service."""
    return HealthResponse()


@router.post(
    "",
    response_model=ResearchResponse,
    summary="Run research analysis",
    description=(
        "Execute factor analysis for a given stock symbol. "
        "Downloads historical OHLCV data and runs the requested "
        "factors through the FactorEngine."
    ),
    responses={
        400: {"description": "Validation error"},
        500: {"description": "Internal service error"},
    },
)
def run_research(request: ResearchRequest) -> ResearchResponse:
    """Run a research analysis for a symbol.

    Validates the request, invokes the ResearchService, and returns
    structured results with factor outputs and any errors.
    """
    # Validate period
    if request.period not in VALID_PERIODS:
        raise HTTPException(
            status_code=400,
            detail=f"Invalid period '{request.period}'. Valid: {VALID_PERIODS_LIST}",
        )

    # Validate interval
    if request.interval not in VALID_INTERVALS:
        raise HTTPException(
            status_code=400,
            detail=f"Invalid interval '{request.interval}'. Valid: {VALID_INTERVALS_LIST}",
        )

    # Validate factor requests
    if not request.factor_requests:
        raise HTTPException(
            status_code=400,
            detail="factor_requests must not be empty",
        )

    # Convert Pydantic models to FactorRequest objects
    factor_requests = [
        FactorRequest(factor=f.factor, params=f.params)
        for f in request.factor_requests
    ]

    # Invoke ResearchService
    try:
        service = ResearchService()
        result = service.analyze(
            symbol=request.symbol,
            factor_requests=factor_requests,
            period=request.period,
            interval=request.interval,
        )
    except Exception as exc:
        raise HTTPException(
            status_code=500,
            detail=f"Internal service error: {exc}",
        )

    # Convert FactorResult objects to response models
    factor_results = {}
    for label, fr in result.factor_results.items():
        factor_results[label] = FactorResultResponse(
            factor_name=fr.factor_name,
            factor_category=fr.factor_category.value,
            symbol=fr.symbol,
            value=fr.value,
            signal=fr.signal.value,
            as_of=fr.as_of.isoformat() if fr.as_of else None,
            confidence=fr.confidence,
            metadata=fr.metadata,
        )

    # Convert EngineError objects to response models
    errors = [
        EngineErrorResponse(
            factor=e.factor,
            message=e.message,
            detail=e.detail,
        )
        for e in result.engine_errors
    ]

    return ResearchResponse(
        success=True,
        symbol=result.symbol,
        generated_at=result.generated_at.isoformat(),
        factor_results=factor_results,
        errors=errors,
        execution_time_ms=result.execution_time_ms,
        metadata=result.metadata,
    )
