"""Confidence scoring engine.

Computes prediction confidence with supporting evidence, alternative
model analysis, historical reliability, and recommendation strength.
"""

from __future__ import annotations

import math

from backend.intelligence.exceptions import ConfidenceError
from backend.intelligence.models import (
    ConfidenceScore,
    EvaluationResult,
    IntelligenceConfig,
    PerformanceHistory,
)


class ConfidenceEngine:
    """Confidence scoring for predictions and recommendations.

    Evaluates confidence based on model agreement, historical
    reliability, prediction consistency, and recommendation strength.
    """

    def __init__(
        self,
        config: IntelligenceConfig | None = None,
    ) -> None:
        self._config = config or IntelligenceConfig()

    @property
    def config(self) -> IntelligenceConfig:
        return self._config

    def evaluate(
        self,
        prediction: float,
        predictions: dict[str, float],
        evaluations: dict[str, EvaluationResult],
        histories: dict[str, PerformanceHistory] | None = None,
    ) -> ConfidenceScore:
        """Evaluate confidence for a prediction.

        Args:
            prediction:  Final ensemble prediction.
            predictions: Individual model predictions.
            evaluations: Model name -> evaluation result.
            histories:   Model name -> performance history (optional).

        Returns:
            ConfidenceScore with supporting evidence.
        """
        if not predictions:
            raise ConfidenceError("No predictions to evaluate confidence")

        supporting = self._supporting_evidence(predictions, evaluations)
        alternatives = self._alternative_models(predictions, evaluations)
        reliability = self._historical_reliability(evaluations, histories)
        strength = self._recommendation_strength(
            prediction, predictions, supporting, reliability,
        )
        confidence = self._compute_confidence(
            supporting, reliability, strength, len(predictions),
        )

        return ConfidenceScore(
            prediction=prediction,
            confidence=confidence,
            supporting_evidence=supporting,
            alternative_models=tuple(alternatives),
            historical_reliability=reliability,
            recommendation_strength=strength,
            model_count=len(predictions),
        )

    def _supporting_evidence(
        self,
        predictions: dict[str, float],
        evaluations: dict[str, EvaluationResult],
    ) -> dict[str, float]:
        evidence: dict[str, float] = {}
        for name, pred in predictions.items():
            eval_result = evaluations.get(name)
            if eval_result is None:
                continue
            sharpe_score = max(0, min(1, (eval_result.sharpe + 2) / 4))
            hit_score = eval_result.hit_ratio
            rmse_score = max(0, 1.0 - min(1, eval_result.rmse))
            evidence[name] = (sharpe_score + hit_score + rmse_score) / 3.0
        return evidence

    def _alternative_models(
        self,
        predictions: dict[str, float],
        evaluations: dict[str, EvaluationResult],
    ) -> list[str]:
        sorted_models = sorted(
            predictions.keys(),
            key=lambda n: evaluations.get(n, EvaluationResult()).sharpe
            if evaluations.get(n) else 0.0,
            reverse=True,
        )
        return sorted_models[:3]

    def _historical_reliability(
        self,
        evaluations: dict[str, EvaluationResult],
        histories: dict[str, PerformanceHistory] | None,
    ) -> float:
        if not evaluations:
            return 0.0
        avg_sharpe = sum(
            max(0, e.sharpe) for e in evaluations.values()
        ) / max(len(evaluations), 1)
        normalized_sharpe = max(0, min(1, (avg_sharpe + 2) / 4))

        if not histories:
            return normalized_sharpe

        stability_scores: list[float] = []
        for name, history in histories.items():
            if len(history.scores) > 1:
                std = _stdev(history.scores)
                mean = sum(history.scores) / len(history.scores)
                if mean != 0:
                    cv = std / abs(mean)
                    stability_scores.append(max(0, min(1, 1.0 - cv)))
        avg_stability = sum(stability_scores) / max(len(stability_scores), 1) if stability_scores else 0.5

        return (normalized_sharpe * 0.6 + avg_stability * 0.4)

    def _recommendation_strength(
        self,
        prediction: float,
        predictions: dict[str, float],
        evidence: dict[str, float],
        reliability: float,
    ) -> float:
        agreement = self._model_agreement(predictions)
        avg_evidence = sum(evidence.values()) / max(len(evidence), 1) if evidence else 0.0
        return (agreement * 0.4 + avg_evidence * 0.3 + reliability * 0.3)

    def _compute_confidence(
        self,
        evidence: dict[str, float],
        reliability: float,
        strength: float,
        model_count: int,
    ) -> float:
        avg_evidence = sum(evidence.values()) / max(len(evidence), 1) if evidence else 0.0
        model_factor = min(1.0, model_count / self._config.max_ensemble_models)
        confidence = (
            avg_evidence * 0.3
            + reliability * 0.3
            + strength * 0.2
            + model_factor * 0.2
        )
        return max(0.0, min(1.0, confidence))

    def _model_agreement(
        self,
        predictions: dict[str, float],
    ) -> float:
        if len(predictions) < 2:
            return 1.0
        values = list(predictions.values())
        mean = sum(values) / len(values)
        if mean == 0:
            return 0.5
        deviations = [abs(v - mean) / abs(mean) for v in values]
        avg_dev = sum(deviations) / len(deviations)
        return max(0.0, min(1.0, 1.0 - avg_dev))

    def evaluate_prediction_confidence(
        self,
        prediction: float,
        predictions: dict[str, float],
        evaluation: EvaluationResult,
        history: PerformanceHistory | None = None,
    ) -> ConfidenceScore:
        """Quick confidence evaluation for a single model prediction.

        Args:
            prediction:  Model prediction.
            predictions: All model predictions (single entry for one model).
            evaluation:  Model evaluation result.
            history:     Optional performance history.

        Returns:
            ConfidenceScore.
        """
        evals = {evaluation.model_name: evaluation}
        histories: dict[str, PerformanceHistory] | None = None
        if history is not None:
            histories = {evaluation.model_name: history}
        return self.evaluate(prediction, predictions, evals, histories)


def _stdev(values: tuple[float, ...]) -> float:
    if len(values) < 2:
        return 0.0
    m = sum(values) / len(values)
    return math.sqrt(sum((v - m) ** 2 for v in values) / (len(values) - 1))
