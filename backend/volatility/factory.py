"""Volatility forecast factory.

Constructs fully configured engines using dependency injection.
"""

from __future__ import annotations

from typing import Any

from backend.volatility.comparison import ModelComparer
from backend.volatility.engine import VolatilityEngine
from backend.volatility.forecast import ForecastEngine
from backend.volatility.models import VolatilityConfig


class VolatilityFactory:
    """Factory for constructing configured VolatilityEngine instances."""

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
            config:             Configuration (defaults created).
            forecast_engine:    Forecast engine (defaults created).
            comparer:           Model comparer (defaults created).
            portfolio_engine:   Optional portfolio engine.
            risk_engine:        Optional risk engine.
            sizing_engine:      Optional sizing engine.
            strategy_engine:    Optional strategy engine.
            backtesting_engine: Optional backtesting engine.

        Returns:
            Configured VolatilityEngine.
        """
        config = config or VolatilityConfig()
        forecast_engine = forecast_engine or ForecastEngine()
        comparer = comparer or ModelComparer()
        return VolatilityEngine(
            config=config, forecast_engine=forecast_engine, comparer=comparer,
            portfolio_engine=portfolio_engine, risk_engine=risk_engine,
            sizing_engine=sizing_engine, strategy_engine=strategy_engine,
            backtesting_engine=backtesting_engine,
        )

    @staticmethod
    def create_with_estimators(
        estimators: dict[str, Any],
        config: VolatilityConfig | None = None,
    ) -> VolatilityEngine:
        """Create with custom estimators.

        Args:
            estimators: Custom estimators (name -> instance).
            config:     Configuration (defaults created).

        Returns:
            VolatilityEngine.
        """
        fe = ForecastEngine()
        for name, est in estimators.items():
            fe.register_estimator(name, est)
        return VolatilityEngine(config=config, forecast_engine=fe)

    @staticmethod
    def create_from_config(config: VolatilityConfig) -> VolatilityEngine:
        """Create from configuration.

        Args:
            config: Configuration.

        Returns:
            VolatilityEngine.
        """
        return VolatilityEngine(config=config)
