"""Screener factory.

Constructs fully configured screening engines using dependency injection.
"""

from __future__ import annotations

from backend.screener.engine import ScreenerEngine
from backend.screener.operators import OperatorRegistry
from backend.screener.registry import FilterRegistry, build_default_filter_registry


class ScreenerFactory:
    """Factory for constructing fully configured ScreenerEngine instances.

    Uses dependency injection to construct all required components.
    No global state is maintained.
    """

    @staticmethod
    def create(
        filter_registry: FilterRegistry | None = None,
        operator_registry: OperatorRegistry | None = None,
    ) -> ScreenerEngine:
        """Create a fully configured ScreenerEngine.

        Args:
            filter_registry:   Registry of filters (defaults created).
            operator_registry: Registry of operators (defaults created).

        Returns:
            Configured ScreenerEngine instance.
        """
        filter_registry = filter_registry or build_default_filter_registry()
        operator_registry = operator_registry or OperatorRegistry()

        return ScreenerEngine(
            filter_registry=filter_registry,
            operator_registry=operator_registry,
        )

    @staticmethod
    def create_with_custom_filters() -> ScreenerEngine:
        """Create a ScreenerEngine with an empty filter registry.

        Useful for applications that only want custom filters.

        Returns:
            ScreenerEngine with no built-in filters.
        """
        return ScreenerEngine(
            filter_registry=FilterRegistry(load_defaults=False),
            operator_registry=OperatorRegistry(),
        )

    @staticmethod
    def create_from_registries(
        filter_registry: FilterRegistry,
        operator_registry: OperatorRegistry,
    ) -> ScreenerEngine:
        """Create a ScreenerEngine from existing registries.

        Args:
            filter_registry:   Pre-configured filter registry.
            operator_registry: Pre-configured operator registry.

        Returns:
            ScreenerEngine using the provided registries.
        """
        return ScreenerEngine(
            filter_registry=filter_registry,
            operator_registry=operator_registry,
        )
