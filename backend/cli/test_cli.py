"""
Sprint 11: CLI — Full Verification Suite.

All tests mock ResearchService. No internet, no yfinance, no real downloads.
"""

from __future__ import annotations

from datetime import date, datetime
from io import StringIO
from unittest.mock import MagicMock, patch

from backend.cli.main import build_parser, main, parse_factor
from backend.cli.formatter import format_error, format_result
from backend.core.enums import FactorCategory, Signal
from backend.core.factor_result import FactorResult
from backend.engines.factor_engine import EngineError, FactorRequest
from backend.services.research_service import ResearchResult

print("=== Sprint 11: CLI Verification ===")
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


def make_fake_result(
    symbol: str = "RELIANCE.NS",
    factor_results: dict | None = None,
    errors: list | None = None,
    metadata: dict | None = None,
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
    if metadata is None:
        metadata = {}

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
        metadata=metadata,
    )


def mock_research_service(result: ResearchResult):
    """Create a patch for ResearchService."""
    mock_service = MagicMock()
    mock_service.analyze.return_value = result
    return patch("backend.cli.main.ResearchService", return_value=mock_service)


# ========== PARSER ==========
print("--- Parser ---")
parser = build_parser()
check("parser created", parser is not None)

# Parse analyze command
args = parser.parse_args(["analyze", "RELIANCE.NS"])
check("parse: symbol", args.symbol == "RELIANCE.NS")
check("parse: period default", args.period == "1y")
check("parse: interval default", args.interval == "1d")
check("parse: factors default empty", args.factors == [])

# Parse with options
args = parser.parse_args([
    "analyze", "TCS.NS",
    "--period", "6mo",
    "--interval", "1h",
    "--factor", "EMA:20",
    "--factor", "RSI:14",
    "--factor", "MACD",
])
check("parse: custom symbol", args.symbol == "TCS.NS")
check("parse: custom period", args.period == "6mo")
check("parse: custom interval", args.interval == "1h")
check("parse: 3 factors", len(args.factors) == 3)
check("parse: factor EMA:20", args.factors[0] == "EMA:20")
check("parse: factor RSI:14", args.factors[1] == "RSI:14")
check("parse: factor MACD", args.factors[2] == "MACD")

# No command
args = parser.parse_args([])
check("parse: no command", args.command is None)

# ========== PARSE FACTOR ==========
print("--- Parse Factor ---")
fr = parse_factor("EMA:20")
check("parse_factor: EMA:20 name", fr.factor == "ema")
check("parse_factor: EMA:20 period", fr.params["period"] == 20)

fr = parse_factor("RSI:14")
check("parse_factor: RSI:14 name", fr.factor == "rsi")
check("parse_factor: RSI:14 period", fr.params["period"] == 14)

fr = parse_factor("MACD")
check("parse_factor: MACD name", fr.factor == "macd")
check("parse_factor: MACD no params", fr.params == {})

fr = parse_factor("ATR:14")
check("parse_factor: ATR:14 name", fr.factor == "atr")
check("parse_factor: ATR:14 period", fr.params["period"] == 14)

# Float param
fr = parse_factor("BB:2.5")
check("parse_factor: BB:2.5 float", fr.params["period"] == 2.5)

# Invalid formats
try:
    parse_factor("")
    check("parse_factor: empty raises", False)
except ValueError:
    check("parse_factor: empty raises", True)

try:
    parse_factor("EMA:")
    check("parse_factor: empty param raises", False)
except ValueError:
    check("parse_factor: empty param raises", True)

try:
    parse_factor("EMA:abc")
    check("parse_factor: non-numeric raises", False)
except ValueError:
    check("parse_factor: non-numeric raises", True)

try:
    parse_factor("EMA:1:2")
    check("parse_factor: too many colons raises", False)
except ValueError:
    check("parse_factor: too many colons raises", True)

try:
    parse_factor(":20")
    check("parse_factor: empty name raises", False)
except ValueError:
    check("parse_factor: empty name raises", True)

# ========== SUCCESSFUL ANALYSIS ==========
print("--- Successful Analysis ---")
fake_result = make_fake_result()
with mock_research_service(fake_result):
    exit_code = main(["analyze", "RELIANCE.NS"])
check("success: exit code 0", exit_code == 0)

