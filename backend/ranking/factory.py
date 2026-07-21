"""Ranking factory.

Constructs fully configured ranking engines using dependency injection.
"""

from __future__ import annotations

from backend.ranking.engine import RankingEngine
from backend.ranking.registry import FactorRegistry, build_default_factor_registry


class RankingFactory:
    """Factory for constructing fully configured RankingEngine instances.

    Uses dependency injection to construct all required components.
    No global state is maintained.
    """

    @staticmethod
    def create(
        factor_registry: FactorRegistry | None = None,
    ) -> RankingEngine:
        """Create a fully configured RankingEngine.

        Args:
            factor_registry: Registry of factors (defaults created).

        Returns:
            Configured RankingEngine instance.
        """
        factor_registry = factor_registry or build_default_factor_registry()

        return RankingEngine(factor_registry=factor_registry)

    @staticmethod
    def create_with_custom_factors() -> RankingEngine:
        """Create a RankingEngine with an empty factor registry.

        Useful for applications that only want custom factors.

        Returns:
            RankingEngine with no built-in factors.
        """
        return RankingEngine(factor_registry=FactorRegistry(load_defaults=False))

    @staticmethod
    def create_from_registry(factor_registry: FactorRegistry) -> RankingEngine:
        """Create a RankingEngine from an existing registry.

        Args:
            factor_registry: Pre-configured factor registry.

        Returns:
            RankingEngine using the provided registry.
        """
        return RankingEngine(factor_registry=factor_registry)
