"""Intelligence engine.

Main orchestrator integrating model selection, ensemble building,
learning updates, confidence scoring, and adaptive recommendations.
"""

from __future__ import annotations

from typing import Any

from backend.intelligence.confidence import ConfidenceEngine
from backend.intelligence.ensemble import EnsembleEngine
from backend.intelligence.evaluation import MetricsCalculator
from backend.intelligence.exceptions import InsufficientDataError
from backend.intelligence.learning import LearningEngine
from backend.intelligence.models import (
    AdaptiveRecommendation,
    EnsembleModel,
    EnsembleResult,
    EvaluationRequest,
    EvaluationResult,
    IntelligenceConfig,
    WeightingStrategy,
)
from backend.intelligence.selection import ChampionChallengerSelector


class IntelligenceEngine:
    """Main intelligence engine for adaptive model evaluation and selection.

    Integrates:
    - Champion-Challenger model selection
    - Multi-strategy ensemble building
    - Continuous learning and weight updates
    - Confidence scoring with evidence
    - Adaptive recommendations for downstream engines
    """

    def __init__(
        self,
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
    ) -> None:
        """Initialize the intelligence engine.

        Args:
            config:            Configuration (defaults created).
            metrics_calculator: Metrics calculator (defaults created).
            selector:           Champion-challenger selector (defaults created).
            ensemble:           Ensemble engine (defaults created).
            learning:           Learning engine (defaults created).
            confidence:         Confidence engine (defaults created).
            strategy_engine:    Optional strategy engine for integration.
            ranking_engine:     Optional ranking engine for integration.
            regime_engine:      Optional regime engine for integration.
            volatility_engine:  Optional volatility engine for integration.
        """
        from backend.intelligence.confidence import ConfidenceEngine as _Confidence
        from backend.intelligence.ensemble import EnsembleEngine as _Ensemble
        from backend.intelligence.evaluation import MetricsCalculator as _Metrics
        from backend.intelligence.learning import LearningEngine as _Learning
        from backend.intelligence.selection import ChampionChallengerSelector as _Selector

        self._config = config or IntelligenceConfig()
        self._metrics = metrics_calculator or _Metrics()
        self._selector = selector or _Selector(self._config)
        self._ensemble = ensemble or _Ensemble(self._config)
        self._learning = learning or _Learning(self._config)
        self._confidence = confidence or _Confidence(self._config)
        self._strategy_engine = strategy_engine
        self._ranking_engine = ranking_engine
        self._regime_engine = regime_engine
        self._volatility_engine = volatility_engine

    @property
    def config(self) -> IntelligenceConfig:
        return self._config

    @property
    def selector(self) -> ChampionChallengerSelector:
        return self._selector

    @property
    def ensemble(self) -> EnsembleEngine:
        return self._ensemble

    @property
    def learning(self) -> LearningEngine:
        return self._learning

    @property
    def confidence(self) -> ConfidenceEngine:
        return self._confidence

    # ======================= Core Methods =======================

    def evaluate(
        self,
        request: EvaluationRequest,
    ) -> EvaluationResult:
        """Evaluate a model's predictions against actuals.

        Args:
            request: Evaluation request with predictions and actuals.

        Returns:
            EvaluationResult with all computed metrics.

        Raises:
            InsufficientDataError: If insufficient data for evaluation.
        """
        if len(request.predictions) < self._config.min_observations:
            raise InsufficientDataError(
                f"Need at least {self._config.min_observations} observations, "
                f"got {len(request.predictions)}"
            )
        result = self._selector.evaluate(request)
        score = self._composite_score(result, self._config.selection_criterion)
        self._learning.update(request.model_name, result, score)
        return result

    def select_best(
        self,
        criterion: str | None = None,
    ) -> tuple[str, EvaluationResult]:
        """Select the best model from champion and challengers.

        Args:
            criterion: Selection criterion (uses config default if None).

        Returns:
            Tuple of (model_name, evaluation_result).
        """
        from backend.intelligence.models import SelectionCriterion

        crit = SelectionCriterion(criterion) if criterion else self._config.selection_criterion
        return self._selector.select_best(crit)

    def build_ensemble(
        self,
        models: tuple[EnsembleModel, ...],
        strategy: WeightingStrategy | None = None,
        regime: str | None = None,
    ) -> EnsembleResult:
        """Build an ensemble from multiple models.

        Args:
            models:   Models to include in ensemble.
            strategy: Weighting strategy (uses config default if None).
            regime:   Current market regime for regime-aware weighting.

        Returns:
            EnsembleResult with combined prediction and confidence.
        """
        return self._ensemble.build(models, strategy, regime)

    def update_learning(
        self,
        name: str,
        result: EvaluationResult,
        score: float,
    ) -> None:
        """Update learning engine with new evaluation result.

        Args:
            name:   Model name.
            result: Evaluation result.
            score:  Composite performance score.
        """
        self._learning.update(name, result, score)

    def evaluate_confidence(
        self,
        prediction: float,
        predictions: dict[str, float],
        evaluations: dict[str, EvaluationResult],
    ) -> tuple[float, dict[str, float], dict[str, float]]:
        """Compute confidence for a prediction.

        Args:
            prediction:  Final ensemble prediction.
            predictions: Individual model predictions.
            evaluations: Model name -> evaluation result.

        Returns:
            Tuple of (confidence, supporting_evidence, alternative_models).
        """
        histories = {
            name: self._learning.get_history(name)
            for name in predictions
            if self._learning.get_history(name) is not None
        }
        score = self._confidence.evaluate(
            prediction, predictions, evaluations, histories
        )
        return score.confidence, score.supporting_evidence, score.historical_reliability

    def adaptive_recommendation(
        self,
        context: dict[str, Any] | None = None,
    ) -> AdaptiveRecommendation:
        """Generate an adaptive recommendation for downstream engines.

        Args:
            context: Optional context (regime, portfolio state, etc.).

        Returns:
            AdaptiveRecommendation with confidence and reasoning.
        """
        regime = "UNKNOWN"
        if self._regime_engine and hasattr(self._regime_engine, "detect"):
            try:
                regime_result = self._regime_engine.detect()
                regime = getattr(regime_result, "regime", "UNKNOWN")
            except Exception:
                pass

        champ = self._selector.champion
        recommendation = "Maintain current allocation"
        confidence = 0.5
        reasoning: list[str] = []

        if champ:
            recommendation = f"Follow {champ.name} champion model"
            confidence = champ.evaluation.hit_ratio * 0.5 + champ.stability * 0.5
            reasoning.append(f"Champion: {champ.name} (Sharpe: {champ.evaluation.sharpe:.2f})")
            reasoning.append(f"Win rate: {champ.win_rate:.1%}")
            reasoning.append(f"Stability: {champ.stability:.2f}")

        if self._strategy_engine:
            reasoning.append("Strategy engine available for detailed signals")
        if self._ranking_engine:
            reasoning.append("Ranking engine available for factor analysis")

        return AdaptiveRecommendation(
            recommendation=recommendation,
            confidence=min(1.0, max(0.0, confidence)),
            reasoning=tuple(reasoning),
            alternatives=("Reduce exposure", "Increase hedging", "Hold cash"),
            source_models=(champ.name,) if champ else (),
            regime=regime,
            urgency=0.3,
        )

    def _composite_score(
        self,
        result: EvaluationResult,
        criterion: str,
    ) -> float:
        from backend.intelligence.models import SelectionCriterion
        crit = SelectionCriterion(criterion)
        return self._selector._composite_score(result, crit)

    # ======================= Integration Helpers =======================

    def register_champion(
        self,
        name: str,
        evaluation: EvaluationResult | None = None,
    ) -> None:
        """Register a champion model."""
        self._selector.register_champion(name, evaluation)

    def register_challenger(
        self,
        name: str,
        evaluation: EvaluationResult | None = None,
    ) -> None:
        """Register a challenger model."""
        self._selector.register_challenger(name, evaluation)

    def check_replacement(self) -> tuple[bool, str | None]:
        """Check if champion should be replaced."""
        return self._selector.check_replacement()

    def promote_challenger(self, name: str) -> None:
        """Promote a challenger to champion."""
        self._selector.replace_champion(name)

    def get_performance_history(self, name: str) -> tuple[EvaluationResult, ...]:
        """Get evaluation history for a model."""
        return self._selector.get_history(name)
