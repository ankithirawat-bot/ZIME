"""
Volume Intelligence Models.

Data classes for institutional-quality volume analysis.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from enum import Enum
from typing import Optional


class VolumeQuality(str, Enum):
    """Volume quality classification."""

    EXCEPTIONAL = "Exceptional"
    STRONG = "Strong"
    HEALTHY = "Healthy"
    WEAK = "Weak"
    POOR = "Poor"


@dataclass(frozen=True)
class VolumeSnapshot:
    """Input data for volume analysis.

    Attributes:
        price:                 Current price.
        volume:                Current volume.
        avg_volume_20:         20-period average volume.
        avg_volume_50:         50-period average volume.
        breakout_volume:       Volume on breakout day.
        consolidation_volume:  Average volume during consolidation.
        rvol:                  Relative volume ratio.
        accumulation_days:     Number of accumulation days.
        distribution_days:     Number of distribution days.
        close_position_percent: Close position within day range (0-100).
        trend_quality:         Trend quality score (0-100).
        atr:                   Average True Range.
    """

    price: float
    volume: float = 0.0
    avg_volume_20: Optional[float] = None
    avg_volume_50: Optional[float] = None
    breakout_volume: Optional[float] = None
    consolidation_volume: Optional[float] = None
    rvol: Optional[float] = None
    accumulation_days: Optional[int] = None
    distribution_days: Optional[int] = None
    close_position_percent: Optional[float] = None
    trend_quality: Optional[float] = None
    atr: Optional[float] = None


@dataclass(frozen=True)
class VolumeResult:
    """Result of volume analysis.

    Attributes:
        overall_score:        Overall score (0-100).
        rvol_score:           Relative volume score (0-20).
        breakout_score:       Breakout confirmation score (0-20).
        dryup_score:          Volume dry-up score (0-15).
        accumulation_score:   Accumulation score (0-20).
        distribution_score:   Distribution penalty (0-15, lower is better).
        institutional_score:  Institutional footprint score (0-10).
        volume_quality:       Volume quality classification.
        confidence:           Confidence score (0-100).
        reasons:              Deterministic explanations.
        warnings:             Warnings about data quality.
    """

    overall_score: float
    rvol_score: float
    breakout_score: float
    dryup_score: float
    accumulation_score: float
    distribution_score: float
    institutional_score: float
    volume_quality: VolumeQuality
    confidence: float
    reasons: list[str]
    warnings: list[str]
