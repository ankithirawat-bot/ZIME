"""Sizing optimizer.

Optimizes position allocations against constraints, risk budgets,
and portfolio-level targets.
"""

from __future__ import annotations

import math

from backend.sizing.models import (
    AllocationResult,
    PositionRequest,
    PositionSizing,
    RiskBudget,
    SizingConfig,
)


class SizingOptimizer:
    """Portfolio sizing optimizer.

    Applies constraints, respects available cash, and scales allocations
    to meet portfolio-level targets. Designed for future optimization algorithms.
    """

    def optimize(
        self,
        sizings: tuple[PositionSizing, ...],
        config: SizingConfig,
        available_cash: float,
    ) -> AllocationResult:
        """Optimize a set of position sizings into an allocation.

        Args:
            sizings:        Position sizing results.
            config:         Sizing configuration.
            available_cash: Available cash for allocation.

        Returns:
            AllocationResult with optimized positions.
        """
        if not sizings:
            return AllocationResult(
                cash_remaining=available_cash,
                cash_reserve=available_cash * config.cash_reserve,
            )

        total_value = sum(s.value for s in sizings)
        total_exposure = total_value / config.default_account_size if config.default_account_size > 0 else 0.0

        if total_exposure > config.max_portfolio_exposure:
            scale = config.max_portfolio_exposure / total_exposure if total_exposure > 0 else 1.0
            sizings = self._scale_sizings(sizings, scale, config)
            total_value = sum(s.value for s in sizings)
            total_exposure = total_value / config.default_account_size if config.default_account_size > 0 else 0.0

        if total_value > available_cash:
            scale = available_cash / total_value if total_value > 0 else 1.0
            sizings = self._scale_sizings(sizings, scale, config)
            total_value = sum(s.value for s in sizings)
            total_exposure = total_value / config.default_account_size if config.default_account_size > 0 else 0.0

        sizings = self._apply_constraint_resizing(sizings, config)
        total_value = sum(s.value for s in sizings)
        total_exposure = total_value / config.default_account_size if config.default_account_size > 0 else 0.0

        cash_remaining = max(0.0, available_cash - total_value)
        cash_reserve = config.default_account_size * config.cash_reserve
        total_risk = sum(s.risk_amount for s in sizings)

        risk_budgets = self._calculate_risk_budgets(sizings, config)

        warnings = self._generate_warnings(sizings, total_exposure, config)

        return AllocationResult(
            positions=sizings,
            total_value=total_value,
            total_risk=total_risk,
            cash_remaining=cash_remaining,
            cash_reserve=cash_reserve,
            exposure=total_exposure,
            risk_budgets=risk_budgets,
            warnings=warnings,
        )

    def allocate_by_risk_budget(
        self,
        requests: tuple[PositionRequest, ...],
        budgets: tuple[RiskBudget, ...],
        config: SizingConfig,
        available_cash: float,
    ) -> AllocationResult:
        """Allocate capital according to risk budgets.

        Args:
            requests:       Position requests.
            budgets:        Risk budget allocations.
            config:         Sizing configuration.
            available_cash: Available cash.

        Returns:
            AllocationResult with risk-budgeted positions.
        """
        if not budgets:
            return AllocationResult(cash_remaining=available_cash)

        total_risk_weight = sum(b.risk_weight for b in budgets)
        if total_risk_weight <= 0:
            return AllocationResult(cash_remaining=available_cash)

        sizings_list: list[PositionSizing] = []
        request_map = {r.symbol: r for r in requests}

        for budget in budgets:
            request = request_map.get(budget.symbol)
            if request is None:
                continue

            risk_share = budget.risk_weight / total_risk_weight
            capital_share = available_cash * risk_share
            value = min(capital_share, available_cash * config.max_position_size)
            shares = value / request.price if request.price > 0 else 0.0
            weight = value / config.default_account_size if config.default_account_size > 0 else 0.0

            if config.round_lot > 1 and shares > 0:
                shares = math.floor(shares / config.round_lot) * config.round_lot
                value = shares * request.price

            sizings_list.append(
                PositionSizing(
                    symbol=budget.symbol,
                    method="risk_budget",
                    shares=shares,
                    value=value,
                    weight=weight,
                    price=request.price,
                    risk_amount=budget.risk_amount,
                    reason=f"Risk budget allocation: {budget.risk_weight:.2%} weight",
                )
            )

        return self.optimize(tuple(sizings_list), config, available_cash)

    def _scale_sizings(
        self,
        sizings: tuple[PositionSizing, ...],
        scale: float,
        config: SizingConfig,
    ) -> tuple[PositionSizing, ...]:
        """Scale position sizes proportionally."""
        scaled = []
        for s in sizings:
            new_value = s.value * scale
            new_shares = new_value / s.price if s.price > 0 else 0.0
            new_weight = new_value / config.default_account_size if config.default_account_size > 0 else 0.0

            if config.round_lot > 1 and new_shares > 0:
                new_shares = math.floor(new_shares / config.round_lot) * config.round_lot
                new_value = new_shares * s.price

            scaled.append(
                PositionSizing(
                    symbol=s.symbol,
                    method=s.method,
                    shares=new_shares,
                    value=new_value,
                    weight=new_weight,
                    price=s.price,
                    risk_amount=s.risk_amount * scale,
                    risk_percentage=s.risk_percentage,
                    confidence=s.confidence,
                    reason=s.reason + f"; scaled by {scale:.2%}",
                )
            )
        return tuple(scaled)

    def _apply_constraint_resizing(
        self,
        sizings: tuple[PositionSizing, ...],
        config: SizingConfig,
    ) -> tuple[PositionSizing, ...]:
        """Resize positions to respect constraints."""
        resized = []

        for s in sizings:
            weight = s.weight
            value = s.value
            shares = s.shares

            if weight > config.max_position_size:
                value = config.default_account_size * config.max_position_size
                shares = value / s.price if s.price > 0 else 0.0
                weight = config.max_position_size

            if config.round_lot > 1 and shares > 0:
                shares = math.floor(shares / config.round_lot) * config.round_lot
                value = shares * s.price
                weight = value / config.default_account_size if config.default_account_size > 0 else 0.0

            resized.append(
                PositionSizing(
                    symbol=s.symbol,
                    method=s.method,
                    shares=shares,
                    value=value,
                    weight=weight,
                    price=s.price,
                    risk_amount=s.risk_amount * (value / s.value) if s.value > 0 else 0.0,
                    risk_percentage=s.risk_percentage,
                    confidence=s.confidence,
                    reason=s.reason + "; resized" if s.reason else "Resized to constraints",
                )
            )

        return tuple(resized)

    def _calculate_risk_budgets(
        self,
        sizings: tuple[PositionSizing, ...],
        config: SizingConfig,
    ) -> tuple[RiskBudget, ...]:
        """Calculate risk budget allocations."""
        total_risk = sum(s.risk_amount for s in sizings) or 1.0
        budgets = []
        for s in sizings:
            contribution = s.risk_amount / total_risk if total_risk > 0 else 0.0
            budgets.append(
                RiskBudget(
                    symbol=s.symbol,
                    risk_weight=contribution,
                    risk_amount=s.risk_amount,
                    contribution=contribution,
                )
            )
        return tuple(budgets)

    def _generate_warnings(
        self,
        sizings: tuple[PositionSizing, ...],
        total_exposure: float,
        config: SizingConfig,
    ) -> tuple[str, ...]:
        """Generate allocation warnings."""
        warnings_list: list[str] = []

        if total_exposure > config.max_portfolio_exposure * 0.9:
            warnings_list.append(
                f"Portfolio exposure {total_exposure:.2%} approaching limit {config.max_portfolio_exposure:.2%}"
            )

        for s in sizings:
            if s.weight > config.max_position_size * 0.9:
                warnings_list.append(
                    f"Position {s.symbol} weight {s.weight:.2%} approaching limit"
                )
            if s.value < config.min_trade_value and s.value > 0:
                warnings_list.append(
                    f"Position {s.symbol} value {s.value:,.0f} below min trade value"
                )

        return tuple(warnings_list)
