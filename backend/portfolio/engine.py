"""Portfolio engine.

Core portfolio management engine for capital allocation and position management.
"""

from __future__ import annotations

from datetime import datetime
from typing import Any

from backend.portfolio.allocation import calculate_weights, validate_weights
from backend.portfolio.constraints import ConstraintValidator
from backend.portfolio.exceptions import (
    AllocationError,
    InsufficientFundsError,
    InvalidPortfolioConfigError,
    PositionNotFoundError,
)
from backend.portfolio.models import (
    Allocation,
    PortfolioConfig,
    PortfolioDefinition,
    PortfolioMetrics,
    PortfolioSnapshot,
    RebalanceAction,
    RebalanceActionType,
)
from backend.portfolio.positions import PositionManager
from backend.portfolio.rebalancer import Rebalancer


class PortfolioEngine:
    """Core portfolio management engine.

    Manages capital allocation, position sizing, rebalancing, and exposure control.
    """

    def __init__(
        self,
        position_manager: PositionManager | None = None,
        rebalancer: Rebalancer | None = None,
        constraint_validator: ConstraintValidator | None = None,
    ) -> None:
        """Initialize the engine.

        Args:
            position_manager:    Position manager.
            rebalancer:          Rebalancer.
            constraint_validator: Constraint validator.
        """
        self._position_manager = position_manager
        self._rebalancer = rebalancer
        self._constraint_validator = constraint_validator
        self._cash = 0.0
        self._config: PortfolioConfig | None = None

    @property
    def cash(self) -> float:
        """Available cash."""
        return self._cash

    @property
    def config(self) -> PortfolioConfig | None:
        """Current configuration."""
        return self._config

    def create_portfolio(self, definition: PortfolioDefinition) -> PortfolioSnapshot:
        """Create a new portfolio.

        Args:
            definition: Portfolio definition.

        Returns:
            Initial portfolio snapshot.
        """
        self._config = definition.config
        self._cash = definition.config.initial_capital

        self._position_manager = PositionManager(definition.config)
        self._rebalancer = Rebalancer(definition.config)
        self._constraint_validator = ConstraintValidator(definition.config)

        return self.generate_snapshot()

    def allocate(
        self,
        symbols: tuple[str, ...],
        data: dict[str, Any],
        prices: dict[str, float],
    ) -> list[Allocation]:
        """Allocate capital to symbols.

        Args:
            symbols: Symbols to allocate.
            data:    Market data for calculations.
            prices:  Current prices.

        Returns:
            List of allocations.
        """
        if self._config is None:
            raise InvalidPortfolioConfigError("Portfolio not created")

        if not symbols:
            raise AllocationError("No symbols provided")

        weights = calculate_weights(
            self._config.allocation_strategy,
            symbols,
            data,
            self._config,
        )

        validate_weights(weights)

        total_equity = self._cash + self._get_holdings_value()
        available_cash = total_equity * (1 - self._config.cash_reserve)

        allocations = []
        for symbol in symbols:
            weight = weights.get(symbol, 0.0)
            amount = available_cash * weight
            price = prices.get(symbol, 0.0)

            if price > 0 and amount > 0:
                quantity = int(amount / price)
                if quantity > 0:
                    allocations.append(
                        Allocation(
                            symbol=symbol,
                            weight=weight,
                            amount=amount,
                        )
                    )

        return allocations

    def execute_allocations(
        self,
        allocations: list[Allocation],
        prices: dict[str, float],
    ) -> PortfolioSnapshot:
        """Execute allocations.

        Args:
            allocations: Allocations to execute.
            prices:      Current prices.

        Returns:
            Updated portfolio snapshot.
        """
        if self._config is None:
            raise InvalidPortfolioConfigError("Portfolio not created")

        for alloc in allocations:
            price = prices.get(alloc.symbol, 0.0)
            if price <= 0:
                continue

            quantity = int(alloc.amount / price)
            if quantity <= 0:
                continue

            cost = quantity * price * (1 + self._config.transaction_cost)
            if cost > self._cash:
                raise InsufficientFundsError(cost, self._cash)

            self._cash -= cost

            self._position_manager.open_position(
                alloc.symbol,
                quantity,
                price,
                alloc.sector,
            )

        return self.generate_snapshot()

    def rebalance(
        self,
        target_allocations: dict[str, float],
        prices: dict[str, float],
    ) -> list[RebalanceAction]:
        """Rebalance the portfolio.

        Args:
            target_allocations: Target allocation weights.
            prices:            Current prices.

        Returns:
            List of rebalancing actions executed.
        """
        if self._config is None:
            raise InvalidPortfolioConfigError("Portfolio not created")

        positions = self._position_manager.get_all_positions()
        total_equity = self._cash + self._get_holdings_value()

        if not self._rebalancer.should_rebalance(positions, total_equity):
            return []

        actions = self._rebalancer.generate_actions(
            positions, target_allocations, total_equity, prices
        )

        actions = self._rebalancer.filter_actions(
            actions, self._cash, total_equity
        )

        executed_actions = []
        for action in actions:
            if action.action_type == RebalanceActionType.BUY:
                self._execute_buy(action, prices)
                executed_actions.append(action)
            elif action.action_type == RebalanceActionType.SELL:
                self._execute_sell(action, prices)
                executed_actions.append(action)

        return executed_actions

    def update_market_values(self, prices: dict[str, float]) -> PortfolioSnapshot:
        """Update market values for all positions.

        Args:
            prices: Current prices.

        Returns:
            Updated portfolio snapshot.
        """
        self._position_manager.update_all_prices(prices)
        return self.generate_snapshot()

    def evaluate_constraints(self) -> list[str]:
        """Evaluate all constraints.

        Returns:
            List of constraint violation messages.
        """
        if self._config is None:
            return ["Portfolio not created"]

        positions = self._position_manager.get_all_positions()
        total_equity = self._cash + self._get_holdings_value()

        violations = self._constraint_validator.validate_all(
            positions, self._cash, total_equity
        )

        return [str(v) for v in violations]

    def generate_snapshot(self) -> PortfolioSnapshot:
        """Generate a portfolio snapshot.

        Returns:
            PortfolioSnapshot with current state.
        """
        if self._config is None:
            return PortfolioSnapshot()

        positions = self._position_manager.get_all_positions()
        holdings_value = self._get_holdings_value()
        total_equity = self._cash + holdings_value

        unrealized = sum(p.unrealized_pnl for p in positions)
        realized = sum(p.realized_pnl for p in positions)

        exposure = holdings_value / total_equity if total_equity > 0 else 0.0

        cash_reserve = total_equity * self._config.cash_reserve
        available_cash = self._cash - cash_reserve

        return PortfolioSnapshot(
            timestamp=datetime.now().astimezone(),
            cash=self._cash,
            holdings_value=holdings_value,
            total_equity=total_equity,
            unrealized_pnl=unrealized,
            realized_pnl=realized,
            exposure=exposure,
            positions=tuple(positions),
            cash_reserve=cash_reserve,
            available_cash=max(available_cash, 0.0),
        )

    def get_metrics(
        self,
        returns: list[float] | None = None,
        benchmark_returns: list[float] | None = None,
    ) -> PortfolioMetrics:
        """Calculate portfolio metrics.

        Args:
            returns:           Portfolio returns history.
            benchmark_returns: Benchmark returns history.

        Returns:
            PortfolioMetrics with calculated metrics.
        """
        import math

        snapshot = self.generate_snapshot()
        positions = snapshot.positions

        concentration = sum(p.weight**2 for p in positions if p.quantity > 0)

        sector_exposure = self._position_manager.get_sector_exposure()

        cash_utilization = (
            (snapshot.total_equity - snapshot.cash) / snapshot.total_equity
            if snapshot.total_equity > 0
            else 0.0
        )

        volatility = 0.0
        sharpe = 0.0
        if returns and len(returns) > 1:
            mean_ret = sum(returns) / len(returns)
            variance = sum((r - mean_ret) ** 2 for r in returns) / (len(returns) - 1)
            volatility = math.sqrt(variance) if variance > 0 else 0.0001
            excess = mean_ret - (self._config.risk_free_rate / 252 if self._config else 0.06 / 252)
            sharpe = (excess / volatility) * math.sqrt(252) if volatility > 0 else 0.0

        alpha = 0.0
        beta = 0.0
        if returns and benchmark_returns and len(returns) == len(benchmark_returns):
            if len(returns) > 1:
                mean_r = sum(returns) / len(returns)
                mean_b = sum(benchmark_returns) / len(benchmark_returns)
                cov = sum(
                    (r - mean_r) * (b - mean_b)
                    for r, b in zip(returns, benchmark_returns)
                ) / (len(returns) - 1)
                var_b = sum((b - mean_b) ** 2 for b in benchmark_returns) / (
                    len(benchmark_returns) - 1
                )
                beta = cov / var_b if var_b > 0 else 0.0
                alpha = mean_r - beta * mean_b

        max_dd = 0.0
        if returns:
            peak = 1.0
            equity = 1.0
            for r in returns:
                equity *= 1 + r
                if equity > peak:
                    peak = equity
                dd = (peak - equity) / peak if peak > 0 else 0.0
                max_dd = max(max_dd, dd)

        return PortfolioMetrics(
            portfolio_return=sum(returns) if returns else 0.0,
            alpha=alpha,
            beta=beta,
            volatility=volatility,
            sharpe_ratio=sharpe,
            maximum_drawdown=max_dd,
            concentration_index=concentration,
            cash_utilization=cash_utilization,
            sector_exposure=sector_exposure,
        )

    def _get_holdings_value(self) -> float:
        """Get total holdings value."""
        if self._position_manager is None:
            return 0.0
        return self._position_manager.get_total_value()

    def _execute_buy(self, action: RebalanceAction, prices: dict[str, float]) -> None:
        """Execute a buy action.

        Args:
            action: Buy action.
            prices: Current prices.
        """
        price = prices.get(action.symbol, 0.0)
        if price <= 0:
            return

        cost = action.quantity * price * (1 + (self._config.transaction_cost if self._config else 0.001))
        if cost > self._cash:
            action_qty = int(self._cash / (price * (1 + (self._config.transaction_cost if self._config else 0.001))))
            if action_qty <= 0:
                return
            action = RebalanceAction(
                symbol=action.symbol,
                action_type=action.action_type,
                quantity=action_qty,
                current_weight=action.current_weight,
                target_weight=action.target_weight,
                current_value=action.current_value,
                target_value=action.target_value,
                drift=action.drift,
            )
            cost = action.quantity * price * (1 + (self._config.transaction_cost if self._config else 0.001))

        self._cash -= cost
        self._position_manager.open_position(action.symbol, action.quantity, price)

    def _execute_sell(self, action: RebalanceAction, prices: dict[str, float]) -> None:
        """Execute a sell action.

        Args:
            action: Sell action.
            prices: Current prices.
        """
        price = prices.get(action.symbol, 0.0)
        if price <= 0:
            return

        try:
            position = self._position_manager.get_position(action.symbol)
            qty_to_sell = min(action.quantity, position.quantity)
            if qty_to_sell <= 0:
                return

            proceeds = qty_to_sell * price * (1 - (self._config.transaction_cost if self._config else 0.001))
            self._cash += proceeds
            self._position_manager.reduce_position(action.symbol, qty_to_sell, price)
        except PositionNotFoundError:
            pass
