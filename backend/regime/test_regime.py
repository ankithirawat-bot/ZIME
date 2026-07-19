"""
Sprint 13: Market Regime Engine — Full Verification Suite.

All tests use mock MarketSnapshot objects. No internet, no yfinance.
"""

from __future__ import annotations

from backend.regime.models import (
    BreadthData,
    IndexData,
    MarketRegime,
    MarketSnapshot,
    Regime,
)
from backend.regime.regime_engine import analyze_regime

print("=== Sprint 13: Market Regime Engine Verification ===")
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


def make_index(
    name: str = "Nifty 50",
    price: float = 20000.0,
    ema20: float | None = 19500.0,
    ema50: float | None = 19000.0,
    sma200: float | None = 18000.0,
    rsi14: float | None = 60.0,
    macd_bullish: bool | None = True,
) -> IndexData:
    """Create an IndexData for testing."""
    return IndexData(
        name=name,
        current_price=price,
        ema20=ema20,
        ema50=ema50,
        sma200=sma200,
        rsi14=rsi14,
        macd_bullish=macd_bullish,
    )


def make_breadth(
    above_50dma: float | None = 65.0,
    above_200dma: float | None = 55.0,
) -> BreadthData:
    """Create a BreadthData for testing."""
    return BreadthData(
        percent_above_50dma=above_50dma,
        percent_above_200dma=above_200dma,
    )


def make_snapshot(
    nifty_price: float = 20000.0,
    nifty_ema20: float | None = 19500.0,
    nifty_ema50: float | None = 19000.0,
    nifty_sma200: float | None = 18000.0,
    nifty_rsi: float | None = 60.0,
    nifty_macd: bool | None = True,
    midcap_price: float = 30000.0,
    midcap_sma200: float | None = 28000.0,
    smallcap_price: float = 15000.0,
    smallcap_sma200: float | None = 14000.0,
    breadth_50dma: float | None = 65.0,
    breadth_200dma: float | None = 55.0,
    vix: float | None = 14.0,
) -> MarketSnapshot:
    """Create a MarketSnapshot for testing."""
    return MarketSnapshot(
        nifty50=make_index("Nifty 50", nifty_price, nifty_ema20, nifty_ema50, nifty_sma200, nifty_rsi, nifty_macd),
        nifty_midcap=make_index("Nifty Midcap 150", midcap_price, sma200=midcap_sma200),
        nifty_smallcap=make_index("Nifty Smallcap 250", smallcap_price, sma200=smallcap_sma200),
        breadth=make_breadth(breadth_50dma, breadth_200dma),
        india_vix=vix,
    )


# ========== MODELS ==========
print("--- Models ---")
idx = IndexData(name="Test", current_price=100.0)
check("IndexData: name", idx.name == "Test")
check("IndexData: price", idx.current_price == 100.0)

bd = BreadthData(percent_above_50dma=65.0)
check("BreadthData: 50dma", bd.percent_above_50dma == 65.0)

snap = MarketSnapshot(
    nifty50=make_index("Nifty 50"),
    nifty_midcap=make_index("Midcap"),
    nifty_smallcap=make_index("Smallcap"),
    breadth=make_breadth(),
)
check("MarketSnapshot: nifty50", snap.nifty50.name == "Nifty 50")

regime = MarketRegime(
    regime=Regime.BULL, confidence=80.0, score=80.0,
    reasons=["test"], warnings=[],
)
check("MarketRegime: regime", regime.regime == Regime.BULL)
check("MarketRegime: confidence", regime.confidence == 80.0)

# ========== STRONG BULL ==========
print("--- Strong Bull ---")
snapshot = make_snapshot(
    nifty_price=22000, nifty_sma200=18000, nifty_ema20=21000, nifty_ema50=20000,
    nifty_rsi=65, nifty_macd=True,
    midcap_price=32000, midcap_sma200=28000,
    smallcap_price=16000, smallcap_sma200=14000,
    breadth_50dma=75, breadth_200dma=60,
    vix=12,
)
result = analyze_regime(snapshot)
check("strong bull: regime", result.regime == Regime.STRONG_BULL)
check("strong bull: score >= 90", result.score >= 90)
check("strong bull: confidence > 0", result.confidence > 0)
check("strong bull: has reasons", len(result.reasons) > 0)
check("strong bull: no warnings", len(result.warnings) == 0)

# ========== BULL ==========
print("--- Bull ---")
snapshot = make_snapshot(
    nifty_price=21000, nifty_sma200=19000, nifty_ema20=20500, nifty_ema50=20000,
    nifty_rsi=52, nifty_macd=True,
    midcap_price=31000, midcap_sma200=29000,
    smallcap_price=15500, smallcap_sma200=14500,
    breadth_50dma=65, breadth_200dma=52,
    vix=18,
)
result = analyze_regime(snapshot)
check("bull: regime", result.regime == Regime.BULL)
check("bull: 75 <= score < 90", 75 <= result.score < 90)

