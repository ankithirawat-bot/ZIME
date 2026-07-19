"""
Market Regime Models.

Data classes for market regime classification.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from enum import Enum
from typing import Optional


class Regime(str, Enum):
    """Market regime classification."""

    STRONG_BULL = "Strong Bull"
    BULL = "Bull"
    NEUTRAL = "Neutral"
    WEAK = "Weak"
    BEAR = "Bear"


@dataclass(frozen=True)
class IndexData:
    """Data for a single market index.

    Attributes:
        name:           Index name (e.g. "Nifty 50").
        current_price:  Current price level.
        ema20:          20-period exponential moving average.
        ema50:          50-period exponential moving average.
        sma200:         200-period simple moving average.
        rsi14:          14-period RSI.
        macd_bullish:   Whether MACD is above signal line.
    """

    name: str
    current_price: float
    ema20: Optional[float] = None
    ema50: Optional[float] = None
    sma200: Optional[float] = None
    rsi14: Optional[float] = None
    macd_bullish: Optional[bool] = None


@dataclass(frozen=True)
class BreadthData:
    """Market breadth metrics.

    Attributes:
        percent_above_50dma:  Percentage of stocks above 50-day MA.
        percent_above_200dma: Percentage of stocks above 200-day MA.
    """

    percent_above_50dma: Optional[float] = None
    percent_above_200dma: Optional[float] = None


@dataclass(frozen=True)
class MarketSnapshot:
    """Complete market snapshot for regime analysis.

    Attributes:
        nifty50:      Nifty 50 index data.
        nifty_midcap: Nifty Midcap 150 index data.
        nifty_smallcap: Nifty Smallcap 250 index data.
        breadth:      Market breadth metrics.
        india_vix:    India VIX value (optional).
    """

    nifty50: IndexData
    nifty_midcap: IndexData
    nifty_smallcap: IndexData
    breadth: BreadthData
    india_vix: Optional[float] = None


@dataclass(frozen=True)
class MarketRegime:
    """Result of market regime analysis.

    Attributes:
        regime:     Classified market regime.
        confidence: Confidence score (0-100).
        score:      Raw score (0-100).
        reasons:    List of deterministic explanations.
        warnings:   List of warnings about missing data.
    """

    regime: Regime
    confidence: float
    score: float
    reasons: list[str]
    warnings: list[str]
