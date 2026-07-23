"""
Research Report Models.

Data classes for the explainable research report.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from datetime import datetime


@dataclass(frozen=True)
class Section:
    """A section of the research report.

    Attributes:
        name:        Section name (e.g. "Trend", "Momentum").
        interpretation: Human-readable interpretation.
        signals:     List of individual signal interpretations.
    """

    name: str
    interpretation: str
    signals: list[str] = field(default_factory=list)


@dataclass(frozen=True)
class DataSummary:
    """Summary of the data used for analysis.

    Attributes:
        symbol:     Ticker symbol.
        period:     Time period analyzed.
        interval:   Data interval.
        rows:       Number of data rows.
        data_start: Start date of data.
        data_end:   End date of data.
    """

    symbol: str
    period: str
    interval: str
    rows: int
    data_start: str | None
    data_end: str | None


@dataclass(frozen=True)
class ResearchReport:
    """Explainable research report generated from factor results.

    Attributes:
        symbol:           Ticker symbol.
        generated_at:     Timestamp when report was created.
        data_summary:     Summary of the data used.
        trend:            Trend analysis section.
        momentum:         Momentum analysis section.
        volatility:       Volatility analysis section.
        warnings:         List of warnings about missing/failed data.
        overall_summary:  Concise overall interpretation.
    """

    symbol: str
    generated_at: datetime
    data_summary: DataSummary
    trend: Section
    momentum: Section
    volatility: Section
    warnings: list[str]
    overall_summary: str
