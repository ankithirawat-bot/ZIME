"""Strategy rule registry.

Maintains a registry of available rules for extensibility.
"""

from __future__ import annotations

from backend.strategy.exceptions import RuleNotFoundError
from backend.strategy.models import RuleCategory, StrategyRule


class RuleRegistry:
    """Registry of strategy rules.

    Supports custom rules without modifying engine code.
    """

    def __init__(self) -> None:
        self._rules: dict[str, StrategyRule] = {}

    def register(self, rule: StrategyRule) -> None:
        """Register a strategy rule.

        Args:
            rule: Strategy rule to register.
        """
        self._rules[rule.name] = rule

    def get(self, name: str) -> StrategyRule:
        """Get a rule by name.

        Args:
            name: Rule name.

        Returns:
            The strategy rule.

        Raises:
            RuleNotFoundError: If the rule is not registered.
        """
        if name not in self._rules:
            raise RuleNotFoundError(name)
        return self._rules[name]

    def is_registered(self, name: str) -> bool:
        """Check if a rule is registered."""
        return name in self._rules

    def registered_names(self) -> tuple[str, ...]:
        """Return all registered rule names."""
        return tuple(sorted(self._rules.keys()))

    def rules_by_category(self, category: RuleCategory) -> tuple[StrategyRule, ...]:
        """Return rules for a given category."""
        return tuple(
            rule for rule in self._rules.values() if rule.category == category
        )

    def all_rules(self) -> dict[str, StrategyRule]:
        """Return a copy of all registered rules."""
        return dict(self._rules)

    def clear(self) -> None:
        """Clear all registered rules."""
        self._rules.clear()


def build_default_rule_registry() -> RuleRegistry:
    """Build a rule registry with no default rules.

    Returns:
        An empty RuleRegistry.
    """
    return RuleRegistry()
