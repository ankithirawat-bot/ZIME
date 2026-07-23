"""
Trend Quality Models.

Data classes for structural trend quality analysis.
"""

from __future__ import annotations

from dataclasses import dataclass
from enum import StrEnum


class TrendQuality(StrEnum):
    """Trend quality classification."""

    EXCEPTIONAL = "Exceptional"
    STRONG = "Strong"
    HEALTHY = "Healthy"
    WEAK = "Weak"
    BROKEN = "Broken"


class TrendStage(StrEnum):
    """Trend lifecycle stage."""

    EARLY = "Early"
    ESTABLISHED = "Established"
    EXTENDED = "Extended"
    LATE = "Late"
    BROKEN = "Broken"


@dataclass(frozen=True)
class TrendSnapshot:
    """Input data for trend quality analysis.

    Attributes:
        current_price:    Current price.
        ema20:            20-period EMA.
        ema50:            50-period EMA.
        sma150:           150-period SMA.
        sma200:           200-period SMA.
        high_52w:         52-week high price.
        low_52w:          52-week low price.
        slope_ema20:      20 EMA slope (positive = rising).
        slope_ema50:      50 EMA slope.
        slope_sma150:     150 SMA slope.
        slope_sma200:     200 SMA slope.
        higher_high_count: Number of recent higher highs.
        higher_low_count:  Number of recent higher lows.
        trend_age:        Number of bars since trend began.
        history_length:   Number of data points available.
    """

    current_price: float
    ema20: float | None = None
    ema50: float | None = None
    sma150: float | None = None
    sma200: float | None = None
    high_52w: float | None = None
    low_52w: float | None = None
    slope_ema20: float | None = None
    slope_ema50: float | None = None
    slope_sma150: float | None = None
    slope_sma200: float | None = None
    higher_high_count: int | None = None
    higher_low_count: int | None = None
    trend_age: int | None = None
    history_length: int | None = None


@dataclass(frozen=True)
class TrendResult:
    """Result of trend quality analysis.

    Attributes:
        overall_score:        Overall score (0-100).
        alignment_score:      MA alignment score (0-20).
        price_position_score: Price position score (0-15).
        slope_score:          MA slopes score (0-20).
        structure_score:      Trend structure score (0-20).
        persistence_score:    Trend persistence score (0-10).
        high_score:           52-week position score (0-15).
        trend_quality:        Trend quality classification.
        trend_stage:          Trend lifecycle stage.
        confidence:           Confidence score (0-100).
        reasons:              Deterministic explanations.
        warnings:             Warnings about missing data.
    """

    overall_score: float
    alignment_score: float
    price_position_score: float
    slope_score: float
    structure_score: float
    persistence_score: float
    high_score: float
    trend_quality: TrendQuality
    trend_stage: TrendStage
    confidence: float
    reasons: list[str]
    warnings: list[str]
