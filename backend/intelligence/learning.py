"""Learning engine for continuous adaptation.

Maintains performance history, computes rolling statistics,
detects performance decay, updates model weights, and
maintains historical rankings with adaptive scores.
"""

from __future__ import annotations

import math
from datetime import datetime

from backend.intelligence.models import (
    EvaluationResult,
    IntelligenceConfig,
    PerformanceHistory,
)


class LearningEngine:
    """Continuous learning engine for model adaptation.

    Tracks performance history across evaluations, detects decay,
    updates weights adaptively, and maintains rankings.
    """

    def __init__(
        self,
        config: IntelligenceConfig | None = None,
    ) -> None:
        self._config = config or IntelligenceConfig()
        self._history: dict[str, PerformanceHistory] = {}
        self._latest_scores: dict[str, float] = {}

    @property
    def config(self) -> IntelligenceConfig:
        return self._config

    def update(
        self,
        name: str,
        result: EvaluationResult,
        score: float,
    ) -> PerformanceHistory:
        """Update performance history with a new evaluation.

        Args:
            name:   Model name.
            result: Evaluation result.
            score:  Composite performance score.

        Returns:
            Updated PerformanceHistory.
        """
        prev = self._history.get(name)

        evaluations: tuple[EvaluationResult, ...] = (result,)
        scores: tuple[float, ...] = (score,)
        weights: tuple[float, ...] = (1.0,)
        rankings: tuple[int, ...] = (1,)

        if prev:
            evaluations = prev.evaluations + (result,)
            scores = prev.scores + (score,)
            weights = self._compute_weights(name, prev, score)
            rankings = self._compute_rankings()

        decay = self._detect_decay(scores)
        adaptive = self._compute_adaptive_score(scores, weights)

        history = PerformanceHistory(
            model_name=name,
            evaluations=evaluations,
            scores=scores,
            weights=weights,
            rankings=rankings,
            decay_rate=decay,
            adaptive_score=adaptive,
            last_updated=datetime.now().astimezone(),
        )
        self._history[name] = history
        self._latest_scores[name] = score
        return history

    def _compute_weights(
        self,
        name: str,
        prev: PerformanceHistory,
        current_score: float,
    ) -> tuple[float, ...]:
        scores = prev.scores + (current_score,)
        recent = scores[-self._config.rolling_window:] if len(scores) > self._config.rolling_window else scores
        total = sum(max(0, s) for s in recent)
        if total <= 0:
            return prev.weights + (1.0,)
        raw_weights = tuple(max(0, s) / total for s in recent)
        return raw_weights

    def _compute_rankings(self) -> tuple[int, ...]:
        if not self._latest_scores:
            return (1,)
        sorted_names = sorted(
            self._latest_scores, key=lambda n: self._latest_scores[n], reverse=True
        )
        current_rankings: list[int] = []
        for name in self._latest_scores:
            rank = sorted_names.index(name) + 1
            current_rankings.append(rank)
        return tuple(current_rankings)

    def get_history(self, name: str) -> PerformanceHistory | None:
        """Get performance history for a model.

        Args:
            name: Model name.

        Returns:
            PerformanceHistory or None.
        """
        return self._history.get(name)

    def rolling_statistics(
        self,
        name: str,
        window: int | None = None,
    ) -> dict[str, float]:
        """Compute rolling statistics from performance history.

        Args:
            name:   Model name.
            window: Rolling window (defaults to config).

        Returns:
            Dict of statistic name -> value.
        """
        prev = self._history.get(name)
        if prev is None or len(prev.scores) == 0:
            return {
                "mean": 0.0,
                "std": 0.0,
                "min": 0.0,
                "max": 0.0,
                "recent_mean": 0.0,
                "trend": 0.0,
            }

        window = window or self._config.rolling_window
        scores = prev.scores
        recent = scores[-window:] if len(scores) > window else scores

        mean = sum(scores) / len(scores)
        std = _stdev(scores)
        recent_mean = sum(recent) / len(recent)
        trend = self._compute_trend(scores)

        return {
            "mean": mean,
            "std": std,
            "min": min(scores),
            "max": max(scores),
            "recent_mean": recent_mean,
            "trend": trend,
        }

    def detect_decay(
        self,
        name: str,
        threshold: float = -0.05,
    ) -> bool:
        """Detect if a model's performance is decaying.

        Args:
            name:      Model name.
            threshold: Decay threshold.

        Returns:
            True if decay detected.
        """
        prev = self._history.get(name)
        if prev is None:
            return False
        return prev.decay_rate < threshold

    def _detect_decay(
        self,
        scores: tuple[float, ...],
    ) -> float:
        if len(scores) < self._config.min_observations:
            return 0.0
        recent = scores[-self._config.min_observations:]
        decay = self._compute_trend(recent)
        return decay

    def weight_updates(
        self,
        name: str,
    ) -> tuple[float, ...]:
        """Get weight history for a model.

        Args:
            name: Model name.

        Returns:
            Tuple of historical weights.
        """
        prev = self._history.get(name)
        if prev is None:
            return (1.0,)
        return prev.weights

    def historical_rankings(
        self,
        name: str,
    ) -> tuple[int, ...]:
        """Get historical rankings for a model.

        Args:
            name: Model name.

        Returns:
            Tuple of historical rankings.
        """
        prev = self._history.get(name)
        if prev is None:
            return (1,)
        return prev.rankings

    def adaptive_score(self, name: str) -> float:
        """Get current adaptive score for a model.

        Args:
            name: Model name.

        Returns:
            Adaptive score.
        """
        prev = self._history.get(name)
        if prev is None:
            return 0.0
        return prev.adaptive_score

    def _compute_adaptive_score(
        self,
        scores: tuple[float, ...],
        weights: tuple[float, ...],
    ) -> float:
        if not scores:
            return 0.0
        recent = scores[-min(len(scores), self._config.rolling_window):]
        if not recent:
            return 0.0
        weighted_sum = sum(
            s * w for s, w in zip(recent, weights[-len(recent):])
        )
        total_weight = sum(weights[-len(recent):])
        if total_weight <= 0:
            return sum(recent) / len(recent)
        return weighted_sum / total_weight

    def _compute_trend(
        self,
        scores: tuple[float, ...],
    ) -> float:
        if len(scores) < 2:
            return 0.0
        n = len(scores)
        x_mean = (n - 1) / 2.0
        y_mean = sum(scores) / n
        num = sum((i - x_mean) * (scores[i] - y_mean) for i in range(n))
        den = sum((i - x_mean) ** 2 for i in range(n))
        return num / den if den > 0 else 0.0


def _stdev(values: tuple[float, ...]) -> float:
    if len(values) < 2:
        return 0.0
    m = sum(values) / len(values)
    return math.sqrt(sum((v - m) ** 2 for v in values) / (len(values) - 1))
