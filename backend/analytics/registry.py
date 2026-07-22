"""
Analytics Plugin Registry.

Manages the lifecycle and ordering of analytics engines.  Engines are
registered by name and can be retrieved, listed or iterated in insertion
order.  The registry is the single source of truth for which engines are
available to the pipeline.
"""

from __future__ import annotations

from collections import OrderedDict

from backend.analytics.base_engine import AnalyticsEngineBase


class AnalyticsRegistry:
    """Registry for analytics engine plugins.

    Engines are stored in registration order, which defines the execution
    order for the pipeline.  Each engine must have a unique name (returned
    by :meth:`AnalyticsEngineBase._engine_name`).

    Example::

        registry = AnalyticsRegistry()
        registry.register(TrendEngine())
        registry.register(MomentumEngine())
        for engine in registry.ordered():
            fact = engine.analyze(context)
    """

    def __init__(self) -> None:
        self._engines: OrderedDict[str, AnalyticsEngineBase] = OrderedDict()

    def register(
        self,
        engine: AnalyticsEngineBase,
        *,
        name: str | None = None,
    ) -> None:
        """Register an engine.

        Args:
            engine: Engine instance to register.
            name:   Optional explicit name.  If ``None`` the engine's
                    :meth:`~AnalyticsEngineBase._engine_name` is used.

        Raises:
            ValueError: If an engine with the same name is already registered.
        """
        key = name if name is not None else engine._engine_name()
        if key in self._engines:
            raise ValueError(f"Engine '{key}' is already registered")
        self._engines[key] = engine

    def unregister(self, name: str) -> None:
        """Remove a previously registered engine by name.

        Args:
            name: Engine name to remove.

        Raises:
            KeyError: If *name* is not registered.
        """
        del self._engines[name]

    def list(self) -> tuple[str, ...]:
        """Return registered engine names in registration order."""
        return tuple(self._engines.keys())

    def get(self, name: str) -> AnalyticsEngineBase | None:
        """Retrieve an engine by name, or ``None`` if not found."""
        return self._engines.get(name)

    def ordered(self) -> tuple[AnalyticsEngineBase, ...]:
        """Return engine instances in registration order."""
        return tuple(self._engines.values())

    def __len__(self) -> int:
        return len(self._engines)

    def __contains__(self, name: str) -> bool:
        return name in self._engines


def create_default_registry() -> AnalyticsRegistry:
    """Create a registry pre-populated with all standard analytics engines.

    This is a convenience factory so that consumers can obtain a fully
    populated registry without importing individual engine modules::

        from backend.analytics.registry import create_default_registry
        registry = create_default_registry()
        pipeline = AnalyticsPipeline(registry=registry)

    Returns:
        AnalyticsRegistry with Trend, Momentum, Volume, Relative Strength
        and Volatility engines registered in that order.
    """
    from backend.analytics.momentum.momentum_engine import MomentumEngine
    from backend.analytics.relative_strength.relative_strength_engine import (
        RelativeStrengthEngine,
    )
    from backend.analytics.trend.trend_engine import TrendEngine
    from backend.analytics.volatility.volatility_engine import (
        VolatilityEngine,
    )
    from backend.analytics.volume.volume_engine import VolumeEngine

    registry = AnalyticsRegistry()
    registry.register(TrendEngine())
    registry.register(MomentumEngine())
    registry.register(VolumeEngine())
    registry.register(RelativeStrengthEngine())
    registry.register(VolatilityEngine())
    return registry
