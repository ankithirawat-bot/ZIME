"""
Portfolio Construction Models.

Frozen dataclasses for institutional-grade portfolio construction.
"""

from __future__ import annotations

from dataclasses import dataclass
from datetime import date

from backend.risk.models import RiskManagementResult


@dataclass(frozen=True)
class PortfolioCandidate:
    """A candidate trade for portfolio consideration.

    Attributes:
        symbol:      Ticker symbol.
        risk_result: Risk management result for this trade.
    """

    symbol: str
    risk_result: RiskManagementResult


@dataclass(frozen=True)
class PortfolioInput:
    """Input to the portfolio construction engine.

    Attributes:
        candidates:       List of candidate trades.
        available_capital: Total capital available for deployment.
        evaluation_date:  Date of portfolio evaluation.
    """

    candidates: tuple[PortfolioCandidate, ...]
    available_capital: float
    evaluation_date: date


@dataclass(frozen=True)
class PortfolioSummary:
    """High-level portfolio statistics.

    Attributes:
        total_capital:         Total available capital.
        capital_deployed:      Capital allocated to approved positions.
        cash_remaining:        Unallocated capital.
        cash_percent:          Cash as percentage of total capital.
        deployment_percent:    Deployed capital as percentage of total.
        approved_positions:    Count of approved positions.
        rejected_positions:    Count of rejected positions.
        portfolio_risk:        Aggregate portfolio risk score (0-100).
        portfolio_return_score: Aggregate expected return score (0-100).
        portfolio_confidence:  Average confidence of approved positions.
        diversification_score: Concentration-adjusted score (0-100).
    """

    total_capital: float
    capital_deployed: float
    cash_remaining: float
    cash_percent: float
    deployment_percent: float
    approved_positions: int
    rejected_positions: int
    portfolio_risk: float
    portfolio_return_score: float
    portfolio_confidence: float
    diversification_score: float


@dataclass(frozen=True)
class PortfolioPosition:
    """A single position in the portfolio.

    Attributes:
        symbol:              Ticker symbol.
        rank:                Rank by priority (1 = highest).
        allocation_percent:  Allocation as percentage of total capital.
        capital_allocated:   Absolute capital allocated.
        shares:              Number of shares to buy.
        expected_risk:       Expected risk per share.
        expected_reward:     Expected reward per share.
        confidence:          Position confidence score.
        approval_reason:     Why this position was approved.
    """

    symbol: str
    rank: int
    allocation_percent: float
    capital_allocated: float
    shares: int
    expected_risk: float
    expected_reward: float
    confidence: float
    approval_reason: str


@dataclass(frozen=True)
class AllocationSummary:
    """Portfolio allocation statistics.

    Attributes:
        largest_position:   Largest allocation percentage.
        smallest_position:  Smallest allocation percentage.
        average_position:   Average allocation percentage.
        cash_percent:       Cash as percentage of total capital.
        deployment_percent: Deployed capital as percentage of total.
    """

    largest_position: float
    smallest_position: float
    average_position: float
    cash_percent: float
    deployment_percent: float


@dataclass(frozen=True)
class PortfolioDecisionTrace:
    """Trace of how portfolio decisions were sourced.

    Attributes:
        ranking_source:   How positions were ranked.
        allocation_source: How allocation was determined.
        cash_source:      How cash was managed.
        risk_source:      How portfolio risk was calculated.
        approval_source:  How positions were approved.
    """

    ranking_source: str
    allocation_source: str
    cash_source: str
    risk_source: str
    approval_source: str


@dataclass(frozen=True)
class PortfolioResult:
    """Complete portfolio construction result.

    Attributes:
        summary:          Portfolio-level statistics.
        positions:        Approved positions, ordered by rank.
        allocation:       Allocation summary statistics.
        decision_trace:   Trace of portfolio decisions.
        validation_flags: Validation outcomes.
        reasons:          Aggregated explanations.
        warnings:         Aggregated warnings.
    """

    summary: PortfolioSummary
    positions: tuple[PortfolioPosition, ...]
    allocation: AllocationSummary
    decision_trace: PortfolioDecisionTrace
    validation_flags: tuple[str, ...]
    reasons: tuple[str, ...]
    warnings: tuple[str, ...]
