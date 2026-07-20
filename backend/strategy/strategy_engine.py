"""
Strategy Engine.

Single public API for strategy evaluation.
Coordinates pipeline, registry, and strategy evaluation.
"""

from __future__ import annotations

from backend.strategy.models import (
    StrategyConfiguration,
    StrategyDecisionTrace,
    StrategyInput,
    StrategyResult,
    StrategyType,
)
from backend.strategy.pipeline import EvaluationPipeline
from backend.strategy.strategies import MomentumStrategy
from backend.strategy.strategy_registry import StrategyRegistry


class StrategyEngine:
    """Strategy Engine.

    Single public API: evaluate(StrategyInput) -> StrategyResult.
    """

    def __init__(self) -> None:
        self._pipeline = EvaluationPipeline()
        self._registry = StrategyRegistry()
        self._register_defaults()

    def _register_defaults(self) -> None:
        """Register built-in strategies."""
        self._registry.register(StrategyType.MOMENTUM, MomentumStrategy())

    def evaluate(self, strategy_input: StrategyInput) -> StrategyResult:
        """Evaluate a strategy for a symbol.

        Args:
            strategy_input: Full input with snapshots and configuration.

        Returns:
            StrategyResult with approval decision.

        Raises:
            ValueError: If strategy type is unknown.
        """
        config = strategy_input.configuration

        # Validate configuration
        self._validate_configuration(config)

        # Resolve strategy
        strategy = self._registry.resolve(config.strategy_type)
        if strategy is None:
            raise ValueError(f"Unknown strategy: {config.strategy_type}")

        # Run pipeline
        context = self._pipeline.run(strategy_input)

        # Evaluate strategy
        result = strategy.evaluate(context, config)

        # Build decision trace
        decision_trace = StrategyDecisionTrace(
            pipeline_source="EvaluationPipeline",
            strategy_source=type(strategy).__name__,
            approval_source="strategy.evaluate",
        )

        # Rebuild with trace
        return StrategyResult(
            summary=result.summary,
            context=result.context,
            decision_trace=decision_trace,
            validation_flags=result.validation_flags,
            reasons=result.reasons,
            warnings=result.warnings,
        )

    def _validate_configuration(self, config: StrategyConfiguration) -> None:
        """Validate strategy configuration.

        Raises:
            ValueError: If configuration is invalid.
        """
        if config.minimum_composite_score < 0:
            raise ValueError("minimum_composite_score must be non-negative")
        if config.minimum_confidence < 0 or config.minimum_confidence > 100:
            raise ValueError("minimum_confidence must be between 0 and 100")
