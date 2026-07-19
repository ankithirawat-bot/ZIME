"""
Sprint 12: Explainable Research Report — Full Verification Suite.

All tests use mock ResearchResult objects. No internet, no yfinance.
"""

from __future__ import annotations

from datetime import date, datetime

from backend.core.enums import FactorCategory, Signal
from backend.core.factor_result import FactorResult
from backend.engines.factor_engine import EngineError
from backend.reporting.models import DataSummary, ResearchReport, Section
from backend.reporting.report_builder import build_report
from backend.services.research_service import ResearchResult

print("=== Sprint 12: Explainable Research Report Verification ===")
print("")

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


def make_factor(
    name: str,
    value: float | None,
    signal: Signal,
    category: FactorCategory = FactorCategory.TECHNICAL,
    metadata: dict | None = None,
) -> FactorResult:
    """Create a FactorResult for testing."""
    return FactorResult(
        factor_name=name,
        factor_category=category,
        symbol="TEST",
        value=value,
        signal=signal,
        as_of=date(2025, 12, 31),
        confidence=None,
        metadata=metadata,
    )


def make_research_result(
    factors: dict[str, FactorResult] | None = None,
    errors: list[EngineError] | None = None,
    rows: int = 250,
) -> ResearchResult:
    """Create a ResearchResult for testing."""
    return ResearchResult(
        symbol="RELIANCE.NS",
        period="1y",
        interval="1d",
        generated_at=datetime(2025, 7, 19, 12, 0, 0),
        data_start=date(2025, 1, 1),
        data_end=date(2025, 12, 31),
        rows=rows,
        execution_time_ms=100.0,
        factor_results=factors or {},
        engine_errors=errors or [],
        metadata={},
    )


# ========== MODELS ==========
print("--- Models ---")
section = Section(name="Test", interpretation="test interpretation", signals=["signal1"])
check("Section: name", section.name == "Test")
check("Section: interpretation", section.interpretation == "test interpretation")
check("Section: signals", section.signals == ["signal1"])

ds = DataSummary(symbol="TEST", period="1y", interval="1d", rows=250, data_start="2025-01-01", data_end="2025-12-31")
check("DataSummary: symbol", ds.symbol == "TEST")
check("DataSummary: rows", ds.rows == 250)

report = ResearchReport(
    symbol="TEST", generated_at=datetime.now(), data_summary=ds,
    trend=section, momentum=section, volatility=section,
    warnings=[], overall_summary="test",
)
check("ResearchReport: symbol", report.symbol == "TEST")
check("ResearchReport: trend", report.trend.name == "Test")

# ========== BULLISH TREND ==========
print("--- Bullish Trend ---")
result = make_research_result(
    factors={
        "SMA20": make_factor("sma", 100.0, Signal.BULLISH, metadata={"period": 20}),
        "EMA20": make_factor("ema", 101.0, Signal.BULLISH, metadata={"period": 20}),
    }
)
report = build_report(result)
check("bullish trend: section exists", report.trend.name == "Trend")
check("bullish trend: has interpretation", len(report.trend.interpretation) > 0)
check("bullish trend: signals present", len(report.trend.signals) > 0)
check("bullish trend: mentions above", "above" in report.trend.interpretation.lower())

# ========== BEARISH TREND ==========
print("--- Bearish Trend ---")
result = make_research_result(
    factors={
        "SMA20": make_factor("sma", 90.0, Signal.BEARISH, metadata={"period": 20}),
        "EMA20": make_factor("ema", 89.0, Signal.BEARISH, metadata={"period": 20}),
    }
)
report = build_report(result)
check("bearish trend: mentions below", "below" in report.trend.interpretation.lower())

# ========== MIXED TREND ==========
print("--- Mixed Trend ---")
result = make_research_result(
    factors={
        "SMA20": make_factor("sma", 100.0, Signal.BULLISH, metadata={"period": 20}),
        "EMA20": make_factor("ema", 90.0, Signal.BEARISH, metadata={"period": 20}),
    }
)
report = build_report(result)
check("mixed trend: mentions mixed", "mixed" in report.trend.interpretation.lower())

