"""Champion-Challenger model selection.

Manages model evaluation, champion selection, challenger promotion,
performance decay detection, and stability scoring.
"""

from __future__ import annotations

import math
from datetime import datetime

from backend.intelligence.evaluation import MetricsCalculator
from backend.intelligence.exceptions import (
    ModelNotFoundError,
    SelectionError,
)
from backend.intelligence.models import (
    ChallengerModel,
    ChampionModel,
    EvaluationRequest,
    EvaluationResult,
    IntelligenceConfig,
    SelectionCriterion,
)


class ChampionChallengerSelector:
    """Champion-Challenger model selection system.

    Manages champion and challenger models, performs rolling evaluation,
    detects performance decay, and promotes challengers when they
    outperform the champion.
    """

    def __init__(
        self,
        config: IntelligenceConfig | None = None,
        calculator: MetricsCalculator | None = None,
    ) -> None:
        self._config = config or IntelligenceConfig()
        self._calculator = calculator or MetricsCalculator()
        self._champion: ChampionModel | None = None
        self._challengers: dict[str, ChallengerModel] = {}
        self._evaluation_history: dict[str, tuple[EvaluationResult, ...]] = {}

    @property
    def config(self) -> IntelligenceConfig:
        return self._config

    @property
    def champion(self) -> ChampionModel | None:
        return self._champion

    @property
    def challengers(self) -> dict[str, ChallengerModel]:
        return dict(self._challengers)

    def register_champion(
        self,
        name: str,
        evaluation: EvaluationResult | None = None,
    ) -> ChampionModel:
        """Register or update the champion model.

        Args:
            name:       Champion model name.
            evaluation: Optional initial evaluation.

        Returns:
            ChampionModel instance.
        """
        champ = ChampionModel(
            name=name,
            evaluation=evaluation or EvaluationResult(model_name=name),
            champion_since=datetime.now().astimezone(),
            total_periods=0,
            win_rate=1.0,
            stability=1.0,
            performance_trend=0.0,
        )
        self._champion = champ
        return champ

    def register_challenger(
        self,
        name: str,
        evaluation: EvaluationResult | None = None,
    ) -> ChallengerModel:
        """Register a challenger model.

        Args:
            name:       Challenger model name.
            evaluation: Optional initial evaluation.

        Returns:
            ChallengerModel instance.
        """
        if name in self._challengers:
            raise SelectionError(f"Challenger already registered: {name}")
        eval_obj = evaluation or EvaluationResult(model_name=name)
        challenger = ChallengerModel(
            name=name,
            evaluation=eval_obj,
            # An evaluation supplied at registration counts as the first
            # observed challenge, allowing immediate comparison checks.
            challenges=1,
            best_score=self._composite_score(eval_obj, self._config.selection_criterion),
            consistency=1.0,
            improvement=0.0,
        )
        self._challengers[name] = challenger
        if evaluation is not None:
            existing = self._evaluation_history.get(name, ())
            self._evaluation_history[name] = existing + (evaluation,)
        return challenger

    def unregister_challenger(self, name: str) -> None:
        """Remove a challenger model."""
        if name not in self._challengers:
            raise ModelNotFoundError(name)
        del self._challengers[name]

    def _composite_score(
        self,
        result: EvaluationResult,
        criterion: SelectionCriterion,
    ) -> float:
        """Compute a composite selection score."""
        if criterion == SelectionCriterion.BEST_PERFORMANCE:
            return result.sharpe + result.hit_ratio - result.rmse * 0.1
        elif criterion == SelectionCriterion.HIGHEST_SHARPE:
            return result.sharpe
        elif criterion == SelectionCriterion.LOWEST_RISK:
            return -result.max_drawdown + result.sortino
        elif criterion == SelectionCriterion.HIGHEST_CONFIDENCE:
            return result.f1 + result.precision
        elif criterion == SelectionCriterion.BEST_ROLLING:
            rolling = result.rolling_sharpe
            return _mean(rolling) if rolling else result.sharpe
        elif criterion == SelectionCriterion.MOST_STABLE:
            rolling = result.rolling_sharpe
            if len(rolling) > 1:
                return result.sharpe / (1 + _stdev(rolling))
            return result.sharpe
        return result.sharpe

    def evaluate(
        self,
        request: EvaluationRequest,
    ) -> EvaluationResult:
        """Evaluate a model against the evaluation request.

        Args:
            request: Evaluation request.

        Returns:
            EvaluationResult.
        """
        result = self._calculator.evaluate(request)

        name = request.model_name
        history = list(self._evaluation_history.get(name, ()))
        history.append(result)
        self._evaluation_history[name] = tuple(history)

        if name in self._challengers:
            self._update_challenger(name, result)

        if self._champion and name == self._champion.name:
            self._update_champion(result)

        return result

    def _update_champion(self, result: EvaluationResult) -> None:
        if self._champion is None:
            return
        champ = self._champion
        history = self._evaluation_history.get(champ.name, ())
        trend = self._compute_trend(history)
        stability = self._compute_stability(history)
        self._champion = ChampionModel(
            name=champ.name,
            evaluation=result,
            champion_since=champ.champion_since,
            total_periods=champ.total_periods + 1,
            win_rate=champ.win_rate,
            stability=stability,
            performance_trend=trend,
        )

    def _update_challenger(self, name: str, result: EvaluationResult) -> None:
        challenger = self._challengers[name]
        score = self._composite_score(result, self._config.selection_criterion)
        history = self._evaluation_history.get(name, ())
        consistency = self._compute_consistency(history)
        improvement = self._compute_improvement(history)
        self._challengers[name] = ChallengerModel(
            name=name,
            evaluation=result,
            challenges=challenger.challenges + 1,
            best_score=max(challenger.best_score, score),
            consistency=consistency,
            improvement=improvement,
        )

    def select_best(
        self,
        criterion: SelectionCriterion | None = None,
    ) -> tuple[str, EvaluationResult]:
        """Select the best model from champion and challengers.

        Args:
            criterion: Selection criterion (defaults to config).

        Returns:
            Tuple of (model_name, evaluation_result).

        Raises:
            SelectionError: If no models are available.
        """
        crit = criterion or self._config.selection_criterion
        candidates: dict[str, EvaluationResult] = {}

        if self._champion:
            candidates[self._champion.name] = self._champion.evaluation

        for name, challenger in self._challengers.items():
            if challenger.challenges >= 1:
                candidates[name] = challenger.evaluation

        if not candidates:
            raise SelectionError("No models available for selection")

        best_name = max(
            candidates,
            key=lambda n: self._composite_score(candidates[n], crit),
        )
        return best_name, candidates[best_name]

    def check_replacement(self) -> tuple[bool, str | None]:
        """Check if a challenger should replace the champion.

        Returns:
            Tuple of (should_replace, challenger_name).
        """
        if not self._champion:
            return False, None

        champ_score = self._composite_score(
            self._champion.evaluation, self._config.selection_criterion,
        )

        for name, challenger in self._challengers.items():
            # Accept any challenger that has at least one observation recorded
            # (either via registration with an evaluation or via update).
            if challenger.challenges < 1:
                continue
            challenger_score = self._composite_score(
                challenger.evaluation, self._config.selection_criterion,
            )
            if challenger_score > champ_score * 1.1:
                return True, name

        return False, None

    def replace_champion(self, challenger_name: str) -> ChampionModel:
        """Promote a challenger to champion.

        Args:
            challenger_name: Name of challenger to promote.

        Returns:
            New ChampionModel.
        """
        if challenger_name not in self._challengers:
            raise ModelNotFoundError(challenger_name)

        challenger = self._challengers[challenger_name]
        champ = ChampionModel(
            name=challenger.name,
            evaluation=challenger.evaluation,
            champion_since=datetime.now().astimezone(),
            total_periods=0,
            win_rate=1.0,
            stability=0.5,
            performance_trend=0.0,
        )
        self._champion = champ
        del self._challengers[challenger_name]
        return champ

    def detect_decay(
        self,
        name: str,
        threshold: float = -0.1,
    ) -> bool:
        """Detect if a model's performance is decaying.

        Args:
            name:      Model name.
            threshold: Decay threshold (negative indicates decay).

        Returns:
            True if decay detected.
        """
        history = self._evaluation_history.get(name, ())
        if len(history) < self._config.min_observations:
            return False
        trend = self._compute_trend(history)
        return trend < threshold

    def stability_score(self, name: str) -> float:
        """Compute stability score for a model.

        Args:
            name: Model name.

        Returns:
            Stability score (0 to 1).
        """
        history = self._evaluation_history.get(name, ())
        return self._compute_stability(history)

    def _compute_trend(
        self,
        history: tuple[EvaluationResult, ...],
    ) -> float:
        if len(history) < 2:
            return 0.0
        scores = [
            self._composite_score(r, self._config.selection_criterion)
            for r in history
        ]
        n = len(scores)
        x_mean = (n - 1) / 2.0
        y_mean = sum(scores) / n
        num = sum((i - x_mean) * (scores[i] - y_mean) for i in range(n))
        den = sum((i - x_mean) ** 2 for i in range(n))
        return num / den if den > 0 else 0.0

    def _compute_stability(
        self,
        history: tuple[EvaluationResult, ...],
    ) -> float:
        if len(history) < 2:
            return 1.0
        scores = [
            self._composite_score(r, self._config.selection_criterion)
            for r in history
        ]
        std = _stdev(tuple(scores))
        mean = sum(scores) / len(scores)
        if mean == 0:
            return 0.5
        cv = std / abs(mean)
        return max(0.0, min(1.0, 1.0 - cv))

    def _compute_consistency(
        self,
        history: tuple[EvaluationResult, ...],
    ) -> float:
        if len(history) < 2:
            return 1.0
        scores = [
            self._composite_score(r, self._config.selection_criterion)
            for r in history
        ]
        n = len(scores)
        changes = sum(
            1 for i in range(1, n)
            if abs(scores[i] - scores[i - 1]) > 0.1 * max(abs(scores[i]), 0.01)
        )
        return 1.0 - (changes / max(n - 1, 1))

    def _compute_improvement(
        self,
        history: tuple[EvaluationResult, ...],
    ) -> float:
        if len(history) < 2:
            return 0.0
        scores = [
            self._composite_score(r, self._config.selection_criterion)
            for r in history
        ]
        return (scores[-1] - scores[0]) / max(abs(scores[0]), 0.01)

    def get_history(
        self,
        name: str,
    ) -> tuple[EvaluationResult, ...]:
        """Get evaluation history for a model.

        Args:
            name: Model name.

        Returns:
            Tuple of evaluation results.
        """
        return self._evaluation_history.get(name, ())


def _mean(values: tuple[float, ...]) -> float:
    return sum(values) / len(values) if values else 0.0


def _stdev(values: tuple[float, ...]) -> float:
    if len(values) < 2:
        return 0.0
    m = _mean(values)
    return math.sqrt(sum((v - m) ** 2 for v in values) / (len(values) - 1))
