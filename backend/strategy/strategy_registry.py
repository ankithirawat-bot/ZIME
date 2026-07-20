"""
Strategy Registry.

Maps StrategyType to Strategy implementations.
No if/elif dispatch.
"""

from __future__ import annotations

from typing import TYPE_CHECKING

from backend.strategy.models import StrategyType

if TYPE_CHECKING:
    from backend.strategy.strategies import Strategy


class StrategyRegistry:
    """Registry mapping StrategyType to Strategy instances.

    Strategies self-register. The engine resolves through the registry.
    """

    def __init__(self) -> None:
        self._strategies: dict[StrategyType, Strategy] = {}

    def register(self, strategy_type: StrategyType, strategy: Strategy) -> None:
        """Register a strategy.

        Args:
            strategy_type: Strategy type key.
            strategy:      Strategy instance.
        """
        self._strategies[strategy_type] = strategy

    def resolve(self, strategy_type: StrategyType) -> Strategy | None:
        """Resolve a strategy by type.

        Args:
            strategy_type: Strategy type to resolve.

        Returns:
            Strategy instance or None if not found.
        """
        return self._strategies.get(strategy_type)

    def has(self, strategy_type: StrategyType) -> bool:
        """Check if a strategy is registered.

        Args:
            strategy_type: Strategy type to check.

        Returns:
            True if registered.
        """
        return strategy_type in self._strategies

    def registered_types(self) -> tuple[StrategyType, ...]:
        """Return all registered strategy types.

        Returns:
            Tuple of registered strategy types.
        """
        return tuple(self._strategies.keys())
