"""
Sprint 14: Relative Strength Engine — Full Verification Suite.

All tests use mock StockSnapshot objects. No internet, no yfinance.
"""

from __future__ import annotations

from backend.relative_strength.models import (
    BenchmarkData,
    Leadership,
    RelativeStrengthResult,
    StockSnapshot,
)
from backend.relative_strength.rs_engine import (
    _weighted_return,
    analyze_relative_strength,
)

print("=== Sprint 14: Relative Strength Engine Verification ===")
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


def make_stock(
    returns_1m: float | None = 5.0,
    returns_3m: float | None = 15.0,
    returns_6m: float | None = 25.0,
    returns_1y: float | None = 35.0,
) -> BenchmarkData:
    """Create stock BenchmarkData for testing."""
    return BenchmarkData(
        name="Stock",
        returns_1m=returns_1m,
        returns_3m=returns_3m,
        returns_6m=returns_6m,
        returns_1y=returns_1y,
    )


def make_market(
    returns_1m: float | None = 3.0,
    returns_3m: float | None = 10.0,
    returns_6m: float | None = 18.0,
    returns_1y: float | None = 25.0,
) -> BenchmarkData:
    """Create market benchmark for testing."""
    return BenchmarkData(
        name="Nifty 50",
        returns_1m=returns_1m,
        returns_3m=returns_3m,
        returns_6m=returns_6m,
        returns_1y=returns_1y,
    )


def make_sector(
    returns_1m: float | None = 4.0,
    returns_3m: float | None = 12.0,
    returns_6m: float | None = 20.0,
    returns_1y: float | None = 28.0,
) -> BenchmarkData:
    """Create sector benchmark for testing."""
    return BenchmarkData(
        name="Sector",
        returns_1m=returns_1m,
        returns_3m=returns_3m,
        returns_6m=returns_6m,
        returns_1y=returns_1y,
    )


def make_industry(
    returns_1m: float | None = 2.0,
    returns_3m: float | None = 8.0,
    returns_6m: float | None = 15.0,
    returns_1y: float | None = 22.0,
) -> BenchmarkData:
    """Create industry benchmark for testing."""
    return BenchmarkData(
        name="Industry",
        returns_1m=returns_1m,
        returns_3m=returns_3m,
        returns_6m=returns_6m,
        returns_1y=returns_1y,
    )


def make_snapshot(
    symbol: str = "RELIANCE.NS",
    stock_returns: tuple = (5, 15, 25, 35),
    market_returns: tuple = (3, 10, 18, 25),
    sector_returns: tuple | None = (4, 12, 20, 28),
    industry_returns: tuple | None = (2, 8, 15, 22),
    high_52w: float | None = 3000.0,
    low_52w: float | None = None,
    current_price: float | None = 2850.0,
    history_length: int | None = 250,
) -> StockSnapshot:
    """Create a StockSnapshot for testing."""
    return StockSnapshot(
        symbol=symbol,
        stock=make_stock(*stock_returns),
        market_benchmark=make_market(*market_returns),
        sector_benchmark=make_sector(*sector_returns) if sector_returns else None,
        industry_benchmark=make_industry(*industry_returns) if industry_returns else None,
        high_52w=high_52w,
        low_52w=low_52w,
        current_price=current_price,
        history_length=history_length,
    )


# ========== MODELS ==========
print("--- Models ---")
bd = BenchmarkData(name="Test", returns_1y=25.0)
check("BenchmarkData: name", bd.name == "Test")
check("BenchmarkData: returns_1y", bd.returns_1y == 25.0)

snap = StockSnapshot(symbol="TEST", stock=bd, market_benchmark=bd)
check("StockSnapshot: symbol", snap.symbol == "TEST")
check("StockSnapshot: low_52w", snap.low_52w is None)

result = RelativeStrengthResult(
    overall_score=80, market_score=25, sector_score=20, industry_score=10,
    high_score=15, momentum_score=10, leadership=Leadership.STRONG,
    confidence=90, reasons=["test"], warnings=[],
)
check("RelativeStrengthResult: overall_score", result.overall_score == 80)
check("RelativeStrengthResult: leadership", result.leadership == Leadership.STRONG)

