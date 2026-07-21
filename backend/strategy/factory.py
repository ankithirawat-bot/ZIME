"""Strategy factory.

Constructs fully configured strategy engines using dependency injection.
"""

from __future__ import annotations

from backend.strategy.engine import StrategyEngine
from backend.strategy.registry import RuleRegistry, build_default_rule_registry


class StrategyFactory:
    """Factory for constructing fully configured StrategyEngine instances.

    Uses dependency injection to construct all required components.
    No global state is maintained.
    """

    @staticmethod
    def create(
        rule_registry: RuleRegistry | None = None,
    ) -> StrategyEngine:
        """Create a fully configured StrategyEngine.

        Args:
            rule_registry: Registry of rules (defaults created).

        Returns:
            Configured StrategyEngine instance.
        """
        rule_registry = rule_registry or build_default_rule_registry()

        return StrategyEngine(rule_registry=rule_registry)

    @staticmethod
    def create_with_custom_rules() -> StrategyEngine:
        """Create a StrategyEngine with an empty rule registry.

        Useful for applications that only want custom rules.

        Returns:
            StrategyEngine with no pre-registered rules.
        """
        return StrategyEngine(rule_registry=RuleRegistry())

    @staticmethod
    def create_from_registry(rule_registry: RuleRegistry) -> StrategyEngine:
        """Create a StrategyEngine from an existing registry.

        Args:
            rule_registry: Pre-configured rule registry.

        Returns:
            StrategyEngine using the provided registry.
        """
        return StrategyEngine(rule_registry=rule_registry)
