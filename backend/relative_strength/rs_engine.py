"""
Relative Strength Engine.

Measures whether a stock is a true market leader by comparing
performance against benchmarks using weighted multi-timeframe returns.
Does NOT use RSI.
"""

from __future__ import annotations

from backend.relative_strength.models import (
    BenchmarkData,
    Leadership,
    RelativeStrengthResult,
    StockSnapshot,
)

# Return weights: 1M=10%, 3M=20%, 6M=30%, 12M=40%
_WEIGHT_1M = 0.10
_WEIGHT_3M = 0.20
_WEIGHT_6M = 0.30
_WEIGHT_1Y = 0.40


def analyze_relative_strength(snapshot: StockSnapshot) -> RelativeStrengthResult:
    """Analyze relative strength of a stock.

    Compares stock performance against market, sector, and industry
    benchmarks using weighted multi-timeframe returns to determine
    leadership quality.

    Args:
        snapshot: Complete stock snapshot.

    Returns:
        A RelativeStrengthResult with scores and classification.
    """
    scores: list[tuple[str, float, float, str]] = []
    warnings: list[str] = []

    # 1. Performance vs Market (30 pts)
    market_score, market_reason = _score_vs_benchmark(
        snapshot.stock, snapshot.market_benchmark, "Nifty", 30
    )
    scores.append(("market", market_score, 30, market_reason))

    # 2. Performance vs Sector (25 pts)
    if snapshot.sector_benchmark is not None:
        sector_score, sector_reason = _score_vs_benchmark(
            snapshot.stock, snapshot.sector_benchmark, "sector", 25
        )
        scores.append(("sector", sector_score, 25, sector_reason))
    else:
        warnings.append("Missing sector benchmark data")

    # 3. Performance vs Industry (15 pts)
    if snapshot.industry_benchmark is not None:
        industry_score, industry_reason = _score_vs_benchmark(
            snapshot.stock, snapshot.industry_benchmark, "industry", 15
        )
        scores.append(("industry", industry_score, 15, industry_reason))
    else:
        warnings.append("Missing industry benchmark data")

    # 4. Distance from 52-week High (20 pts)
    high_score, high_reason = _score_distance_from_high(
        snapshot.current_price, snapshot.high_52w, 20
    )
    scores.append(("high", high_score, 20, high_reason))

    # 5. Relative Momentum (10 pts)
    momentum_score, momentum_reason = _score_relative_momentum(
        snapshot.stock, snapshot.market_benchmark, 10
    )
    scores.append(("momentum", momentum_score, 10, momentum_reason))

    # Check for insufficient history
    if snapshot.history_length is not None and snapshot.history_length < 50:
        warnings.append(f"Insufficient history: only {snapshot.history_length} data points")

    # Check for missing returns
    missing = _check_missing_returns(snapshot)
    warnings.extend(missing)

    # Calculate overall score
    overall_score = sum(s[1] for s in scores)
    overall_score = max(0.0, min(100.0, overall_score))

    # Classify leadership
    leadership = _classify_leadership(overall_score)

    # Generate reasons
    reasons = [s[3] for s in scores if s[3]]

    # Calculate confidence
    confidence = _calculate_confidence(snapshot, warnings)

    # Extract individual scores
    market_val = market_score
    sector_val = scores[1][1] if len(scores) > 1 and scores[1][0] == "sector" else 0
    industry_val = scores[2][1] if len(scores) > 2 and scores[2][0] == "industry" else 0

    return RelativeStrengthResult(
        overall_score=overall_score,
        market_score=market_val,
        sector_score=sector_val,
        industry_score=industry_val,
        high_score=high_score,
        momentum_score=momentum_score,
        leadership=leadership,
        confidence=confidence,
        reasons=reasons,
        warnings=warnings,
    )


def _weighted_return(data: BenchmarkData) -> float | None:
    """Calculate weighted return across available timeframes.

    Weights: 1M=10%, 3M=20%, 6M=30%, 12M=40%.
    Only available periods contribute. Normalized by total weight
    of available periods.

    Args:
        data: Benchmark data with returns.

    Returns:
        Weighted return or None if no returns available.
    """
    returns: list[tuple[float, float]] = []

    if data.returns_1m is not None:
        returns.append((data.returns_1m, _WEIGHT_1M))
    if data.returns_3m is not None:
        returns.append((data.returns_3m, _WEIGHT_3M))
    if data.returns_6m is not None:
        returns.append((data.returns_6m, _WEIGHT_6M))
    if data.returns_1y is not None:
        returns.append((data.returns_1y, _WEIGHT_1Y))

    if not returns:
        return None

    total_weight = sum(w for _, w in returns)
    if total_weight == 0:
        return None

    weighted_sum = sum(r * w for r, w in returns)
    return weighted_sum / total_weight


