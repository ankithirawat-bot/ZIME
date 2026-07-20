"""
Composite Decision Models.

Data classes for combined investment decision scoring.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from enum import StrEnum


class InvestmentGrade(StrEnum):
    """Investment grade classification."""

    A_PLUS = "A+"
    A = "A"
    A_MINUS = "A-"
    B_PLUS = "B+"
    B = "B"
    B_MINUS = "B-"
    C = "C"
    D = "D"
    F = "F"


class Recommendation(StrEnum):
    """Investment recommendation."""

    STRONG_BUY = "Strong Buy"
    BUY = "Buy"
    WATCHLIST = "Watchlist"
    MONITOR = "Monitor"
    AVOID = "Avoid"


@dataclass(frozen=True)
class DecisionTrace:
    """Trace of each engine's weighted contribution.

    Attributes:
        market_contribution:            Market regime weighted contribution.
        relative_strength_contribution: Relative strength weighted contribution.
        trend_contribution:             Trend quality weighted contribution.
        pattern_contribution:           Pattern weighted contribution.
        volume_contribution:            Volume weighted contribution.
    """

    market_contribution: float
    relative_strength_contribution: float
    trend_contribution: float
    pattern_contribution: float
    volume_contribution: float


@dataclass(frozen=True)
class CompositeResult:
    """Result of composite decision analysis.

    Attributes:
        overall_score:          Weighted composite score (0-100).
        market_score:           Market regime contribution (0-15).
        relative_strength_score: Relative strength contribution (0-20).
        trend_score:            Trend quality contribution (0-25).
        pattern_score:          Pattern contribution (0-20).
        volume_score:           Volume contribution (0-20).
        investment_grade:       Letter grade classification.
        recommendation:         Action recommendation.
        confidence:             Confidence score (0-100).
        position_size:          Suggested max allocation (0-1.0).
        reasons:                Aggregated explanations.
        warnings:               Aggregated warnings.
        decision_trace:         Weighted contributions from each engine.
        failed_gates:           Gating rules that changed the recommendation.
    """

    overall_score: float
    market_score: float
    relative_strength_score: float
    trend_score: float
    pattern_score: float
    volume_score: float
    investment_grade: InvestmentGrade
    recommendation: Recommendation
    confidence: float
    position_size: float
    reasons: list[str]
    warnings: list[str]
    decision_trace: DecisionTrace
    failed_gates: list[str] = field(default_factory=list)
