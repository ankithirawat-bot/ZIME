"""Ensemble engine.

Combines multiple model predictions using various weighting strategies
including weighted average, voting, confidence weighting, performance
weighting, regime-aware weighting, and adaptive weighting.
"""

from __future__ import annotations

import math

from backend.intelligence.exceptions import EnsembleError
from backend.intelligence.models import (
    EnsembleModel,
    EnsembleResult,
    IntelligenceConfig,
    WeightingStrategy,
)


class EnsembleEngine:
    """Ensemble engine combining multiple model predictions."""

    def __init__(
        self,
        config: IntelligenceConfig | None = None,
    ) -> None:
        self._config = config or IntelligenceConfig()

    @property
    def config(self) -> IntelligenceConfig:
        return self._config

    def build(
        self,
        models: tuple[EnsembleModel, ...],
        strategy: WeightingStrategy | None = None,
        regime: str | None = None,
    ) -> EnsembleResult:
        """Build an ensemble from models using the specified strategy.

        Args:
            models:   Models to include in ensemble.
            strategy: Weighting strategy (defaults to config).
            regime:   Current market regime (for regime-aware weighting).

        Returns:
            EnsembleResult with combined prediction.

        Raises:
            EnsembleError: If no models provided.
        """
        if not models:
            raise EnsembleError("No models provided for ensemble")

        strategy = strategy or self._config.weighting_strategy

        if strategy == WeightingStrategy.WEIGHTED_AVERAGE:
            weights = self._weighted_average(models)
        elif strategy == WeightingStrategy.WEIGHTED_VOTING:
            weights = self._weighted_voting(models)
        elif strategy == WeightingStrategy.CONFIDENCE_WEIGHTING:
            weights = self._confidence_weighting(models)
        elif strategy == WeightingStrategy.PERFORMANCE_WEIGHTING:
            weights = self._performance_weighting(models)
        elif strategy == WeightingStrategy.REGIME_AWARE_WEIGHTING:
            weights = self._regime_aware_weighting(models, regime)
        elif strategy == WeightingStrategy.ADAPTIVE_WEIGHTING:
            weights = self._adaptive_weighting(models)
        else:
            weights = self._equal_weights(models)

        prediction = sum(m.score * weights.get(m.name, 0.0) for m in models)
        total_weight = sum(weights.values())
        if total_weight > 0:
            prediction /= total_weight

        component_predictions = {m.name: m.score for m in models}
        component_weights = dict(weights)
        confidence = self._ensemble_confidence(models, weights, prediction)
        diversity = self._diversity_score(models)

        return EnsembleResult(
            prediction=prediction,
            confidence=confidence,
            component_predictions=component_predictions,
            component_weights=component_weights,
            strategy=strategy,
            model_count=len(models),
            diversity_score=diversity,
        )

    def _equal_weights(
        self,
        models: tuple[EnsembleModel, ...],
    ) -> dict[str, float]:
        w = 1.0 / len(models)
        return {m.name: w for m in models}

    def _weighted_average(
        self,
        models: tuple[EnsembleModel, ...],
    ) -> dict[str, float]:
        return {m.name: m.weight for m in models}

    def _weighted_voting(
        self,
        models: tuple[EnsembleModel, ...],
    ) -> dict[str, float]:
        total = sum(m.weight for m in models)
        if total <= 0:
            return self._equal_weights(models)
        return {m.name: m.weight / total for m in models}

    def _confidence_weighting(
        self,
        models: tuple[EnsembleModel, ...],
    ) -> dict[str, float]:
        total_conf = sum(m.confidence for m in models)
        if total_conf <= 0:
            return self._equal_weights(models)
        return {m.name: m.confidence / total_conf for m in models}

    def _performance_weighting(
        self,
        models: tuple[EnsembleModel, ...],
    ) -> dict[str, float]:
        total_score = sum(max(0, m.score) for m in models)
        if total_score <= 0:
            return self._equal_weights(models)
        return {m.name: max(0, m.score) / total_score for m in models}

    def _regime_aware_weighting(
        self,
        models: tuple[EnsembleModel, ...],
        regime: str | None,
    ) -> dict[str, float]:
        if regime is None:
            return self._performance_weighting(models)
        regime_weights: dict[str, float] = {}
        for m in models:
            base = max(0, m.score)
            if m.confidence > 0.8:
                base *= 1.2
            regime_weights[m.name] = base
        total = sum(regime_weights.values())
        if total <= 0:
            return self._equal_weights(models)
        return {k: v / total for k, v in regime_weights.items()}

    def _adaptive_weighting(
        self,
        models: tuple[EnsembleModel, ...],
    ) -> dict[str, float]:
        scores = [max(0, m.score) for m in models]
        confs = [m.confidence for m in models]
        combined = [
            (s * 0.6 + c * 0.4) if (s + c) > 0 else 0.0
            for s, c in zip(scores, confs)
        ]
        total = sum(combined)
        if total <= 0:
            return self._equal_weights(models)
        return {models[i].name: combined[i] / total for i in range(len(models))}

    def _ensemble_confidence(
        self,
        models: tuple[EnsembleModel, ...],
        weights: dict[str, float],
        prediction: float,
    ) -> float:
        if len(models) < 2:
            return models[0].confidence if models else 0.0
        weighted_conf = sum(
            m.confidence * weights.get(m.name, 0.0) for m in models
        )
        total_weight = sum(weights.values())
        if total_weight > 0:
            weighted_conf /= total_weight
        predictions = [m.score for m in models]
        variance = _variance(tuple(predictions))
        diversity_factor = 1.0 / (1.0 + math.sqrt(variance))
        return min(1.0, weighted_conf * diversity_factor)

    def _diversity_score(
        self,
        models: tuple[EnsembleModel, ...],
    ) -> float:
        if len(models) < 2:
            return 0.0
        predictions = [m.score for m in models]
        cv = _coefficient_variation(tuple(predictions))
        return min(1.0, cv)

    def combine_predictions(
        self,
        predictions: dict[str, float],
        weights: dict[str, float] | None = None,
    ) -> float:
        """Combine raw predictions using provided weights.

        Args:
            predictions: Model name -> prediction value.
            weights:     Model name -> weight (equal weights if None).

        Returns:
            Combined prediction.
        """
        if not predictions:
            raise EnsembleError("No predictions to combine")
        if weights is None:
            w = 1.0 / len(predictions)
            weights = {k: w for k in predictions}
        total = sum(
            predictions[k] * weights.get(k, 0.0) for k in predictions
        )
        total_weight = sum(weights.get(k, 0.0) for k in predictions)
        if total_weight <= 0:
            return sum(predictions.values()) / len(predictions)
        return total / total_weight


def _variance(values: tuple[float, ...]) -> float:
    if len(values) < 2:
        return 0.0
    m = sum(values) / len(values)
    return sum((v - m) ** 2 for v in values) / (len(values) - 1)


def _coefficient_variation(values: tuple[float, ...]) -> float:
    if len(values) < 2:
        return 0.0
    m = sum(values) / len(values)
    if m == 0:
        return 0.0
    std = math.sqrt(_variance(values))
    return std / abs(m)