# ========== WEIGHTED RETURNS ==========
print("--- Weighted Returns ---")
# Weights: 1M=10%, 3M=20%, 6M=30%, 12M=40%
# (5*0.1 + 15*0.2 + 25*0.3 + 35*0.4) = 0.5+3+7.5+14 = 25.0
wr = _weighted_return(BenchmarkData(name="T", returns_1m=5, returns_3m=15, returns_6m=25, returns_1y=35))
check("weighted: all periods", abs(wr - 25.0) < 0.01, str(wr))

# Only 1M and 12M: (5*0.1 + 35*0.4) / 0.5 = (0.5+14)/0.5 = 29.0
wr = _weighted_return(BenchmarkData(name="T", returns_1m=5, returns_1y=35))
check("weighted: partial periods", abs(wr - 29.0) < 0.01, str(wr))

# Only 12M: (35*0.4) / 0.4 = 35.0
wr = _weighted_return(BenchmarkData(name="T", returns_1y=35))
check("weighted: single period", abs(wr - 35.0) < 0.01, str(wr))

# No returns: None
wr = _weighted_return(BenchmarkData(name="T"))
check("weighted: no returns", wr is None)

# ========== LEADER ==========
print("--- Leader ---")
# Weighted WR: stock=43.30, market=17.70, sector=20.00, industry=15.10
# Market diff=25.60 >20% → 30pts, sector diff=23.30 >20% → 25pts,
# industry diff=28.20 >20% → 15pts, high 1.67% → 20pts, momentum 0 → 0pts = 90.00
snapshot = make_snapshot(
    stock_returns=(8, 25, 45, 60),
    market_returns=(3, 10, 18, 25),
    sector_returns=(4, 12, 20, 28),
    industry_returns=(2, 8, 15, 22),
    high_52w=3000,
    current_price=2950,
)
result = analyze_relative_strength(snapshot)
check("leader: overall_score >= 90", result.overall_score >= 90, str(result.overall_score))
check("leader: leadership", result.leadership == Leadership.LEADER)
check("leader: market_score > 0", result.market_score > 0)
check("leader: has reasons", len(result.reasons) > 0)

# ========== STRONG ==========
print("--- Strong ---")
# Weighted WR: stock=38.00, market=17.70, sector=20.00, industry=15.10
# Market diff=20.30 >20% → 30pts, sector diff=18.00 10-20% → 16.75pts,
# industry diff=22.90 >20% → 15pts, high 3.33% → 20pts, momentum accel=-37 → 0pts = 81.75
snapshot = make_snapshot(
    stock_returns=(6, 18, 30, 65),
    market_returns=(3, 10, 18, 25),
    sector_returns=(4, 12, 20, 28),
    industry_returns=(2, 8, 15, 22),
    high_52w=3000,
    current_price=2900,
)
result = analyze_relative_strength(snapshot)
check("strong: 75 <= overall_score < 90", 75 <= result.overall_score < 90, str(result.overall_score))
check("strong: leadership", result.leadership == Leadership.STRONG, result.leadership.value)

# ========== AVERAGE ==========
print("--- Average ---")
# Weighted WR: stock=27.80, market=17.70, sector=20.00, industry=15.10
# Market diff=10.10 10-20% → 20.1pts, sector diff=7.80 0-10% → 8.25pts,
# industry diff=12.70 10-20% → 10.05pts, high 3.33% → 20pts, momentum accel=-15 → 0pts = 58.40
snapshot = make_snapshot(
    stock_returns=(5, 15, 25, 42),
    market_returns=(3, 10, 18, 25),
    sector_returns=(4, 12, 20, 28),
    industry_returns=(2, 8, 15, 22),
    high_52w=3000,
    current_price=2900,
)
result = analyze_relative_strength(snapshot)
check("average: 55 <= overall_score < 75", 55 <= result.overall_score < 75, str(result.overall_score))
check("average: leadership", result.leadership == Leadership.AVERAGE, result.leadership.value)

