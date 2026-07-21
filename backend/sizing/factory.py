"""Sizing factory.

Constructs fully configured sizing engines using dependency injection.
"""

from __future__ import annotations

from typing import Any

from backend.sizing.engine import SizingEngine
from backend.sizing.models import SizingConfig
from backend.sizing.optimizer import SizingOptimizer


class SizingFactory:
    """Factory for constructing fully configured SizingEngine instances.

    Uses dependency injection to construct all required components.
    No global state is maintained.
    """

    @staticmethod
    def create(
        config: SizingConfig | None = None,
        optimizer: SizingOptimizer | None = None,
        portfolio_engine: Any | None = None,
        risk_engine: Any | None = None,
        strategy_engine: Any | None = None,
    ) -> SizingEngine:
        """Create a fully configured SizingEngine.

        Args:
            config:           Sizing configuration (defaults created).
            optimizer:        Sizing optimizer (defaults created).
            portfolio_engine: Optional portfolio engine for integration.
            risk_engine:      Optional risk engine for integration.
            strategy_engine:  Optional strategy engine for integration.

        Returns:
            Configured SizingEngine instance.
        """
        config = config or SizingConfig()
        optimizer = optimizer or SizingOptimizer()

        return SizingEngine(
            config=config,
            optimizer=optimizer,
            portfolio_engine=portfolio_engine,
            risk_engine=risk_engine,
            strategy_engine=strategy_engine,
        )

    @staticmethod
    def create_with_methods(
        methods: dict[str, Any],
        config: SizingConfig | None = None,
    ) -> SizingEngine:
        """Create a SizingEngine with custom sizing methods.

        Default methods are still registered; custom methods override.

        Args:
            methods: Custom sizing methods (name -> method instance).
            config:  Sizing configuration (defaults created).

        Returns:
            SizingEngine with custom methods.
        """
        engine = SizingEngine(config=config)
        for name, method in methods.items():
            engine.register_method(name, method)
        return engine

    @staticmethod
    def create_from_config(
        config: SizingConfig,
    ) -> SizingEngine:
        """Create a SizingEngine from a configuration.

        Args:
            config: Sizing configuration.

        Returns:
            SizingEngine using the provided config.
        """
        return SizingEngine(config=config)
