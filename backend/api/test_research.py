"""
Sprint 9: Research API — Full Verification Suite.

All tests mock ResearchService. No internet, no yfinance, no real downloads.
"""

from __future__ import annotations

from datetime import date, datetime
from unittest.mock import MagicMock, patch

from fastapi import FastAPI
from fastapi.testclient import TestClient

# Import the app and router
from backend.api.research import router
from backend.core.api_constants import HEALTH_ENDPOINT, ROUTE_RESEARCH
from backend.core.enums import FactorCategory, Signal
from backend.core.factor_result import FactorResult
from backend.engines.factor_engine import EngineError
from backend.services.research_service import ResearchResult

# Create a test app with just the research router
app = FastAPI()
app.include_router(router)
client = TestClient(app)

print("=== Sprint 9: Research API Verification ===")
print("")

passed = 0
failed = 0


def check(name: str, condition: bool, detail: str = "") -> None:
    global passed, failed
    if condition:
        passed += 1
        print(f"  PASS: {name}")
    else:
        failed += 1
        print(f"  FAIL: {name}{f' ({detail})' if detail else ''}")


def make_fake_result(
    symbol: str = "RELIANCE.NS",
    factor_results: dict | None = None,
    errors: list | None = None,
) -> ResearchResult:
    """Build a fake ResearchResult for mocking."""
    if factor_results is None:
        factor_results = {
            "SMA20": FactorResult(
                factor_name="sma",
                factor_category=FactorCategory.TECHNICAL,
                symbol=symbol,
                value=95.5,
                signal=Signal.BULLISH,
                as_of=date(2025, 12, 31),
                confidence=None,
                metadata={"period": 20},
            )
        }
    if errors is None:
        errors = []

    return ResearchResult(
        symbol=symbol,
        period="1y",
        interval="1d",
        generated_at=datetime(2025, 7, 19, 12, 0, 0),
        data_start=date(2025, 1, 1),
        data_end=date(2025, 12, 31),
        rows=250,
        execution_time_ms=123.45,
        factor_results=factor_results,
        engine_errors=errors,
        metadata={},
    )


def mock_research_service(result: ResearchResult):
    """Create a patch for ResearchService.analyze."""
    mock_service = MagicMock()
    mock_service.analyze.return_value = result
    return patch("backend.api.research.ResearchService", return_value=mock_service)


# ========== HEALTH ENDPOINT ==========
print("--- Health Endpoint ---")
response = client.get(f"{ROUTE_RESEARCH}/{HEALTH_ENDPOINT.lstrip('/')}")
check("health: status 200", response.status_code == 200)
data = response.json()
check("health: status=healthy", data["status"] == "healthy")
check("health: version exists", "version" in data)

# ========== SUCCESSFUL REQUEST ==========
print("--- Successful Request ---")
fake_result = make_fake_result()
with mock_research_service(fake_result):
    response = client.post(
        ROUTE_RESEARCH,
        json={
            "symbol": "RELIANCE.NS",
            "factor_requests": [
                {"factor": "sma", "params": {"period": 20}},
            ],
            "period": "1y",
            "interval": "1d",
        },
    )
check("success: status 200", response.status_code == 200)
data = response.json()
check("success: success=True", data["success"] is True)
check("success: symbol", data["symbol"] == "RELIANCE.NS")
check("success: generated_at", data["generated_at"] == "2025-07-19T12:00:00")
check("success: execution_time_ms", data["execution_time_ms"] == 123.45)
check("success: factor_results present", len(data["factor_results"]) > 0)
check("success: SMA20 in results", "SMA20" in data["factor_results"])
sma = data["factor_results"]["SMA20"]
check("success: SMA20 value", sma["value"] == 95.5)
check("success: SMA20 signal", sma["signal"] == "bullish")
check("success: SMA20 factor_name", sma["factor_name"] == "sma")
check("success: SMA20 as_of", sma["as_of"] == "2025-12-31")
check("success: SMA20 metadata", sma["metadata"] == {"period": 20})
check("success: errors empty", len(data["errors"]) == 0)
check("success: metadata is dict", isinstance(data["metadata"], dict))