# ========== WEAK ==========
print("--- Weak ---")
# Weighted WR: stock=20.40, market=17.70, sector=20.00, industry=15.10
# Market diff=2.70 0-10% → 9.9pts, sector diff=0.40 0-10% → 8.25pts,
# industry diff=5.30 0-10% → 4.95pts, high 6.67% → 15pts, momentum accel=-7 → 0pts = 38.10
snapshot = make_snapshot(
    stock_returns=(4, 10, 16, 33),
    market_returns=(3, 10, 18, 25),
    sector_returns=(4, 12, 20, 28),
    industry_returns=(2, 8, 15, 22),
    high_52w=3000,
    current_price=2800,
)
result = analyze_relative_strength(snapshot)
check("weak: 35 <= overall_score < 55", 35 <= result.overall_score < 55, str(result.overall_score))
check("weak: leadership", result.leadership == Leadership.WEAK, result.leadership.value)

# ========== LAGGARD ==========
print("--- Laggard ---")
snapshot = make_snapshot(
    stock_returns=(-2, -5, -10, -15),
    market_returns=(3, 10, 18, 25),
    sector_returns=(4, 12, 20, 28),
    industry_returns=(2, 8, 15, 22),
    high_52w=3000,
    current_price=2000,
)
result = analyze_relative_strength(snapshot)
check("laggard: overall_score < 35", result.overall_score < 35, str(result.overall_score))
check("laggard: leadership", result.leadership == Leadership.LAGGARD)

# ========== NEAR 52-WEEK HIGH ==========
print("--- Near 52-Week High ---")
snapshot = make_snapshot(
    stock_returns=(5, 15, 25, 35),
    market_returns=(3, 10, 18, 25),
    high_52w=3000,
    current_price=2950,
)
result = analyze_relative_strength(snapshot)
check("near high: high_score > 0", result.high_score > 0)
check("near high: reason mentions high", any("high" in r.lower() for r in result.reasons))

# ========== FAR FROM HIGH ==========
print("--- Far from High ---")
snapshot = make_snapshot(
    stock_returns=(5, 15, 25, 35),
    market_returns=(3, 10, 18, 25),
    high_52w=3000,
    current_price=2100,
)
result = analyze_relative_strength(snapshot)
check("far from high: high_score == 0", result.high_score == 0)

# ========== MARKET OUTPERFORMANCE ==========
print("--- Market Outperformance ---")
snapshot = make_snapshot(
    stock_returns=(8, 25, 45, 60),
    market_returns=(3, 10, 18, 25),
)
result = analyze_relative_strength(snapshot)
check("market outperform: market_score > 20", result.market_score > 20, str(result.market_score))
check("market outperform: reason mentions Nifty", any("nifty" in r.lower() for r in result.reasons))

# ========== SECTOR OUTPERFORMANCE ==========
print("--- Sector Outperformance ---")
snapshot = make_snapshot(
    stock_returns=(8, 25, 45, 60),
    market_returns=(3, 10, 18, 25),
    sector_returns=(4, 12, 20, 28),
)
result = analyze_relative_strength(snapshot)
check("sector outperform: sector_score > 15", result.sector_score > 15, str(result.sector_score))
check("sector outperform: reason mentions sector", any("sector" in r.lower() for r in result.reasons))

# ========== INDUSTRY OUTPERFORMANCE ==========
print("--- Industry Outperformance ---")
snapshot = make_snapshot(
    stock_returns=(8, 25, 45, 60),
    market_returns=(3, 10, 18, 25),
    industry_returns=(2, 8, 15, 22),
)
result = analyze_relative_strength(snapshot)
check("industry outperform: industry_score > 10", result.industry_score > 10, str(result.industry_score))
check("industry outperform: reason mentions industry", any("industry" in r.lower() for r in result.reasons))

