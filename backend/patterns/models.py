"""
Pattern Recognition Models.

Data classes for chart pattern detection and scoring.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from enum import StrEnum


class PatternType(StrEnum):
    """Detected pattern classification."""

    UNKNOWN = "Unknown"
    VCP = "VCP"
    CUP_HANDLE = "CupHandle"
    FLAT_BASE = "FlatBase"
    ASCENDING_TRIANGLE = "AscendingTriangle"
    HIGH_TIGHT_FLAG = "HighTightFlag"


@dataclass(frozen=True)
class PatternSnapshot:
    """Input data for pattern detection.

    Attributes:
        price:                  Current price.
        volume:                 Current volume.
        highs:                  Recent high prices.
        lows:                   Recent low prices.
        closes:                 Recent close prices.
        pivot_price:            Potential breakout pivot.
        high_52w:               52-week high.
        volatility:             Recent volatility measure.
        atr:                    Average True Range.
        contraction_count:      Number of volatility contractions.
        volume_dryup:           Volume dry-up ratio (lower = drier).
        breakout_volume_ratio:  Volume ratio on breakout attempts.
        trend_quality:          Trend quality score (0-100).
        relative_strength:      Relative strength score (0-100).
    """

    price: float
    volume: float = 0.0
    highs: list[float] = field(default_factory=list)
    lows: list[float] = field(default_factory=list)
    closes: list[float] = field(default_factory=list)
    pivot_price: float | None = None
    high_52w: float | None = None
    volatility: float | None = None
    atr: float | None = None
    contraction_count: int | None = None
    volume_dryup: float | None = None
    breakout_volume_ratio: float | None = None
    trend_quality: float | None = None
    relative_strength: float | None = None


@dataclass(frozen=True)
class PatternResult:
    """Result of pattern detection.

    Attributes:
        pattern_name:    Pattern type detected.
        score:           Quality score (0-100).
        confidence:      Confidence in detection (0-100).
        pivot_price:     Breakout pivot price.
        breakout_price:  Suggested entry above pivot.
        stop_price:      Suggested stop-loss.
        risk_reward:     Risk/reward ratio.
        reasons:         Deterministic explanations.
        warnings:        Warnings about pattern quality.
    """

    pattern_name: PatternType
    score: float
    confidence: float
    pivot_price: float | None = None
    breakout_price: float | None = None
    stop_price: float | None = None
    risk_reward: float | None = None
    reasons: list[str] = field(default_factory=list)
    warnings: list[str] = field(default_factory=list)
