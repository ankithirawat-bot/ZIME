"""Adaptive intelligence models.

Frozen dataclasses for model selection, ensemble configuration,
evaluation results, confidence scoring, and performance tracking.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from datetime import datetime
from enum import StrEnum
from typing import Any, Protocol, runtime_checkable


class WeightingStrategy(StrEnum):
    """Ensemble weighting strategies."""

    WEIGHTED_AVERAGE = "WEIGHTED_AVERAGE"
    WEIGHTED_VOTING = "WEIGHTED_VOTING"
    CONFIDENCE_WEIGHTING = "CONFIDENCE_WEIGHTING"
    PERFORMANCE_WEIGHTING = "PERFORMANCE_WEIGHTING"
    REGIME_AWARE_WEIGHTING = "REGIME_AWARE_WEIGHTING"
    ADAPTIVE_WEIGHTING = "ADAPTIVE_WEIGHTING"


class SelectionCriterion(StrEnum):
    """Model selection criteria."""

    BEST_PERFORMANCE = "BEST_PERFORMANCE"
    HIGHEST_SHARPE = "HIGHEST_SHARPE"
    LOWEST_RISK = "LOWEST_RISK"
    HIGHEST_CONFIDENCE = "HIGHEST_CONFIDENCE"
    BEST_ROLLING = "BEST_ROLLING"
    MOST_STABLE = "MOST_STABLE"


@dataclass(frozen=True)
class IntelligenceMetadata:
    """Metadata for the intelligence platform.

    Attributes:
        name:         Platform name.
        description:  Description.
        version:      Schema version.
        author:       Author.
        created_at:   Creation timestamp.
        tags:         Searchable tags.
    """

    name: str = ""
    description: str = ""
    version: str = "1.0"
    author: str = ""
    created_at: datetime = field(default_factory=lambda: datetime.now().astimezone())
    tags: tuple[str, ...] = field(default_factory=tuple)


@dataclass(frozen=True)
class IntelligenceConfig:
    """Configuration for the intelligence platform.

    Attributes:
        min_observations:        Minimum observations for evaluation.
        rolling_window:          Rolling evaluation window.
        decay_half_life:         Performance decay half-life.
        champion_min_periods:    Minimum periods as champion.
        confidence_threshold:    Minimum confidence threshold.
        performance_weight:      Performance weighting factor.
        stability_weight:        Stability weighting factor.
        diversity_weight:        Diversity weighting factor.
        max_ensemble_models:     Maximum models in ensemble.
        learning_rate:           Learning rate for weight updates.
        selection_criterion:     Default selection criterion.
        weighting_strategy:      Default weighting strategy.
        regime_adaptation:       Enable regime-aware adaptation.
    """

    min_observations: int = 20
    rolling_window: int = 60
    decay_half_life: int = 30
    champion_min_periods: int = 10
    confidence_threshold: float = 0.60
    performance_weight: float = 0.40
    stability_weight: float = 0.35
    diversity_weight: float = 0.25
    max_ensemble_models: int = 5
    learning_rate: float = 0.05
    selection_criterion: SelectionCriterion = SelectionCriterion.BEST_PERFORMANCE
    weighting_strategy: WeightingStrategy = WeightingStrategy.ADAPTIVE_WEIGHTING
    regime_adaptation: bool = True


@dataclass(frozen=True)
class EvaluationRequest:
    """Request to evaluate a model or signal.

    Attributes:
        model_name:    Model or signal name.
        predictions:   Model predictions.
        actuals:       Actual values.
        weights:       Optional sample weights.
        metadata:      Additional evaluation metadata.
        timestamp:     Evaluation timestamp.
    """

    model_name: str
    predictions: tuple[float, ...]
    actuals: tuple[float, ...]
    weights: tuple[float, ...] | None = None
    metadata: dict[str, Any] = field(default_factory=dict)
    timestamp: datetime = field(default_factory=lambda: datetime.now().astimezone())


@dataclass(frozen=True)
class EvaluationResult:
    """Result of a model evaluation.

    Attributes:
        model_name:       Model name.
        rmse:             Root mean squared error.
        mae:              Mean absolute error.
        mape:             Mean absolute percentage error.
        sharpe:           Sharpe ratio.
        sortino:          Sortino ratio.
        hit_ratio:        Hit rate.
        precision:        Precision.
        recall:           Recall.
        f1:               F1 score.
        max_drawdown:     Maximum drawdown.
        cagr:             Compound annual growth rate.
        rolling_rmse:     Rolling RMSE series.
        rolling_sharpe:   Rolling Sharpe series.
        sample_count:     Number of samples.
        metadata:         Additional result metadata.
        timestamp:        Evaluation timestamp.
    """

    model_name: str = ""
    rmse: float = 0.0
    mae: float = 0.0
    mape: float = 0.0
    sharpe: float = 0.0
    sortino: float = 0.0
    hit_ratio: float = 0.0
    precision: float = 0.0
    recall: float = 0.0
    f1: float = 0.0
    max_drawdown: float = 0.0
    cagr: float = 0.0
    rolling_rmse: tuple[float, ...] = field(default_factory=tuple)
    rolling_sharpe: tuple[float, ...] = field(default_factory=tuple)
    sample_count: int = 0
    metadata: dict[str, Any] = field(default_factory=dict)
    timestamp: datetime = field(default_factory=lambda: datetime.now().astimezone())


@dataclass(frozen=True)
class ChampionModel:
    """Current champion model.

    Attributes:
        name:           Model name.
        evaluation:     Latest evaluation result.
        champion_since: When it became champion.
        total_periods:  Total periods as champion.
        win_rate:       Win rate against challengers.
        stability:      Stability score.
        performance_trend: Performance trend direction.
    """

    name: str = ""
    evaluation: EvaluationResult = field(default_factory=EvaluationResult)
    champion_since: datetime = field(default_factory=lambda: datetime.now().astimezone())
    total_periods: int = 0
    win_rate: float = 0.0
    stability: float = 0.0
    performance_trend: float = 0.0


@dataclass(frozen=True)
class ChallengerModel:
    """Challenger model being evaluated against champion.

    Attributes:
        name:           Model name.
        evaluation:     Latest evaluation result.
        challenges:     Number of challenges performed.
        best_score:     Best evaluation score achieved.
        consistency:    Consistency score across challenges.
        improvement:    Improvement trend.
    """

    name: str = ""
    evaluation: EvaluationResult = field(default_factory=EvaluationResult)
    challenges: int = 0
    best_score: float = 0.0
    consistency: float = 0.0
    improvement: float = 0.0


@dataclass(frozen=True)
class EnsembleModel:
    """Model participating in an ensemble.

    Attributes:
        name:       Model name.
        weight:     Ensemble weight.
        score:      Individual performance score.
        confidence: Model confidence.
    """

    name: str
    weight: float
    score: float = 0.0
    confidence: float = 0.0


@dataclass(frozen=True)
class EnsembleResult:
    """Result of an ensemble computation.

    Attributes:
        prediction:           Final ensemble prediction.
        confidence:           Ensemble confidence.
        component_predictions: Individual model predictions.
        component_weights:    Individual model weights.
        strategy:             Weighting strategy used.
        model_count:          Number of models in ensemble.
        diversity_score:      Diversity of ensemble components.
        metadata:             Additional ensemble metadata.
    """

    prediction: float = 0.0
    confidence: float = 0.0
    component_predictions: dict[str, float] = field(default_factory=dict)
    component_weights: dict[str, float] = field(default_factory=dict)
    strategy: WeightingStrategy = WeightingStrategy.WEIGHTED_AVERAGE
    model_count: int = 0
    diversity_score: float = 0.0
    metadata: dict[str, Any] = field(default_factory=dict)


@dataclass(frozen=True)
class ConfidenceScore:
    """Confidence scoring result.

    Attributes:
        prediction:          Final prediction.
        confidence:          Confidence level (0 to 1).
        supporting_evidence: Evidence supporting the prediction.
        alternative_models:  Alternative models considered.
        historical_reliability: Historical reliability score.
        recommendation_strength: Strength of recommendation.
        model_count:         Number of models analyzed.
        timestamp:           Computation timestamp.
    """

    prediction: float = 0.0
    confidence: float = 0.0
    supporting_evidence: dict[str, float] = field(default_factory=dict)
    alternative_models: tuple[str, ...] = field(default_factory=tuple)
    historical_reliability: float = 0.0
    recommendation_strength: float = 0.0
    model_count: int = 0
    timestamp: datetime = field(default_factory=lambda: datetime.now().astimezone())


@dataclass(frozen=True)
class PerformanceHistory:
    """Historical performance tracking.

    Attributes:
        model_name:    Model name.
        evaluations:   Historical evaluation results.
        scores:        Historical performance scores.
        weights:       Historical weights.
        rankings:      Historical rankings.
        decay_rate:    Detected decay rate.
        adaptive_score: Current adaptive score.
        last_updated:  Last update timestamp.
    """

    model_name: str = ""
    evaluations: tuple[EvaluationResult, ...] = field(default_factory=tuple)
    scores: tuple[float, ...] = field(default_factory=tuple)
    weights: tuple[float, ...] = field(default_factory=tuple)
    rankings: tuple[int, ...] = field(default_factory=tuple)
    decay_rate: float = 0.0
    adaptive_score: float = 0.0
    last_updated: datetime = field(default_factory=lambda: datetime.now().astimezone())


@dataclass(frozen=True)
class AdaptiveRecommendation:
    """Adaptive recommendation from the intelligence platform.

    Attributes:
        recommendation:  Recommendation text.
        confidence:      Recommendation confidence.
        reasoning:       Supporting reasoning.
        alternatives:    Alternative recommendations.
        source_models:   Models contributing to recommendation.
        regime:          Current detected regime.
        urgency:         Recommendation urgency (0 to 1).
        timestamp:       Recommendation timestamp.
    """

    recommendation: str = ""
    confidence: float = 0.0
    reasoning: tuple[str, ...] = field(default_factory=tuple)
    alternatives: tuple[str, ...] = field(default_factory=tuple)
    source_models: tuple[str, ...] = field(default_factory=tuple)
    regime: str = "UNKNOWN"
    urgency: float = 0.0
    timestamp: datetime = field(default_factory=lambda: datetime.now().astimezone())


@runtime_checkable
class EvaluatableModel(Protocol):
    """Protocol for models that can be evaluated by the intelligence platform."""

    @property
    def name(self) -> str:
        ...

    def predict(self, input_data: Any) -> Any:
        ...

    def evaluate(self, request: EvaluationRequest) -> EvaluationResult:
        ...