# ========== MISSING BENCHMARK ==========
print("--- Missing Benchmark ---")
snapshot = make_snapshot(
    stock_returns=(5, 15, 25, 35),
    market_returns=(3, 10, 18, 25),
    sector_returns=None,
    industry_returns=None,
)
result = analyze_relative_strength(snapshot)
check("missing benchmark: has warnings", len(result.warnings) > 0)
check("missing benchmark: mentions sector", any("sector" in w.lower() for w in result.warnings))
check("missing benchmark: mentions industry", any("industry" in w.lower() for w in result.warnings))

# ========== MISSING SECTOR ==========
print("--- Missing Sector ---")
snapshot = make_snapshot(
    stock_returns=(5, 15, 25, 35),
    market_returns=(3, 10, 18, 25),
    sector_returns=None,
)
result = analyze_relative_strength(snapshot)
check("missing sector: has warning", any("sector" in w.lower() for w in result.warnings))

# ========== MISSING HISTORY ==========
print("--- Missing History ---")
snapshot = make_snapshot(
    stock_returns=(5, 15, 25, 35),
    market_returns=(3, 10, 18, 25),
    history_length=30,
)
result = analyze_relative_strength(snapshot)
check("missing history: has warning", any("history" in w.lower() for w in result.warnings))
check("missing history: confidence < 100", result.confidence < 100)

# ========== MISSING RETURNS ==========
print("--- Missing Returns ---")
snap_no_returns = StockSnapshot(
    symbol="TEST",
    stock=BenchmarkData(name="Stock"),
    market_benchmark=BenchmarkData(name="Market"),
    history_length=250,
)
result = analyze_relative_strength(snap_no_returns)
check("missing returns: has warning", any("missing returns" in w.lower() for w in result.warnings))
check("missing returns: market_score 0", result.market_score == 0)

# ========== REASON GENERATION ==========
print("--- Reason Generation ---")
snapshot = make_snapshot(
    stock_returns=(5, 15, 25, 35),
    market_returns=(3, 10, 18, 25),
)
result = analyze_relative_strength(snapshot)
check("reasons: list type", isinstance(result.reasons, list))
check("reasons: non-empty", len(result.reasons) > 0)
check("reasons: strings", all(isinstance(r, str) for r in result.reasons))

# ========== CONFIDENCE CALCULATION ==========
print("--- Confidence Calculation ---")
# Full data
snapshot = make_snapshot(
    stock_returns=(5, 15, 25, 35),
    market_returns=(3, 10, 18, 25),
    history_length=250,
)
result = analyze_relative_strength(snapshot)
check("full data: confidence high", result.confidence >= 80)

# Missing data
snapshot = make_snapshot(
    stock_returns=(5, 15, 25, 35),
    market_returns=(3, 10, 18, 25),
    sector_returns=None,
    industry_returns=None,
    history_length=30,
)
result = analyze_relative_strength(snapshot)
check("missing data: confidence lower", result.confidence < 80)

# ========== SCORE COMPONENTS ==========
print("--- Score Components ---")
snapshot = make_snapshot(
    stock_returns=(5, 15, 25, 35),
    market_returns=(3, 10, 18, 25),
    sector_returns=(4, 12, 20, 28),
    industry_returns=(2, 8, 15, 22),
    high_52w=3000,
    current_price=2850,
)
result = analyze_relative_strength(snapshot)
check("components: market_score <= 30", result.market_score <= 30)
check("components: sector_score <= 25", result.sector_score <= 25)
check("components: industry_score <= 15", result.industry_score <= 15)
check("components: high_score <= 20", result.high_score <= 20)
check("components: momentum_score <= 10", result.momentum_score <= 10)
check("components: sum matches overall", abs(
    result.market_score + result.sector_score + result.industry_score +
    result.high_score + result.momentum_score - result.overall_score
) < 0.01)

# ========== LEADERSHIP ENUM ==========
print("--- Leadership Enum ---")
check("Leadership.LEADER", Leadership.LEADER.value == "Leader")
check("Leadership.STRONG", Leadership.STRONG.value == "Strong")
check("Leadership.AVERAGE", Leadership.AVERAGE.value == "Average")
check("Leadership.WEAK", Leadership.WEAK.value == "Weak")
check("Leadership.LAGGARD", Leadership.LAGGARD.value == "Laggard")

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