def _score_vs_benchmark(
    stock: BenchmarkData,
    benchmark: BenchmarkData,
    name: str,
    max_points: int,
) -> tuple[float, str]:
    """Score stock performance vs a benchmark using weighted returns.

    Rules:
    - Outperformed by >20%: max_points
    - Outperformed by 10-20%: max_points * 0.67
    - Outperformed by 0-10%: max_points * 0.33
    - Underperformed: 0

    Args:
        stock:      Stock performance data.
        benchmark:  Benchmark performance data.
        name:       Benchmark name for reasons.
        max_points: Maximum score for this comparison.

    Returns:
        Tuple of (score, reason).
    """
    stock_return = _weighted_return(stock)
    bench_return = _weighted_return(benchmark)

    if stock_return is None or bench_return is None:
        return 0, ""

    outperformance = stock_return - bench_return

    if outperformance > 20:
        return max_points, f"Outperforming {name} by {outperformance:.1f}%"
    elif outperformance > 10:
        return max_points * 0.67, f"Outperforming {name} by {outperformance:.1f}%"
    elif outperformance > 0:
        return max_points * 0.33, f"Slightly outperforming {name}"
    else:
        return 0, f"Underperforming {name} by {abs(outperformance):.1f}%"


def _score_distance_from_high(
    current_price: float | None,
    high_52w: float | None,
    max_points: int,
) -> tuple[float, str]:
    """Score based on distance from 52-week high.

    Rules:
    - Within 5%: max_points
    - Within 10%: max_points * 0.75
    - Within 20%: max_points * 0.5
    - Otherwise: 0

    Args:
        current_price: Current price.
        high_52w:      52-week high.
        max_points:    Maximum score.

    Returns:
        Tuple of (score, reason).
    """
    if current_price is None or high_52w is None or high_52w == 0:
        return 0, ""

    distance_pct = ((high_52w - current_price) / high_52w) * 100

    if distance_pct <= 5:
        return max_points, f"Trading within {distance_pct:.1f}% of 52-week high"
    elif distance_pct <= 10:
        return max_points * 0.75, f"Trading {distance_pct:.1f}% below 52-week high"
    elif distance_pct <= 20:
        return max_points * 0.5, f"Trading {distance_pct:.1f}% below 52-week high"
    else:
        return 0, f"Trading {distance_pct:.1f}% below 52-week high"


def _score_relative_momentum(
    stock: BenchmarkData,
    market: BenchmarkData,
    max_points: int,
) -> tuple[float, str]:
    """Score relative momentum (acceleration).

    Compares short-term vs long-term relative performance.
    If stock is accelerating vs market, it's gaining leadership.

    Args:
        stock:  Stock performance data.
        market: Market benchmark data.
        max_points: Maximum score.

    Returns:
        Tuple of (score, reason).
    """
    stock_1m = stock.returns_1m
    stock_1y = stock.returns_1y
    market_1m = market.returns_1m
    market_1y = market.returns_1y

    if any(v is None for v in [stock_1m, stock_1y, market_1m, market_1y]):
        return 0, ""

    # Relative short-term performance
    relative_1m = stock_1m - market_1m
    # Relative long-term performance
    relative_1y = stock_1y - market_1y

    # Acceleration = relative_1m - relative_1y
    acceleration = relative_1m - relative_1y

    if acceleration > 5:
        return max_points, "Relative momentum improving"
    elif acceleration > -5:
        return max_points * 0.5, "Relative momentum stable"
    else:
        return 0, "Relative momentum weakening"


def _classify_leadership(score: float) -> Leadership:
    """Classify leadership based on score.

    Rules:
    - 90+: Leader
    - 75-89: Strong
    - 55-74: Average
    - 35-54: Weak
    - Below 35: Laggard

    Args:
        score: Overall score (0-100).

    Returns:
        Leadership classification.
    """
    if score >= 90:
        return Leadership.LEADER
    elif score >= 75:
        return Leadership.STRONG
    elif score >= 55:
        return Leadership.AVERAGE
    elif score >= 35:
        return Leadership.WEAK
    else:
        return Leadership.LAGGARD


def _check_missing_returns(snapshot: StockSnapshot) -> list[str]:
    """Check for missing return data and generate warnings.

    Args:
        snapshot: Stock snapshot.

    Returns:
        List of warning strings.
    """
    warnings: list[str] = []

    if snapshot.stock.returns_1m is None and snapshot.stock.returns_1y is None:
        warnings.append("Missing returns: stock has no return data")

    if snapshot.market_benchmark.returns_1m is None and snapshot.market_benchmark.returns_1y is None:
        warnings.append("Missing returns: market has no return data")

    return warnings


def _calculate_confidence(
    snapshot: StockSnapshot,
    warnings: list[str],
) -> float:
    """Calculate confidence based on data completeness.

    Start at 100. Reduce for every missing data component.
    Never return confidence greater than data quality.

    Args:
        snapshot: Stock snapshot.
        warnings: List of warnings.

    Returns:
        Confidence score (0-100).
    """
    confidence = 100.0

    # Deduct for missing data
    confidence -= len(warnings) * 5.0

    # Deduct for insufficient history
    if snapshot.history_length is not None and snapshot.history_length < 100:
        confidence -= 10.0

    return max(0.0, min(100.0, confidence))