# ========== MULTIPLE FACTORS ==========
print("--- Multiple Factors ---")
multi_result = make_fake_result(
    factor_results={
        "SMA20": FactorResult(
            factor_name="sma", factor_category=FactorCategory.TECHNICAL,
            symbol="RELIANCE.NS", value=95.5, signal=Signal.BULLISH,
            as_of=date(2025, 12, 31),
        ),
        "RSI14": FactorResult(
            factor_name="rsi", factor_category=FactorCategory.MOMENTUM,
            symbol="RELIANCE.NS", value=55.0, signal=Signal.NEUTRAL,
            as_of=date(2025, 12, 31),
        ),
    }
)
with mock_research_service(multi_result):
    response = client.post(
        ROUTE_RESEARCH,
        json={
            "symbol": "RELIANCE.NS",
            "factor_requests": [
                {"factor": "sma", "params": {"period": 20}},
                {"factor": "rsi", "params": {"period": 14}},
            ],
        },
    )
check("multi: status 200", response.status_code == 200)
data = response.json()
check("multi: 2 factor results", len(data["factor_results"]) == 2)
check("multi: SMA20 present", "SMA20" in data["factor_results"])
check("multi: RSI14 present", "RSI14" in data["factor_results"])

# ========== WITH ERRORS ==========
print("--- With Errors ---")
error_result = make_fake_result(
    factor_results={},
    errors=[EngineError(factor="sma", message="Factor 'sma' not found")],
)
with mock_research_service(error_result):
    response = client.post(
        ROUTE_RESEARCH,
        json={
            "symbol": "INVALID.NS",
            "factor_requests": [{"factor": "sma", "params": {}}],
        },
    )
check("errors: status 200", response.status_code == 200)
data = response.json()
check("errors: 1 error", len(data["errors"]) == 1)
check("errors: factor name", data["errors"][0]["factor"] == "sma")
check("errors: message", "not found" in data["errors"][0]["message"])

# ========== VALIDATION: EMPTY SYMBOL ==========
print("--- Validation: Empty Symbol ---")
response = client.post(
    ROUTE_RESEARCH,
    json={
        "symbol": "",
        "factor_requests": [{"factor": "sma", "params": {"period": 20}}],
    },
)
check("empty symbol: status 422", response.status_code == 422)

# ========== VALIDATION: INVALID PERIOD ==========
print("--- Validation: Invalid Period ---")
response = client.post(
    ROUTE_RESEARCH,
    json={
        "symbol": "RELIANCE.NS",
        "factor_requests": [{"factor": "sma", "params": {"period": 20}}],
        "period": "invalid",
    },
)
check("invalid period: status 400", response.status_code == 400)
data = response.json()
check("invalid period: error message", "period" in data["detail"].lower())

# ========== VALIDATION: INVALID INTERVAL ==========
print("--- Validation: Invalid Interval ---")
response = client.post(
    ROUTE_RESEARCH,
    json={
        "symbol": "RELIANCE.NS",
        "factor_requests": [{"factor": "sma", "params": {"period": 20}}],
        "interval": "invalid",
    },
)
check("invalid interval: status 400", response.status_code == 400)
data = response.json()
check("invalid interval: error message", "interval" in data["detail"].lower())

# ========== VALIDATION: EMPTY FACTOR LIST ==========
print("--- Validation: Empty Factor List ---")
response = client.post(
    ROUTE_RESEARCH,
    json={
        "symbol": "RELIANCE.NS",
        "factor_requests": [],
    },
)
check("empty factors: status 422", response.status_code == 422)

# ========== VALIDATION: MISSING FACTOR FIELD ==========
print("--- Validation: Missing Factor Field ---")
response = client.post(
    ROUTE_RESEARCH,
    json={
        "symbol": "RELIANCE.NS",
        "factor_requests": [{"params": {"period": 20}}],
    },
)
check("missing factor: status 422", response.status_code == 422)

# ========== VALIDATION: MISSING SYMBOL ==========
print("--- Validation: Missing Symbol ---")
response = client.post(
    ROUTE_RESEARCH,
    json={
        "factor_requests": [{"factor": "sma", "params": {"period": 20}}],
    },
)
check("missing symbol: status 422", response.status_code == 422)

