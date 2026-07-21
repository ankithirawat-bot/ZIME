"""Market regime detection factory.

Constructs fully configured regime engines using dependency injection.
"""

from __future__ import annotations

from typing import Any

from backend.regime.engine import RegimeEngine
from backend.regime.features import FeatureExtractor
from backend.regime.models import RegimeConfig


class RegimeFactory:
    """Factory for constructing configured RegimeEngine instances."""

    @staticmethod
    def create(
        config: RegimeConfig | None = None,
        feature_extractor: FeatureExtractor | None = None,
        strategy_engine: Any | None = None,
        sizing_engine: Any | None = None,
        portfolio_engine: Any | None = None,
        risk_engine: Any | None = None,
        volatility_engine: Any | None = None,
        backtesting_engine: Any | None = None,
    ) -> RegimeEngine:
        """Create a fully configured RegimeEngine.

        Args:
            config:             Configuration (defaults created).
            feature_extractor:  Feature extractor (defaults created).
            strategy_engine:    Optional strategy engine.
            sizing_engine:      Optional sizing engine.
            portfolio_engine:   Optional portfolio engine.
            risk_engine:        Optional risk engine.
            volatility_engine:  Optional volatility engine.
            backtesting_engine: Optional backtesting engine.

        Returns:
            Configured RegimeEngine.
        """
        config = config or RegimeConfig()
        feature_extractor = feature_extractor or FeatureExtractor()
        return RegimeEngine(
            config=config,
            feature_extractor=feature_extractor,
            strategy_engine=strategy_engine,
            sizing_engine=sizing_engine,
            portfolio_engine=portfolio_engine,
            risk_engine=risk_engine,
            volatility_engine=volatility_engine,
            backtesting_engine=backtesting_engine,
        )

    @staticmethod
    def create_with_detectors(
        detectors: dict[str, Any],
        config: RegimeConfig | None = None,
    ) -> RegimeEngine:
        """Create with custom detectors.

        Args:
            detectors: Custom detectors (name -> instance).
            config:    Configuration (defaults created).

        Returns:
            RegimeEngine.
        """
        return RegimeEngine(config=config, detectors=detectors)

    @staticmethod
    def create_from_config(
        config: RegimeConfig,
    ) -> RegimeEngine:
        """Create from configuration.

        Args:
            config: Configuration.

        Returns:
            RegimeEngine.
        """
        return RegimeEngine(config=config)
