"""
Sprint 10: Market Data Provider Abstraction — Full Verification Suite.

All tests mock the provider. No internet, no yfinance, no real downloads.
"""

from __future__ import annotations

from datetime import date, datetime
from unittest.mock import MagicMock, patch

import pandas as pd
import numpy as np

from backend.providers.base import MarketDataProvider
from backend.providers.yfinance_provider import YFinanceProvider
from backend.services.research_service import (
    ResearchService,
    ResearchResult,
    REQUIRED_COLUMNS,
    VALID_PERIODS,
    VALID_INTERVALS,
)
from backend.engines.factor_engine import FactorRequest, EngineError
from backend.core.factor_result import FactorResult
from backend.core.enums import Signal

print("=== Sprint 10: Market Data Provider Abstraction Verification ===")
print("")

np.random.seed(42)
dates = pd.date_range("2025-01-01", periods=60, freq="B")
close_vals = 100.0 + np.cumsum(np.random.randn(60) * 0.5)
fake_data = pd.DataFrame({
    "Open": close_vals - 0.2,
    "High": close_vals + np.abs(np.random.randn(60) * 0.5),
    "Low": close_vals - np.abs(np.random.randn(60) * 0.3),
    "Close": close_vals,
    "Volume": [1000000.0] * 60,
}, index=dates)

passed = 0
failed = 0


def check(name: str, condition: bool, detail: str = "") -> None:
    global passed, failed
    if condition:
        passed += 1
        print("  PASS: %s" % name)
    else:
        failed += 1
        print("  FAIL: %s%s" % (name, " (%s)" % detail if detail else ""))


def make_mock_provider(data: pd.DataFrame | None = None, side_effect: Exception | None = None):
    """Create a mock MarketDataProvider."""
    mock = MagicMock(spec=MarketDataProvider)
    if side_effect:
        mock.get_history.side_effect = side_effect
    else:
        mock.get_history.return_value = data
    return mock


# ========== INTERFACE ==========
print("--- Interface ---")
check("MarketDataProvider is ABC", hasattr(MarketDataProvider, "__abstractmethods__"))
check("get_history is abstract", "get_history" in MarketDataProvider.__abstractmethods__)

# ========== YFINANCE PROVIDER ==========
print("--- YFinanceProvider ---")
check("YFinanceProvider inherits MarketDataProvider", issubclass(YFinanceProvider, MarketDataProvider))
yp = YFinanceProvider()
check("YFinanceProvider has get_history", hasattr(yp, "get_history"))

# ========== DEPENDENCY INJECTION ==========
print("--- Dependency Injection ---")
mock_prov = make_mock_provider(fake_data)
service = ResearchService(provider=mock_prov)
check("custom provider injected", service._provider is mock_prov)

default_service = ResearchService()
check("default provider is YFinanceProvider", isinstance(default_service._provider, YFinanceProvider))

# ========== SUCCESSFUL ANALYSIS ==========
print("--- Successful Analysis ---")
mock_prov = make_mock_provider(fake_data)
service = ResearchService(provider=mock_prov)
result = service.analyze(
    symbol="RELIANCE.NS",
    factor_requests=[
        FactorRequest("sma", {"period": 20}),
        FactorRequest("rsi", {"period": 14}),
    ],
    period="1y",
    interval="1d",
)
check("is ResearchResult", isinstance(result, ResearchResult))
check("symbol", result.symbol == "RELIANCE.NS")
check("rows", result.rows == 60)
check("2 factor results", len(result.factor_results) == 2)
check("0 engine errors", len(result.engine_errors) == 0)
check("SMA20 present", "SMA20" in result.factor_results)
check("RSI14 present", "RSI14" in result.factor_results)
check("provider.get_history called", mock_prov.get_history.called)
check("provider called with correct args", mock_prov.get_history.call_args.args == ("RELIANCE.NS", "1y", "1d"))

# ========== PROVIDER RETURNING NONE ==========
print("--- Provider Returns None ---")
mock_prov = make_mock_provider(None)
service = ResearchService(provider=mock_prov)
result = service.analyze(
    symbol="NONE.NS",
    factor_requests=[FactorRequest("sma", {"period": 20})],
)
check("none: rows=0", result.rows == 0)
check("none: 0 results", len(result.factor_results) == 0)
check("none: 1 error", len(result.engine_errors) == 1)
check("none: error about data", result.engine_errors[0].factor == "(data)")

# ========== PROVIDER RETURNING EMPTY ==========
print("--- Provider Returns Empty ---")
mock_prov = make_mock_provider(pd.DataFrame())
service = ResearchService(provider=mock_prov)
result = service.analyze(
    symbol="EMPTY.NS",
    factor_requests=[FactorRequest("sma", {"period": 20})],
)
check("empty: rows=0", result.rows == 0)
check("empty: 1 error", len(result.engine_errors) == 1)

# ========== PROVIDER RAISING EXCEPTION ==========
print("--- Provider Raises Exception ---")
mock_prov = make_mock_provider(side_effect=Exception("Network timeout"))
service = ResearchService(provider=mock_prov)
result = service.analyze(
    symbol="FAIL.NS",
    factor_requests=[FactorRequest("sma", {"period": 20})],
)
check("exception: rows=0", result.rows == 0)
check("exception: 1 error", len(result.engine_errors) == 1)
check("exception: error about download", result.engine_errors[0].factor == "(download)")

