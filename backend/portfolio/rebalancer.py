"""Portfolio rebalancer.

Generates rebalancing actions based on target allocations.
"""

from __future__ import annotations

from datetime import datetime

from backend.portfolio.models import (
    PortfolioConfig,
    PortfolioPosition,
    RebalanceAction,
    RebalanceActionType,
)


class Rebalancer:
    """Generates rebalancing actions.

    Supports periodic, threshold-based, and drift-based rebalancing.
    """

    def __init__(self, config: PortfolioConfig) -> None:
        """Initialize the rebalancer.

        Args:
            config: Portfolio configuration.
        """
        self._config = config
        self._last_rebalance: datetime | None = None

    @property
    def config(self) -> PortfolioConfig:
        """Access the configuration."""
        return self._config

    @property
    def last_rebalance(self) -> datetime | None:
        """Access the last rebalance time."""
        return self._last_rebalance

    def should_rebalance(
        self,
        positions: list[PortfolioPosition],
        total_equity: float,
    ) -> bool:
        """Check if rebalancing is needed.

        Args:
            positions:    Current positions.
            total_equity: Total portfolio equity.

        Returns:
            True if rebalancing should occur.
        """
        if self._config.rebalance_frequency.value in ("THRESHOLD", "DRIFT"):
            return self._check_threshold_rebalance(positions, total_equity)

        return self._check_periodic_rebalance()

    def generate_actions(
        self,
        positions: list[PortfolioPosition],
        target_allocations: dict[str, float],
        total_equity: float,
        prices: dict[str, float],
    ) -> list[RebalanceAction]:
        """Generate rebalancing actions.

        Args:
            positions:         Current positions.
            target_allocations: Target allocation weights.
            total_equity:      Total portfolio equity.
            prices:            Current prices.

        Returns:
            List of rebalancing actions.
        """
        actions = []

        current_weights = self._calculate_current_weights(positions, total_equity)

        all_symbols = set(current_weights.keys()) | set(target_allocations.keys())

        for symbol in all_symbols:
            current = current_weights.get(symbol, 0.0)
            target = target_allocations.get(symbol, 0.0)
            drift = current - target

            price = prices.get(symbol, 0.0)
            if price <= 0:
                continue

            current_value = current * total_equity
            target_value = target * total_equity
            value_diff = target_value - current_value

            quantity = abs(int(value_diff / price)) if price > 0 else 0

            if abs(drift) < self._config.drift_threshold and quantity == 0:
                action_type = RebalanceActionType.HOLD
            elif value_diff > 0:
                action_type = RebalanceActionType.BUY
            elif value_diff < 0:
                action_type = RebalanceActionType.SELL
            else:
                action_type = RebalanceActionType.HOLD

            actions.append(
                RebalanceAction(
                    symbol=symbol,
                    action_type=action_type,
                    quantity=quantity,
                    current_weight=current,
                    target_weight=target,
                    current_value=current_value,
                    target_value=target_value,
                    drift=drift,
                )
            )

        actions.sort(key=lambda a: abs(a.drift), reverse=True)

        self._last_rebalance = datetime.now().astimezone()

        return actions

    def filter_actions(
        self,
        actions: list[RebalanceAction],
        cash: float,
        total_equity: float,
    ) -> list[RebalanceAction]:
        """Filter rebalancing actions based on constraints.

        Args:
            actions:       Rebalancing actions.
            cash:          Available cash.
            total_equity:  Total portfolio equity.

        Returns:
            Filtered list of actions.
        """
        filtered = []
        available_cash = cash - (total_equity * self._config.cash_reserve)

        for action in actions:
            if action.action_type == RebalanceActionType.HOLD:
                continue

            if action.action_type == RebalanceActionType.BUY:
                cost = action.quantity * action.target_value / (
                    action.target_weight * total_equity
                    if action.target_weight > 0
                    else 1.0
                )
                if cost > available_cash:
                    adjusted_qty = int(available_cash / (
                        action.target_value / (
                            action.target_weight * total_equity
                            if action.target_weight > 0
                            else 1.0
                        )
                    ))
                    if adjusted_qty > 0:
                        filtered.append(
                            RebalanceAction(
                                symbol=action.symbol,
                                action_type=action.action_type,
                                quantity=adjusted_qty,
                                current_weight=action.current_weight,
                                target_weight=action.target_weight,
                                current_value=action.current_value,
                                target_value=action.target_value,
                                drift=action.drift,
                            )
                        )
                    continue
                available_cash -= cost

            filtered.append(action)

        return filtered

    def _calculate_current_weights(
        self,
        positions: list[PortfolioPosition],
        total_equity: float,
    ) -> dict[str, float]:
        """Calculate current portfolio weights.

        Args:
            positions:    Current positions.
            total_equity: Total portfolio equity.

        Returns:
            Dictionary of symbol -> weight.
        """
        if total_equity <= 0:
            return {}

        weights = {}
        for pos in positions:
            if pos.quantity > 0:
                weights[pos.symbol] = pos.market_value / total_equity

        return weights

    def _check_periodic_rebalance(self) -> bool:
        """Check if periodic rebalance is due.

        Returns:
            True if rebalance should occur.
        """
        if self._last_rebalance is None:
            return True

        now = datetime.now().astimezone()
        elapsed = now - self._last_rebalance

        from datetime import timedelta

        frequency = self._config.rebalance_frequency
        if frequency.value == "DAILY":
            return elapsed >= timedelta(days=1)
        elif frequency.value == "WEEKLY":
            return elapsed >= timedelta(weeks=1)
        elif frequency.value == "MONTHLY":
            return elapsed >= timedelta(days=30)
        elif frequency.value == "QUARTERLY":
            return elapsed >= timedelta(days=90)

        return False

    def _check_threshold_rebalance(
        self,
        positions: list[PortfolioPosition],
        total_equity: float,
    ) -> bool:
        """Check if threshold-based rebalance is needed.

        Args:
            positions:    Current positions.
            total_equity: Total portfolio equity.

        Returns:
            True if rebalance should occur.
        """
        if total_equity <= 0:
            return False

        for pos in positions:
            if pos.quantity <= 0:
                continue

            weight = pos.market_value / total_equity
            if abs(weight - self._config.max_position_size) > self._config.rebalance_threshold:
                return True

        return False
