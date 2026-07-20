"""
Risk Management Models.

Data classes for capital-preserving execution planning.
"""

from __future__ import annotations

from dataclasses import dataclass
from enum import StrEnum


class ExposureStatus(StrEnum):
    """Portfolio exposure classification."""

    LOW = "Low"
    NORMAL = "Normal"
    HIGH = "High"
    EXCESSIVE = "Excessive"


class TradeRiskGrade(StrEnum):
    """Trade risk classification."""

    VERY_LOW = "Very Low"
    LOW = "Low"
    MODERATE = "Moderate"
    HIGH = "High"
    VERY_HIGH = "Very High"
    REJECT = "Reject"


class PortfolioRiskGrade(StrEnum):
    """Portfolio-level risk classification."""

    LOW = "Low"
    MODERATE = "Moderate"
    HIGH = "High"
    CRITICAL = "Critical"


class RejectionReason(StrEnum):
    """Deterministic rejection reason."""

    NONE = "None"
    TRADE_NOT_READY = "Trade Not Ready"
    INVALID_ENTRY = "Invalid Entry"
    INVALID_STOP = "Invalid Stop"
    LOW_RISK_REWARD = "Low Risk Reward"
    HIGH_EXPOSURE = "High Exposure"
    INVALID_POSITION = "Invalid Position"
    MISSING_STOP = "Missing Stop"


@dataclass(frozen=True)
class RiskDecisionTrace:
    """Trace of how each risk decision was sourced.

    Attributes:
        risk_source:      Source of max risk calculation.
        position_source:  Source of position sizing.
        exposure_source:  Source of exposure classification.
        approval_source:  Source of execution approval.
        loss_source:      Source of maximum loss calculation.
    """

    risk_source: str
    position_source: str
    exposure_source: str
    approval_source: str
    loss_source: str


@dataclass(frozen=True)
class RiskManagementResult:
    """Result of risk management analysis.

    Attributes:
        max_risk_percent:          Maximum permissible risk per trade.
        recommended_position_size: Recommended position size after risk rules.
        capital_at_risk:           Capital at risk per share (entry - stop).
        risk_per_share:            Risk per share (entry - stop).
        maximum_loss:              Maximum loss if stop is hit.
        shares_to_buy:             Number of shares to buy.
        portfolio_exposure:        Portfolio exposure percentage.
        exposure_status:           Exposure classification.
        trade_risk_grade:          Trade risk classification.
        portfolio_risk_grade:      Portfolio risk classification.
        execution_allowed:         Whether execution is permitted.
        rejection_reason:          Deterministic rejection reason.
        decision_trace:            Trace of how each decision was sourced.
        validation_flags:          Validation outcomes for the trade.
        confidence:                Risk management confidence score (0-100).
        reasons:                   Aggregated explanations.
        warnings:                  Aggregated warnings.
    """

    max_risk_percent: float
    recommended_position_size: float
    capital_at_risk: float | None
    risk_per_share: float | None
    maximum_loss: float | None
    shares_to_buy: int
    portfolio_exposure: float
    exposure_status: ExposureStatus
    trade_risk_grade: TradeRiskGrade
    portfolio_risk_grade: PortfolioRiskGrade
    execution_allowed: bool
    rejection_reason: RejectionReason
    decision_trace: RiskDecisionTrace
    validation_flags: list[str]
    confidence: float
    reasons: list[str]
    warnings: list[str]
