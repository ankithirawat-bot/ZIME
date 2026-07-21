"""Volatility forecast factory.

Constructs fully configured volatility forecast engines using dependency injection.
"""

from __future__ import annotations

from typing import Any

from backend.volatility.comparison import ModelComparer
from backend.volatility.engine import VolatilityEngine
from backend.volatility.forecast import ForecastEngine
from backend.volatility.models import VolatilityConfig


class VolatilityFactory:
    """Factory for constructing fully configured VolatilityEngine instances.

    Uses dependency injection to construct all required components.
    No global state is maintained.
    """

    @staticmethod
    def create(
        config: VolatilityConfig | None = None,
        forecast_engine: ForecastEngine | None = None,
        comparer: ModelComparer | None = None,
        portfolio_engine: Any | None = None,
        risk_engine: Any | None = None,
        sizing_engine: Any | None = None,
        strategy_engine: Any | None = None,
        backtesting_engine: Any | None = None,
    ) -> VolatilityEngine:
        """Create a fully configured VolatilityEngine.

        Args:
            config:             Volatility configuration (defaults created).
            forecast_engine:    Forecast engine (defaults created).
            comparer:           Model comparer (defaults created).
            portfolio_engine:   Optional portfolio engine for integration.
            risk_engine:        Optional risk engine for integration.
            sizing_engine:      Optional sizing engine for integration.
            strategy_engine:    Optional strategy engine for integration.
            backtesting_engine: Optional backtesting engine for integration.

        Returns:
            Configured VolatilityEngine instance.
        """
        config = config or VolatilityConfig()
        forecast_engine = forecast_engine or ForecastEngine()
        comparer = comparer or ModelComparer()

        return VolatilityEngine(
            config=config,
            forecast_engine=forecast_engine,
            comparer=comparer,
            portfolio_engine=portfolio_engine,
            risk_engine=risk_engine,
            sizing_engine=sizing_engine,
            strategy_engine=strategy_engine,
            backtesting_engine=backtesting_engine,
        )

    @staticmethod
    def create_with_models(
        models: dict[str, Any],
        config: VolatilityConfig | None = None,
    ) -> VolatilityEngine:
        """Create a VolatilityEngine with custom models.

        Default models are still registered; custom models override.

        Args:
            models: Custom volatility models (name -> estimator instance).
            config: Volatility configuration (defaults created).

        Returns:
            VolatilityEngine with custom models.
        """
        forecast_engine = ForecastEngine()
        for name, estimator in models.items():
            forecast_engine.register_estimator(name, estimator)
        return VolatilityEngine(config=config, forecast_engine=forecast_engine)

    @staticmethod
    def create_from_config(
        config: VolatilityConfig,
    ) -> VolatilityEngine:
        """Create a VolatilityEngine from a configuration.

        Args:
            config: Volatility configuration.

        Returns:
            VolatilityEngine using the provided config.
        """
        return VolatilityEngine(config=config)
