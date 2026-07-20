"""
Trade Planning Models.

Data classes for trade plan generation.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from enum import StrEnum


class EntryType(StrEnum):
    """Trade entry type."""

    BREAKOUT = "Breakout"
    PULLBACK = "Pullback"
    LIMIT = "Limit"
    MARKET = "Market"


class TradeQuality(StrEnum):
    """Trade quality classification."""

    A_PLUS = "A+"
    A = "A"
    B = "B"
    C = "C"
    D = "D"
    REJECT = "Reject"


class ExecutionStatus(StrEnum):
    """Trade execution status."""

    READY = "Ready"
    WAIT = "Wait"
    REJECT = "Reject"


@dataclass(frozen=True)
class TradeDecisionTrace:
    """Trace of how each trade decision was sourced.

    Attributes:
        entry_source:          Source of entry price (pattern.breakout_price,
                               pattern.pivot_price, or "none").
        stop_source:           Source of stop loss (pattern.stop_price,
                               pattern.entry_95pct, or "none").
        target_source:         Source of targets ("risk_multiple" or "none").
        position_size_source:  Source of position size ("composite").
        recommendation_source: Source of recommendation ("composite").
    """

    entry_source: str
    stop_source: str
    target_source: str
    position_size_source: str
    recommendation_source: str


@dataclass(frozen=True)
class TradePlan:
    """Complete trade plan.

    Attributes:
        entry_price:          Suggested entry price.
        entry_type:           Type of entry (breakout, pullback, limit, market).
        stop_loss:            Stop-loss price.
        stop_distance:        Distance from entry to stop.
        risk_percent:         Risk as percentage of entry.
        target_1:             First target (1R).
        target_2:             Second target (2R).
        target_3:             Third target (3R).
        risk_reward_ratio:    Risk/reward ratio.
        position_size:        Suggested position size (0-1.0).
        trade_quality:        Trade quality classification.
        execution_status:     Execution readiness status.
        execution_checklist:  Ordered checklist of requirements.
        confidence:           Trade confidence score (0-100).
        reasons:              Aggregated explanations.
        warnings:             Aggregated warnings.
        decision_trace:       Trace of how each decision was sourced.
        validation_flags:     Validation outcomes for the trade plan.
    """

    entry_price: float | None
    entry_type: EntryType
    stop_loss: float | None
    stop_distance: float | None
    risk_percent: float | None
    target_1: float | None
    target_2: float | None
    target_3: float | None
    risk_reward_ratio: float | None
    position_size: float
    trade_quality: TradeQuality
    execution_status: ExecutionStatus
    execution_checklist: list[str]
    confidence: float
    reasons: list[str]
    warnings: list[str]
    decision_trace: TradeDecisionTrace
    validation_flags: list[str] = field(default_factory=list)