# ========== NEUTRAL ==========
print("--- Neutral ---")
snapshot = make_snapshot(
    nifty_price=20000, nifty_sma200=19500, nifty_ema20=19800, nifty_ema50=19600,
    nifty_rsi=50, nifty_macd=False,
    midcap_price=29000, midcap_sma200=28500,
    smallcap_price=14500, smallcap_sma200=14200,
    breadth_50dma=62, breadth_200dma=45,
    vix=18,
)
result = analyze_regime(snapshot)
check("neutral: regime", result.regime == Regime.NEUTRAL)
check("neutral: 55 <= score < 75", 55 <= result.score < 75)

# ========== WEAK ==========
print("--- Weak ---")
snapshot = make_snapshot(
    nifty_price=19000, nifty_sma200=19500, nifty_ema20=18500, nifty_ema50=18000,
    nifty_rsi=48, nifty_macd=False,
    midcap_price=29000, midcap_sma200=28500,
    smallcap_price=14500, smallcap_sma200=14200,
    breadth_50dma=62, breadth_200dma=35,
    vix=20,
)
result = analyze_regime(snapshot)
check("weak: regime", result.regime == Regime.WEAK)
check("weak: 35 <= score < 55", 35 <= result.score < 55)

# ========== BEAR ==========
print("--- Bear ---")
snapshot = make_snapshot(
    nifty_price=17000, nifty_sma200=20000, nifty_ema20=18000, nifty_ema50=19000,
    nifty_rsi=30, nifty_macd=False,
    midcap_price=24000, midcap_sma200=29000,
    smallcap_price=12000, smallcap_sma200=15000,
    breadth_50dma=20, breadth_200dma=15,
    vix=30,
)
result = analyze_regime(snapshot)
check("bear: regime", result.regime == Regime.BEAR)
check("bear: score < 35", result.score < 35)

# ========== MISSING DATA ==========
print("--- Missing Data ---")
snapshot = MarketSnapshot(
    nifty50=IndexData(name="Nifty 50", current_price=20000),
    nifty_midcap=IndexData(name="Midcap", current_price=30000),
    nifty_smallcap=IndexData(name="Smallcap", current_price=15000),
    breadth=BreadthData(),
)
result = analyze_regime(snapshot)
check("missing data: has warnings", len(result.warnings) > 0)
check("missing data: confidence < 100", result.confidence < 100)
check("missing data: still classifies", result.regime in Regime)

# ========== MISSING BREADTH ==========
print("--- Missing Breadth ---")
snapshot = make_snapshot(breadth_50dma=None, breadth_200dma=None)
result = analyze_regime(snapshot)
check("missing breadth: has warning", any("breadth" in w.lower() for w in result.warnings))

# ========== MISSING VIX ==========
print("--- Missing VIX ---")
snapshot = make_snapshot(vix=None)
result = analyze_regime(snapshot)
check("missing vix: has warning", any("vix" in w.lower() for w in result.warnings))

# ========== CONFIDENCE CALCULATION ==========
print("--- Confidence Calculation ---")
# Full data
snapshot = make_snapshot()
result = analyze_regime(snapshot)
check("full data: confidence high", result.confidence >= 80)

# Missing data
snapshot = MarketSnapshot(
    nifty50=IndexData(name="Nifty 50", current_price=20000),
    nifty_midcap=IndexData(name="Midcap", current_price=30000),
    nifty_smallcap=IndexData(name="Smallcap", current_price=15000),
    breadth=BreadthData(),
)
result = analyze_regime(snapshot)
check("missing data: confidence lower", result.confidence < 80)

# ========== REASON GENERATION ==========
print("--- Reason Generation ---")
snapshot = make_snapshot()
result = analyze_regime(snapshot)
check("reasons: list type", isinstance(result.reasons, list))
check("reasons: non-empty", len(result.reasons) > 0)
check("reasons: strings", all(isinstance(r, str) for r in result.reasons))

# ========== SCORE BOUNDS ==========
print("--- Score Bounds ---")
# Maximum score scenario
snapshot = make_snapshot(
    nifty_price=22000, nifty_sma200=18000, nifty_ema20=21000, nifty_ema50=20000,
    nifty_rsi=70, nifty_macd=True,
    midcap_price=32000, midcap_sma200=28000,
    smallcap_price=16000, smallcap_sma200=14000,
    breadth_50dma=80, breadth_200dma=65,
    vix=10,
)
result = analyze_regime(snapshot)
check("max score: <= 100", result.score <= 100)
check("max score: >= 90", result.score >= 90)

# Minimum score scenario
snapshot = make_snapshot(
    nifty_price=15000, nifty_sma200=20000, nifty_ema20=16000, nifty_ema50=17000,
    nifty_rsi=25, nifty_macd=False,
    midcap_price=22000, midcap_sma200=28000,
    smallcap_price=11000, smallcap_sma200=15000,
    breadth_50dma=15, breadth_200dma=10,
    vix=35,
)
result = analyze_regime(snapshot)
check("min score: >= 0", result.score >= 0)
check("min score: < 35", result.score < 35)

# ========== REGIME ENUM ==========
print("--- Regime Enum ---")
check("Regime.STRONG_BULL", Regime.STRONG_BULL.value == "Strong Bull")
check("Regime.BULL", Regime.BULL.value == "Bull")
check("Regime.NEUTRAL", Regime.NEUTRAL.value == "Neutral")
check("Regime.WEAK", Regime.WEAK.value == "Weak")
check("Regime.BEAR", Regime.BEAR.value == "Bear")

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