# ========== NEUTRAL MOMENTUM ==========
print("--- Neutral Momentum ---")
result = make_research_result(
    factors={
        "RSI14": make_factor("rsi", 50.0, Signal.NEUTRAL, category=FactorCategory.MOMENTUM),
    }
)
report = build_report(result)
check("neutral momentum: section exists", report.momentum.name == "Momentum")
check("neutral momentum: mentions neutral", "neutral" in report.momentum.interpretation.lower())

# ========== OVERBOUGHT ==========
print("--- Overbought ---")
result = make_research_result(
    factors={
        "RSI14": make_factor("rsi", 75.0, Signal.BEARISH, category=FactorCategory.MOMENTUM),
    }
)
report = build_report(result)
check("overbought: mentions overbought", "overbought" in report.momentum.interpretation.lower())

# ========== OVERSOLD ==========
print("--- Oversold ---")
result = make_research_result(
    factors={
        "RSI14": make_factor("rsi", 25.0, Signal.BULLISH, category=FactorCategory.MOMENTUM),
    }
)
report = build_report(result)
check("oversold: mentions oversold", "oversold" in report.momentum.interpretation.lower())

# ========== MACD BULLISH ==========
print("--- MACD Bullish ---")
result = make_research_result(
    factors={
        "MACD": make_factor("macd", 0.5, Signal.BULLISH, category=FactorCategory.MOMENTUM,
                           metadata={"macd": 0.5, "signal": 0.3, "histogram": 0.2}),
    }
)
report = build_report(result)
check("macd bullish: mentions bullish", "bullish" in report.momentum.interpretation.lower())

# ========== MACD BEARISH ==========
print("--- MACD Bearish ---")
result = make_research_result(
    factors={
        "MACD": make_factor("macd", -0.5, Signal.BEARISH, category=FactorCategory.MOMENTUM,
                           metadata={"macd": -0.5, "signal": -0.3, "histogram": -0.2}),
    }
)
report = build_report(result)
check("macd bearish: mentions bearish", "bearish" in report.momentum.interpretation.lower())

# ========== ROC POSITIVE ==========
print("--- ROC Positive ---")
result = make_research_result(
    factors={
        "ROC12": make_factor("roc", 5.0, Signal.BULLISH, category=FactorCategory.MOMENTUM),
    }
)
report = build_report(result)
check("roc positive: mentions positive", "positive" in report.momentum.interpretation.lower())

# ========== ROC NEGATIVE ==========
print("--- ROC Negative ---")
result = make_research_result(
    factors={
        "ROC12": make_factor("roc", -3.0, Signal.BEARISH, category=FactorCategory.MOMENTUM),
    }
)
report = build_report(result)
check("roc negative: mentions negative", "negative" in report.momentum.interpretation.lower())

# ========== ATR VOLATILITY ==========
print("--- ATR Volatility ---")
result = make_research_result(
    factors={
        "ATR14": make_factor("atr", 2.5, Signal.BULLISH, metadata={"period": 14}),
    }
)
report = build_report(result)
check("atr volatility: section exists", report.volatility.name == "Volatility")
check("atr volatility: mentions elevated", "elevated" in report.volatility.interpretation.lower())

# ========== ATR STABLE ==========
print("--- ATR Stable ---")
result = make_research_result(
    factors={
        "ATR14": make_factor("atr", 1.0, Signal.NEUTRAL, metadata={"period": 14}),
    }
)
report = build_report(result)
check("atr stable: mentions normal", "normal" in report.volatility.interpretation.lower())

# ========== BOLLINGER BULLISH ==========
print("--- Bollinger Bullish ---")
result = make_research_result(
    factors={
        "BOLLINGER_BANDS20": make_factor("bollinger_bands", 100.0, Signal.BULLISH,
                                         metadata={"bandwidth": 0.05, "percent_b": 0.9}),
    }
)
report = build_report(result)
check("bollinger bullish: mentions upward", "upward" in report.volatility.interpretation.lower())

# ========== BOLLINGER BEARISH ==========
print("--- Bollinger Bearish ---")
result = make_research_result(
    factors={
        "BOLLINGER_BANDS20": make_factor("bollinger_bands", 90.0, Signal.BEARISH,
                                         metadata={"bandwidth": 0.05, "percent_b": 0.1}),
    }
)
report = build_report(result)
check("bollinger bearish: mentions downward", "downward" in report.volatility.interpretation.lower())

