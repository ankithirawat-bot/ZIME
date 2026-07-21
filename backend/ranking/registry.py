"""Ranking factor registry.

Maintains a registry of available ranking factors for extensibility.
"""

from __future__ import annotations

from backend.ranking.exceptions import FactorNotFoundError
from backend.ranking.factors import FactorFunc, get_builtin_factors
from backend.ranking.models import FactorCategory, RankingDirection


class FactorRegistry:
    """Registry of ranking factors.

    Supports custom factors without modifying engine code.
    """

    def __init__(self, *, load_defaults: bool = True) -> None:
        """Initialize the registry.

        Args:
            load_defaults: Whether to load built-in factors.
        """
        self._factors: dict[str, tuple[FactorCategory, RankingDirection, FactorFunc]] = {}
        if load_defaults:
            self._factors.update(get_builtin_factors())

    def register(
        self,
        name: str,
        func: FactorFunc,
        category: FactorCategory = FactorCategory.CUSTOM,
        direction: RankingDirection = RankingDirection.HIGHER_IS_BETTER,
    ) -> None:
        """Register a factor.

        Args:
        ----
            name:      Factor name.
            func:      Factor function.
            category:  Factor category.
            direction: Ranking direction.
        """
        self._factors[name] = (category, direction, func)

    def get(self, name: str) -> FactorFunc:
        """Get a factor function by name.

        Args:
            name: Factor name.

        Returns:
        -------
            The factor function.

        Raises:
        ------
            FactorNotFoundError: If the factor is not registered.
        """
        if name not in self._factors:
            raise FactorNotFoundError(name)
        _, _, func = self._factors[name]
        return func

    def get_direction(self, name: str) -> RankingDirection:
        """Get the ranking direction for a factor.

        Args:
            name: Factor name.

        Returns:
            The ranking direction.

        Raises:
            FactorNotFoundError: If the factor is not registered.
        """
        if name not in self._factors:
            raise FactorNotFoundError(name)
        _, direction, _ = self._factors[name]
        return direction

    def get_category(self, name: str) -> FactorCategory:
        """Get the category of a factor.

        Args:
            name: Factor name.

        Returns:
            The factor category.

        Raises:
            FactorNotFoundError: If the factor is not registered.
        """
        if name not in self._factors:
            raise FactorNotFoundError(name)
        category, _, _ = self._factors[name]
        return category

    def is_registered(self, name: str) -> bool:
        """Check if a factor is registered."""
        return name in self._factors

    def registered_names(self) -> tuple[str, ...]:
        """Return all registered factor names."""
        return tuple(sorted(self._factors.keys()))

    def factors_by_category(self, category: FactorCategory) -> tuple[str, ...]:
        """Return factor names for a given category."""
        return tuple(
            sorted(
                name for name, (cat, _, _) in self._factors.items() if cat == category
            )
        )

    def all_factors(self) -> dict[str, tuple[FactorCategory, RankingDirection, FactorFunc]]:
        """Return a copy of all registered factors."""
        return dict(self._factors)


def build_default_factor_registry() -> FactorRegistry:
    """Build a factor registry with all built-in factors.

    Returns:
        A FactorRegistry with all built-in factors loaded.
    """
    return FactorRegistry(load_defaults=True)
