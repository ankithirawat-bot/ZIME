"""
Portfolio Construction Engine.

Institutional-grade portfolio construction from approved
RiskManagementResult objects.  Stateless, deterministic, explainable.
"""

from __future__ import annotations

from backend.portfolio.models import (
    AllocationSummary,
    PortfolioCandidate,
    PortfolioDecisionTrace,
    PortfolioInput,
    PortfolioPosition,
    PortfolioResult,
    PortfolioSummary,
)
from backend.risk.models import TradeRiskGrade

# Maximum reasons/warnings
_MAX_REASONS: int = 20
_MAX_WARNINGS: int = 20

# Risk grade ranking (lower index = lower risk = better)
_RISK_GRADE_RANK: dict[TradeRiskGrade, int] = {
    TradeRiskGrade.VERY_LOW: 0,
    TradeRiskGrade.LOW: 1,
    TradeRiskGrade.MODERATE: 2,
    TradeRiskGrade.HIGH: 3,
    TradeRiskGrade.VERY_HIGH: 4,
    TradeRiskGrade.REJECT: 5,
}


class PortfolioEngine:
    """Portfolio Construction Engine.

    Constructs a portfolio from approved RiskManagementResult objects.
    """

    def evaluate(
        self,
        portfolio_input: PortfolioInput,
    ) -> PortfolioResult:
        """Evaluate and construct a portfolio.

        Args:
            portfolio_input: Portfolio construction input.

        Returns:
            PortfolioResult with constructed portfolio.
        """
        validation_flags: list[str] = []
        reasons: list[str] = []
        warnings: list[str] = []

        available_capital = portfolio_input.available_capital

        # Validate capital
        capital_valid = self._validate_capital(
            available_capital, validation_flags, warnings,
        )

        # Separate approved and rejected
        approved, rejected = self._partition_candidates(portfolio_input.candidates)

        # Rank approved candidates
        ranked = self._rank_candidates(approved)

        # Allocate capital
        positions, capital_deployed = self._allocate_capital(
            ranked, available_capital, capital_valid, warnings,
        )

        # Calculate cash
        cash_remaining = available_capital - capital_deployed
        cash_percent = (cash_remaining / available_capital * 100) if available_capital > 0 else 0.0
        deployment_percent = (capital_deployed / available_capital * 100) if available_capital > 0 else 0.0

        # Build allocation summary
        allocation = self._build_allocation_summary(
            positions, cash_percent, deployment_percent,
        )

        # Calculate portfolio scores
        portfolio_risk = self._calculate_portfolio_risk(positions)
        portfolio_return_score = self._calculate_portfolio_return(positions)
        portfolio_confidence = self._calculate_portfolio_confidence(positions)
        diversification_score = self._calculate_diversification(positions, available_capital)

        # Build summary
        summary = PortfolioSummary(
            total_capital=available_capital,
            capital_deployed=round(capital_deployed, 2),
            cash_remaining=round(cash_remaining, 2),
            cash_percent=round(cash_percent, 2),
            deployment_percent=round(deployment_percent, 2),
            approved_positions=len(positions),
            rejected_positions=len(rejected),
            portfolio_risk=round(portfolio_risk, 2),
            portfolio_return_score=round(portfolio_return_score, 2),
            portfolio_confidence=round(portfolio_confidence, 2),
            diversification_score=round(diversification_score, 2),
        )

        # Decision trace
        decision_trace = PortfolioDecisionTrace(
            ranking_source="composite_confidence_then_risk_grade",
            allocation_source="recommended_position_size",
            cash_source="remaining_capital",
            risk_source="risk_engine",
            approval_source="execution_allowed",
        )

        # Collect reasons and warnings from candidates
        self._collect_candidate_reasons(reasons, approved)
        self._collect_candidate_warnings(warnings, approved, rejected)

        return PortfolioResult(
            summary=summary,
            positions=tuple(positions),
            allocation=allocation,
            decision_trace=decision_trace,
            validation_flags=tuple(validation_flags),
            reasons=tuple(reasons[:_MAX_REASONS]),
            warnings=tuple(warnings[:_MAX_WARNINGS]),
        )

    def _validate_capital(
        self,
        available_capital: float,
        validation_flags: list[str],
        warnings: list[str],
    ) -> bool:
        """Validate available capital. Returns True if valid."""
        if available_capital <= 0:
            validation_flags.append("INVALID_CAPITAL")
            warnings.append("Available capital must be positive")
            return False
        validation_flags.append("VALID_CAPITAL")
        return True

    def _partition_candidates(
        self,
        candidates: tuple[PortfolioCandidate, ...],
    ) -> tuple[list[PortfolioCandidate], list[PortfolioCandidate]]:
        """Separate candidates into approved and rejected lists."""
        approved: list[PortfolioCandidate] = []
        rejected: list[PortfolioCandidate] = []
        for candidate in candidates:
            if candidate.risk_result.execution_allowed:
                approved.append(candidate)
            else:
                rejected.append(candidate)
        return approved, rejected

    def _rank_candidates(
        self,
        candidates: list[PortfolioCandidate],
    ) -> list[PortfolioCandidate]:
        """Rank approved candidates by priority.

        Ranking criteria (descending priority):
            1. Composite confidence (highest first)
            2. Trade risk grade (lowest first = best)
            3. Symbol (alphabetical ascending)
        """
        def sort_key(candidate: PortfolioCandidate) -> tuple[float, int, str]:
            return (
                -candidate.risk_result.confidence,
                _RISK_GRADE_RANK.get(candidate.risk_result.trade_risk_grade, 99),
                candidate.symbol,
            )
        return sorted(candidates, key=sort_key)

    def _allocate_capital(
        self,
        ranked: list[PortfolioCandidate],
        available_capital: float,
        capital_valid: bool,
        warnings: list[str],
    ) -> tuple[list[PortfolioPosition], float]:
        """Allocate capital to ranked positions.

        Returns:
            Tuple of (positions list, total capital deployed).
        """
        positions: list[PortfolioPosition] = []
        capital_deployed = 0.0

        if not capital_valid:
            return positions, capital_deployed

        for rank, candidate in enumerate(ranked, start=1):
            result = candidate.risk_result
            symbol = candidate.symbol
            alloc_pct = result.recommended_position_size * 100
            alloc_amount = result.recommended_position_size * available_capital

            # Check if we can fund this position
            if capital_deployed + alloc_amount > available_capital:
                remaining = available_capital - capital_deployed
                if remaining <= 0:
                    warnings.append(f"Insufficient capital for {symbol}")
                    continue
                alloc_amount = remaining
                alloc_pct = (alloc_amount / available_capital) * 100 if available_capital > 0 else 0.0

            shares = result.shares_to_buy
            expected_risk = result.risk_per_share if result.risk_per_share is not None else 0.0
            expected_reward = result.capital_at_risk if result.capital_at_risk is not None else 0.0

            positions.append(PortfolioPosition(
                symbol=symbol,
                rank=rank,
                allocation_percent=round(alloc_pct, 2),
                capital_allocated=round(alloc_amount, 2),
                shares=shares,
                expected_risk=round(expected_risk, 2),
                expected_reward=round(expected_reward, 2),
                confidence=round(result.confidence, 2),
                approval_reason="Execution allowed by risk engine",
            ))

            capital_deployed += alloc_amount

        return positions, capital_deployed

    def _build_allocation_summary(
        self,
        positions: list[PortfolioPosition],
        cash_percent: float,
        deployment_percent: float,
    ) -> AllocationSummary:
        """Build allocation summary from positions."""
        if not positions:
            return AllocationSummary(
                largest_position=0.0,
                smallest_position=0.0,
                average_position=0.0,
                cash_percent=cash_percent,
                deployment_percent=deployment_percent,
            )

        allocs = [p.allocation_percent for p in positions]
        return AllocationSummary(
            largest_position=max(allocs),
            smallest_position=min(allocs),
            average_position=round(sum(allocs) / len(allocs), 2),
            cash_percent=cash_percent,
            deployment_percent=deployment_percent,
        )

    def _calculate_portfolio_risk(
        self,
        positions: list[PortfolioPosition],
    ) -> float:
        """Calculate aggregate portfolio risk score (0-100)."""
        if not positions:
            return 0.0

        total_risk = sum(p.expected_risk for p in positions)
        avg_risk = total_risk / len(positions)
        # Normalize: assume max reasonable risk per share is 20
        score = max(0.0, min(100.0, (avg_risk / 20.0) * 100.0))
        return score

    def _calculate_portfolio_return(
        self,
        positions: list[PortfolioPosition],
    ) -> float:
        """Calculate aggregate expected return score (0-100)."""
        if not positions:
            return 0.0

        total_reward = sum(p.expected_reward for p in positions)
        avg_reward = total_reward / len(positions)
        # Normalize: assume max reasonable reward per share is 20
        score = max(0.0, min(100.0, (avg_reward / 20.0) * 100.0))
        return score

    def _calculate_portfolio_confidence(
        self,
        positions: list[PortfolioPosition],
    ) -> float:
        """Calculate portfolio confidence as average of position confidences."""
        if not positions:
            return 0.0
        return sum(p.confidence for p in positions) / len(positions)

    def _calculate_diversification(
        self,
        positions: list[PortfolioPosition],
        available_capital: float,
    ) -> float:
        """Calculate diversification score (0-100).

        More concentration → lower score.
        More positions → higher score.
        """
        if not positions or available_capital <= 0:
            return 0.0

        # Herfindahl-Hirschman Index (HHI) based
        hhi = sum(
            (p.capital_allocated / available_capital) ** 2 for p in positions
        )

        # Normalize: HHI ranges from 1/n to 1
        n = len(positions)
        if n <= 1:
            return 50.0  # Single position = moderate diversification

        # Perfect diversification HHI = 1/n
        min_hhi = 1.0 / n
        # Max HHI = 1.0 (all in one)
        max_hhi = 1.0

        # Score: lower HHI = better diversification
        normalized = (hhi - min_hhi) / (max_hhi - min_hhi) if max_hhi > min_hhi else 0.0
        score = (1.0 - normalized) * 100.0
        return max(0.0, min(100.0, score))

    def _collect_candidate_reasons(
        self,
        reasons: list[str],
        approved: list[PortfolioCandidate],
    ) -> None:
        """Collect unique reasons from approved candidates."""
        for candidate in approved:
            for r in candidate.risk_result.reasons:
                if r not in reasons:
                    reasons.append(r)

    def _collect_candidate_warnings(
        self,
        warnings: list[str],
        approved: list[PortfolioCandidate],
        rejected: list[PortfolioCandidate],
    ) -> None:
        """Collect unique warnings from all candidates."""
        for candidate in approved:
            for w in candidate.risk_result.warnings:
                if w not in warnings:
                    warnings.append(w)

        for candidate in rejected:
            result = candidate.risk_result
            msg = f"Trade rejected: {candidate.symbol} ({result.rejection_reason.value})"
            if msg not in warnings:
                warnings.append(msg)