# ========== VALIDATION: MISSING FACTOR_REQUESTS ==========
print("--- Validation: Missing factor_requests ---")
response = client.post(
    ROUTE_RESEARCH,
    json={
        "symbol": "RELIANCE.NS",
    },
)
check("missing factor_requests: status 422", response.status_code == 422)

# ========== UNKNOWN FACTOR ==========
print("--- Unknown Factor ---")
unknown_result = make_fake_result(
    factor_results={},
    errors=[EngineError(factor="unknown", message="Factor 'unknown' not found. Available: sma")],
)
with mock_research_service(unknown_result):
    response = client.post(
        ROUTE_RESEARCH,
        json={
            "symbol": "RELIANCE.NS",
            "factor_requests": [{"factor": "unknown", "params": {}}],
        },
    )
check("unknown: status 200", response.status_code == 200)
data = response.json()
check("unknown: 1 error", len(data["errors"]) == 1)
check("unknown: error about not found", "not found" in data["errors"][0]["message"])

# ========== INTERNAL SERVICE FAILURE ==========
print("--- Internal Service Failure ---")
mock_service_fail = MagicMock()
mock_service_fail.analyze.side_effect = Exception("yfinance connection lost")
with patch("backend.api.research.ResearchService", return_value=mock_service_fail):
    response = client.post(
        ROUTE_RESEARCH,
        json={
            "symbol": "RELIANCE.NS",
            "factor_requests": [{"factor": "sma", "params": {"period": 20}}],
        },
    )
check("internal fail: status 500", response.status_code == 500)
data = response.json()
check("internal fail: detail present", "detail" in data)
check("internal fail: no stack trace", "traceback" not in str(data).lower())

# ========== OPENAPI GENERATION ==========
print("--- OpenAPI Generation ---")
openapi = app.openapi()
check("openapi: paths exist", "/api/v1/research" in openapi.get("paths", {}))
check("openapi: health exists", "/api/v1/research/health" in openapi.get("paths", {}))
check("openapi: post method", "post" in openapi["paths"]["/api/v1/research"])
check("openapi: get method", "get" in openapi["paths"]["/api/v1/research/health"])
check("openapi: components exist", "components" in openapi)
check("openapi: ResearchRequest schema", "ResearchRequest" in openapi["components"].get("schemas", {}))
check("openapi: ResearchResponse schema", "ResearchResponse" in openapi["components"].get("schemas", {}))
check("openapi: HealthResponse schema", "HealthResponse" in openapi["components"].get("schemas", {}))

# ========== RESPONSE MODEL COMPLETENESS ==========
print("--- Response Model Completeness ---")
with mock_research_service(fake_result):
    response = client.post(
        ROUTE_RESEARCH,
        json={
            "symbol": "RELIANCE.NS",
            "factor_requests": [{"factor": "sma", "params": {"period": 20}}],
        },
    )
data = response.json()
check("model: success field", "success" in data)
check("model: symbol field", "symbol" in data)
check("model: generated_at field", "generated_at" in data)
check("model: factor_results field", "factor_results" in data)
check("model: errors field", "errors" in data)
check("model: execution_time_ms field", "execution_time_ms" in data)
check("model: metadata field", "metadata" in data)

# ========== FACTOR RESULT MODEL ==========
print("--- Factor Result Model ---")
with mock_research_service(fake_result):
    response = client.post(
        ROUTE_RESEARCH,
        json={
            "symbol": "RELIANCE.NS",
            "factor_requests": [{"factor": "sma", "params": {"period": 20}}],
        },
    )
data = response.json()
sma = data["factor_results"]["SMA20"]
check("factor result: factor_name", "factor_name" in sma)
check("factor result: factor_category", "factor_category" in sma)
check("factor result: symbol", "symbol" in sma)
check("factor result: value", "value" in sma)
check("factor result: signal", "signal" in sma)
check("factor result: as_of", "as_of" in sma)
check("factor result: confidence", "confidence" in sma)
check("factor result: metadata", "metadata" in sma)

# ========== SUMMARY ==========
print("")
total = passed + failed
print("=" * 50)
print(f"RESULT: {passed}/{total} passed")
if failed == 0:
    print("ALL TESTS PASSED")
else:
    print(f"FAILURES: {failed}")
print("=" * 50)