# ========== MISSING COLUMNS ==========
print("--- Missing Columns ---")
incomplete = pd.DataFrame({"Open": [1]*10, "Close": [1]*10})
mock_prov = make_mock_provider(incomplete)
service = ResearchService(provider=mock_prov)
result = service.analyze(
    symbol="INCOMPLETE.NS",
    factor_requests=[FactorRequest("sma", {"period": 5})],
)
check("missing cols: 0 results", len(result.factor_results) == 0)
check("missing cols: 1 error", len(result.engine_errors) == 1)

# ========== MULTIPLE FACTORS ==========
print("--- Multiple Factors ---")
mock_prov = make_mock_provider(fake_data)
service = ResearchService(provider=mock_prov)
result = service.analyze(
    symbol="MULTI.NS",
    factor_requests=[
        FactorRequest("sma", {"period": 20}),
        FactorRequest("ema", {"period": 20}),
        FactorRequest("rsi", {"period": 14}),
        FactorRequest("atr", {"period": 14}),
        FactorRequest("macd", {}),
        FactorRequest("bollinger_bands", {"period": 20}),
    ],
)
check("multi: 6 results", len(result.factor_results) == 6)
check("multi: 0 errors", len(result.engine_errors) == 0)

# ========== PARTIAL FAILURES ==========
print("--- Partial Failures ---")
mock_prov = make_mock_provider(fake_data)
service = ResearchService(provider=mock_prov)
result = service.analyze(
    symbol="PARTIAL.NS",
    factor_requests=[
        FactorRequest("sma", {"period": 20}),
        FactorRequest("nonexistent_factor", {}),
        FactorRequest("rsi", {"period": 14}),
    ],
)
check("partial: 2 results", len(result.factor_results) == 2)
check("partial: 1 error", len(result.engine_errors) == 1)

# ========== EMPTY FACTORS ==========
print("--- Empty Factors ---")
mock_prov = make_mock_provider(fake_data)
service = ResearchService(provider=mock_prov)
result = service.analyze(
    symbol="NOFACTORS.NS",
    factor_requests=[],
)
check("no factors: rows=60", result.rows == 60)
check("no factors: 0 results", len(result.factor_results) == 0)
check("no factors: 0 errors", len(result.engine_errors) == 0)

# ========== COLUMN NORMALIZATION ==========
print("--- Column Normalization ---")
mock_prov = make_mock_provider(fake_data)
service = ResearchService(provider=mock_prov)
result = service.analyze(
    symbol="COLNORM.NS",
    factor_requests=[FactorRequest("sma", {"period": 20})],
)
check("col norm: SMA computed", result.factor_results["SMA20"].value is not None)

# ========== IMMUTABILITY ==========
print("--- Immutability ---")
try:
    result.symbol = "OTHER"
    check("ResearchResult frozen", False)
except Exception:
    check("ResearchResult frozen", True)

# ========== REGRESSION ==========
print("--- Regression ---")
from backend.engines.factor_engine import FactorEngine
mock_prov = make_mock_provider(fake_data)
service = ResearchService(provider=mock_prov)
service_result = service.analyze(
    symbol="REG.NS",
    factor_requests=[FactorRequest("sma", {"period": 20})],
)
direct_data = fake_data.copy()
direct_data.columns = [c.lower() for c in direct_data.columns]
engine = FactorEngine()
direct_result = engine.calculate(data=direct_data, requests=[{"factor": "sma", "params": {"period": 20}}], symbol="REG.NS")
check("regression: service == direct", abs(
    service_result.factor_results["SMA20"].value - direct_result.results["SMA20"].value
) < 1e-10)

# ========== CONSTANTS ==========
print("--- Constants ---")
check("REQUIRED_COLUMNS", REQUIRED_COLUMNS == {"Open", "High", "Low", "Close", "Volume"})
check("VALID_PERIODS", "1y" in VALID_PERIODS)
check("VALID_INTERVALS", "1d" in VALID_INTERVALS)

# ========== METADATA ==========
print("--- Metadata ---")
mock_prov = make_mock_provider(fake_data)
service = ResearchService(provider=mock_prov)
result = service.analyze(
    symbol="META.NS",
    factor_requests=[FactorRequest("sma", {"period": 20})],
)
check("metadata is dict", isinstance(result.metadata, dict))
check("metadata empty on success", len(result.metadata) == 0)

# ========== FAKE PROVIDER (concrete implementation) ==========
print("--- FakeProvider ---")

class FakeProvider(MarketDataProvider):
    """Concrete test provider — proves interface works."""

    def __init__(self, data: pd.DataFrame) -> None:
        self._data = data

    def get_history(self, symbol: str, period: str, interval: str) -> pd.DataFrame:
        return self._data

fake = FakeProvider(fake_data)
check("FakeProvider is MarketDataProvider", isinstance(fake, MarketDataProvider))
check("FakeProvider has get_history", hasattr(fake, "get_history"))

service = ResearchService(provider=fake)
result = service.analyze(
    symbol="FAKE.NS",
    factor_requests=[
        FactorRequest("sma", {"period": 20}),
        FactorRequest("rsi", {"period": 14}),
    ],
)
check("FakeProvider: success", len(result.factor_results) == 2)
check("FakeProvider: SMA20", "SMA20" in result.factor_results)
check("FakeProvider: RSI14", "RSI14" in result.factor_results)
check("FakeProvider: value not None", result.factor_results["SMA20"].value is not None)

# ========== SUMMARY ==========
print("")
total = passed + failed
print("=" * 50)
print("RESULT: %d/%d passed" % (passed, total))
if failed == 0:
    print("ALL TESTS PASSED")
else:
    print("FAILURES: %d" % failed)
print("=" * 50)