# ========== MISSING INDICATORS ==========
print("--- Missing Indicators ---")
result = make_research_result(
    factors={
        "SMA20": make_factor("sma", 100.0, Signal.BULLISH, metadata={"period": 20}),
    }
)
report = build_report(result)
check("missing indicators: has warnings", len(report.warnings) > 0)
check("missing indicators: mentions missing", any("missing" in w.lower() for w in report.warnings))

# ========== PARTIAL FAILURES ==========
print("--- Partial Failures ---")
result = make_research_result(
    factors={
        "SMA20": make_factor("sma", 100.0, Signal.BULLISH, metadata={"period": 20}),
    },
    errors=[EngineError(factor="rsi", message="Factor 'rsi' not found")],
)
report = build_report(result)
check("partial failures: has warnings", len(report.warnings) > 0)
check("partial failures: mentions failed factor", any("failed" in w.lower() for w in report.warnings))

# ========== INSUFFICIENT HISTORY ==========
print("--- Insufficient History ---")
result = make_research_result(rows=30)
report = build_report(result)
check("insufficient history: has warning", any("limited" in w.lower() for w in report.warnings))

# ========== OVERALL SUMMARY ==========
print("--- Overall Summary ---")
result = make_research_result(
    factors={
        "SMA20": make_factor("sma", 100.0, Signal.BULLISH, metadata={"period": 20}),
        "RSI14": make_factor("rsi", 50.0, Signal.NEUTRAL, category=FactorCategory.MOMENTUM),
        "ATR14": make_factor("atr", 1.0, Signal.NEUTRAL, metadata={"period": 14}),
    }
)
report = build_report(result)
check("overall summary: exists", len(report.overall_summary) > 0)
check("overall summary: has trend", "trend" in report.overall_summary.lower())
check("overall summary: has momentum", "momentum" in report.overall_summary.lower())
check("overall summary: has volatility", "volatility" in report.overall_summary.lower())
check("overall summary: ends with period", report.overall_summary.endswith("."))

# ========== DATA SUMMARY ==========
print("--- Data Summary ---")
check("data summary: symbol", report.data_summary.symbol == "RELIANCE.NS")
check("data summary: period", report.data_summary.period == "1y")
check("data summary: interval", report.data_summary.interval == "1d")
check("data summary: rows", report.data_summary.rows == 250)
check("data summary: data_start", report.data_summary.data_start == "2025-01-01")
check("data summary: data_end", report.data_summary.data_end == "2025-12-31")

# ========== NO DATA ==========
print("--- No Data ---")
result = make_research_result(factors={}, rows=0)
report = build_report(result)
check("no data: trend fallback", "no moving average" in report.trend.interpretation.lower())
check("no data: momentum fallback", "no momentum" in report.momentum.interpretation.lower())
check("no data: volatility fallback", "no volatility" in report.volatility.interpretation.lower())

# ========== COMPREHENSIVE ANALYSIS ==========
print("--- Comprehensive Analysis ---")
result = make_research_result(
    factors={
        "SMA20": make_factor("sma", 100.0, Signal.BULLISH, metadata={"period": 20}),
        "EMA20": make_factor("ema", 101.0, Signal.BULLISH, metadata={"period": 20}),
        "RSI14": make_factor("rsi", 65.0, Signal.NEUTRAL, category=FactorCategory.MOMENTUM),
        "MACD": make_factor("macd", 0.5, Signal.BULLISH, category=FactorCategory.MOMENTUM,
                           metadata={"macd": 0.5, "signal": 0.3, "histogram": 0.2}),
        "ATR14": make_factor("atr", 1.5, Signal.BULLISH, metadata={"period": 14}),
        "BOLLINGER_BANDS20": make_factor("bollinger_bands", 100.0, Signal.BULLISH,
                                         metadata={"bandwidth": 0.05, "percent_b": 0.8}),
    }
)
report = build_report(result)
check("comprehensive: all sections populated",
      len(report.trend.signals) > 0 and
      len(report.momentum.signals) > 0 and
      len(report.volatility.signals) > 0)
check("comprehensive: summary is concise", len(report.overall_summary) < 200)

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