# ========== MULTIPLE FACTORS ==========
print("--- Multiple Factors ---")
multi_result = make_fake_result(
    factor_results={
        "EMA20": FactorResult(
            factor_name="ema", factor_category=FactorCategory.TECHNICAL,
            symbol="RELIANCE.NS", value=96.0, signal=Signal.BULLISH,
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
    exit_code = main(["analyze", "RELIANCE.NS", "--factor", "EMA:20", "--factor", "RSI:14"])
check("multi: exit code 0", exit_code == 0)

# ========== WITH ERRORS ==========
print("--- With Errors ---")
error_result = make_fake_result(
    factor_results={},
    errors=[EngineError(factor="sma", message="Factor 'sma' not found")],
)
with mock_research_service(error_result):
    exit_code = main(["analyze", "INVALID.NS", "--factor", "sma"])
check("errors: exit code 0", exit_code == 0)

# ========== EMPTY RESULTS ==========
print("--- Empty Results ---")
empty_result = make_fake_result(factor_results={})
with mock_research_service(empty_result):
    exit_code = main(["analyze", "EMPTY.NS"])
check("empty: exit code 0", exit_code == 0)

# ========== HELP COMMAND ==========
print("--- Help Command ---")
try:
    main(["--help"])
    check("help: exit code 0", True)
except SystemExit as e:
    check("help: exit code 0", e.code == 0)

try:
    main(["analyze", "--help"])
    check("analyze help: exit code 0", True)
except SystemExit as e:
    check("analyze help: exit code 0", e.code == 0)

# ========== NO COMMAND ==========
print("--- No Command ---")
exit_code = main([])
check("no command: exit code 0", exit_code == 0)

# ========== PROVIDER FAILURE ==========
print("--- Provider Failure ---")
provider_error = make_fake_result(
    factor_results={},
    errors=[EngineError(factor="(download)", message="Download failed: Network timeout")],
)
with mock_research_service(provider_error):
    exit_code = main(["analyze", "FAIL.NS", "--factor", "sma:20"])
check("provider fail: exit code 0", exit_code == 0)

# ========== INVALID ARGUMENTS ==========
print("--- Invalid Arguments ---")
# Unknown factor format (will be caught by parse_factor)
exit_code = main(["analyze", "TEST.NS", "--factor", ""])
check("invalid factor: exit code 1", exit_code == 1)

# ========== FORMATTER ==========
print("--- Formatter ---")
result_str = format_result(fake_result)
check("formatter: has symbol", "RELIANCE.NS" in result_str)
check("formatter: has period", "1y" in result_str)
check("formatter: has interval", "1d" in result_str)
check("formatter: has rows", "250" in result_str)
check("formatter: has separator", "=" * 50 in result_str)
check("formatter: has factor label", "SMA20" in result_str)
check("formatter: has value", "95.5" in result_str)
check("formatter: has signal", "bullish" in result_str)

# Error formatting
err_str = format_error("test error")
check("format_error: has prefix", err_str.startswith("Error:"))
check("format_error: has message", "test error" in err_str)

# Formatter with errors
result_with_errors = make_fake_result(
    errors=[EngineError(factor="sma", message="not found")]
)
err_result_str = format_result(result_with_errors)
check("formatter: has error section", "Errors:" in err_result_str)
check("formatter: has error message", "not found" in err_result_str)

# Formatter with warnings
result_with_warnings = make_fake_result(
    metadata={"warnings": ["Duplicate factor 'SMA20'"]}
)
warn_result_str = format_result(result_with_warnings)
check("formatter: has warnings", "Warnings:" in warn_result_str)
check("formatter: has warning message", "Duplicate factor" in warn_result_str)

# Formatter with empty results
empty_str = format_result(make_fake_result(factor_results={}))
check("formatter: empty shows message", "No factor results" in empty_str)

# ========== FACTOR WITH METADATA ==========
print("--- Factor with Metadata ---")
meta_result = make_fake_result(
    factor_results={
        "SMA20": FactorResult(
            factor_name="sma", factor_category=FactorCategory.TECHNICAL,
            symbol="RELIANCE.NS", value=95.5, signal=Signal.BULLISH,
            as_of=date(2025, 12, 31), confidence=0.85,
            metadata={"period": 20, "source": "test"},
        )
    }
)
meta_str = format_result(meta_result)
check("formatter: has confidence", "0.85" in meta_str)
check("formatter: has metadata", "period" in meta_str)
check("formatter: has source", "source" in meta_str)

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
