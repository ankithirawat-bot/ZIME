"""Intelligence factory.

Constructs fully configured intelligence engines using dependency injection.
"""

from __future__ import annotations

from typing import Any

from backend.intelligence.confidence import ConfidenceEngine
from backend.intelligence.engine import IntelligenceEngine
from backend.intelligence.ensemble import EnsembleEngine
from backend.intelligence.evaluation import MetricsCalculator
from backend.intelligence.learning import LearningEngine
from backend.intelligence.models import IntelligenceConfig
from backend.intelligence.selection import ChampionChallengerSelector


class IntelligenceFactory:
    """Factory for constructing configured IntelligenceEngine instances."""

    @staticmethod
    def create(
        config: IntelligenceConfig | None = None,
        metrics_calculator: MetricsCalculator | None = None,
        selector: ChampionChallengerSelector | None = None,
        ensemble: EnsembleEngine | None = None,
        learning: LearningEngine | None = None,
        confidence: ConfidenceEngine | None = None,
        strategy_engine: Any | None = None,
        ranking_engine: Any | None = None,
        regime_engine: Any | None = None,
        volatility_engine: Any | None = None,
    ) -> IntelligenceEngine:
        """Create a fully configured IntelligenceEngine.

        Args:
            config:              Configuration (defaults created).
            metrics_calculator:  Metrics calculator (defaults created).
            selector:            Champion-challenger selector (defaults created).
            ensemble:            Ensemble engine (defaults created).
            learning:            Learning engine (defaults created).
            confidence:          Confidence engine (defaults created).
            strategy_engine:     Optional strategy engine.
            ranking_engine:      Optional ranking engine.
            regime_engine:       Optional regime engine.
            volatility_engine:   Optional volatility engine.

        Returns:
            Configured IntelligenceEngine.
        """
        config = config or IntelligenceConfig()
        metrics = metrics_calculator or MetricsCalculator()
        selector = selector or ChampionChallengerSelector(config)
        ensemble = ensemble or EnsembleEngine(config)
        learning = learning or LearningEngine(config)
        confidence = confidence or ConfidenceEngine(config)

        return IntelligenceEngine(
            config=config,
            metrics_calculator=metrics,
            selector=selector,
            ensemble=ensemble,
            learning=learning,
            confidence=confidence,
            strategy_engine=strategy_engine,
            ranking_engine=ranking_engine,
            regime_engine=regime_engine,
            volatility_engine=volatility_engine,
        )

    @staticmethod
    def create_with_engines(
        engines: dict[str, Any],
        config: IntelligenceConfig | None = None,
    ) -> IntelligenceEngine:
        """Create with pre-configured sub-engines.

        Args:
            engines: Dict with keys: metrics, selector, ensemble, learning, confidence.
            config:  Configuration (defaults created).

        Returns:
            IntelligenceEngine.
        """
        return IntelligenceFactory.create(
            config=config,
            metrics_calculator=engines.get("metrics"),
            selector=engines.get("selector"),
            ensemble=engines.get("ensemble"),
            learning=engines.get("learning"),
            confidence=engines.get("confidence"),
        )

    @staticmethod
    def create_from_config(
        config: IntelligenceConfig,
    ) -> IntelligenceEngine:
        """Create from configuration only.

        Args:
            config: Configuration.

        Returns:
            IntelligenceEngine with defaults.
        """
        return IntelligenceFactory.create(config=config)
