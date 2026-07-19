"""
Relative Strength Models.

Data classes for relative strength analysis.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from enum import Enum
from typing import Optional


class Leadership(str, Enum):
    """Leadership classification."""

    LEADER = "Leader"
    STRONG = "Strong"
    AVERAGE = "Average"
    WEAK = "Weak"
    LAGGARD = "Laggard"


@dataclass(frozen=True)
class BenchmarkData:
    """Performance data for a benchmark.

    Attributes:
        name:           Benchmark name (e.g. "Nifty 50").
        returns_1m:     1-month return (%).
        returns_3m:     3-month return (%).
        returns_6m:     6-month return (%).
        returns_1y:     1-year return (%).
    """

    name: str
    returns_1m: Optional[float] = None
    returns_3m: Optional[float] = None
    returns_6m: Optional[float] = None
    returns_1y: Optional[float] = None


@dataclass(frozen=True)
class StockSnapshot:
    """Complete stock snapshot for relative strength analysis.

    Attributes:
        symbol:             Ticker symbol.
        stock:              Stock performance data.
        market_benchmark:   Market benchmark (e.g. Nifty 50).
        sector_benchmark:   Sector benchmark.
        industry_benchmark: Industry benchmark.
        high_52w:           52-week high price.
        low_52w:            52-week low price.
        current_price:      Current price.
        history_length:     Number of data points.
    """

    symbol: str
    stock: BenchmarkData
    market_benchmark: BenchmarkData
    sector_benchmark: Optional[BenchmarkData] = None
    industry_benchmark: Optional[BenchmarkData] = None
    high_52w: Optional[float] = None
    low_52w: Optional[float] = None
    current_price: Optional[float] = None
    history_length: Optional[int] = None


@dataclass(frozen=True)
class RelativeStrengthResult:
    """Result of relative strength analysis.

    Attributes:
        overall_score:   Overall score (0-100).
        market_score:    Score vs market benchmark (0-30).
        sector_score:    Score vs sector benchmark (0-25).
        industry_score:  Score vs industry benchmark (0-15).
        high_score:      Score from 52-week high distance (0-20).
        momentum_score:  Score from relative momentum (0-10).
        leadership:      Leadership classification.
        confidence:      Confidence score (0-100).
        reasons:         List of deterministic explanations.
        warnings:        List of warnings about missing data.
    """

    overall_score: float
    market_score: float
    sector_score: float
    industry_score: float
    high_score: float
    momentum_score: float
    leadership: Leadership
    confidence: float
    reasons: list[str]
    warnings: list[str]
