"""Sprint 41: Adaptive Intelligence Platform — Full Test Suite.

Comprehensive tests for intelligent model evaluation, selection,
ensemble building, learning, and confidence scoring.
"""

from __future__ import annotations

import math
from datetime import UTC, datetime

import pytest

from backend.intelligence.confidence import ConfidenceEngine
from backend.intelligence.engine import IntelligenceEngine
from backend.intelligence.ensemble import EnsembleEngine
from backend.intelligence.exceptions import (
    EnsembleError,
    EvaluationError,
    InsufficientDataError,
    ModelNotFoundError,
)
from backend.intelligence.factory import IntelligenceFactory
from backend.intelligence.learning import LearningEngine
from backend.intelligence.models import (
    AdaptiveRecommendation,
    ChallengerModel,
    ChampionChallengerSelector,
    ConfidenceScore,
    EnsembleModel,
    EnsembleResult,
    EvaluationRequest,
    EvaluationResult,
    IntelligenceConfig,
    IntelligenceMetadata,
    SelectionCriterion,
    WeightingStrategy,
)

# =========================================================================
# Helpers and Fixtures
# =========================================================================


def _prices(base: float = 100.0, count: int = 100, trend: float = 0.0) -> tuple[float, ...]:
    """Generate price series with optional trend."""
    prices = [base]
    for i in range(1, count):
        ret = trend + 0.01 * (2 * math.sin(i * 0.5))
        prices.append(prices[-1] * (1 + ret))
    return tuple(prices)


def _returns(prices: tuple[float, ...]) -> tuple[float, ...]:
    """Calculate returns from price series."""
    return tuple((prices[i] - prices[i - 1]) / prices[i - 1] for i in range(1, len(prices)))


def _make_request(
    name: str = "test_model",
    predictions: tuple[float, ...] | None = None,
    actuals: tuple[float, ...] | None = None,
) -> EvaluationRequest:
    """Helper to create evaluation requests."""
    if predictions is None:
        predictions = (100.7, 101.7, 102.7, 103.7, 104.7)
    if actuals is None:
        actuals = (100.0, 101.0, 102.0, 103.0, 104.0)
    return EvaluationRequest(model_name=name, predictions=predictions, actuals=actuals)


def _make_evaluation(
    name: str = "test_model",
    sharpe: float = 1.0,
    hit_rate: float = 0.6,
    rmse: float = 1.0,
) -> EvaluationResult:
    """Helper to create evaluation results with specific metrics."""
    return EvaluationResult(
        model_name=name,
        rmse=rmse,
        mae=rmse * 0.8,
        mape=rmse * 0.5,
        sharpe=sharpe,
        sortino=sharpe * 1.2,
        hit_ratio=hit_rate,
        precision=hit_rate,
        recall=hit_rate,
        f1=hit_rate,
        max_drawdown=0.1,
        cagr=sharpe * 0.05,
        sample_count=100,
    )


def _make_challenger(
    name: str = "challenger",
    evaluation: EvaluationResult | None = None,
) -> ChallengerModel:
    return ChallengerModel(
        name=name,
        evaluation=evaluation or _make_evaluation(name),
        challenges=10,
        best_score=1.5,
        consistency=0.8,
        improvement=0.2,
    )


# =========================================================================
# Configuration and Metadata Tests
# =========================================================================


class TestIntelligenceMetadata:
    def test_metadata_defaults(self) -> None:
        md = IntelligenceMetadata()
        assert md.name == ""
        assert md.version == "1.0"
        assert isinstance(md.created_at, datetime)

    def test_metadata_custom(self) -> None:
        ts = datetime(2024, 1, 1, tzinfo=UTC)
        md = IntelligenceMetadata(
            name="test",
            description="Test platform",
            version="2.0",
            created_at=ts,
        )
        assert md.name == "test"
        assert md.description == "Test platform"
        assert md.version == "2.0"
        assert md.created_at == ts


class TestIntelligenceConfig:
    def test_config_defaults(self) -> None:
        cfg = IntelligenceConfig()
        assert cfg.min_observations == 20
        assert cfg.rolling_window == 60
        assert cfg.decay_half_life == 30
        assert cfg.confidence_threshold == 0.60
        assert cfg.selection_criterion == SelectionCriterion.BEST_PERFORMANCE
        assert cfg.weighting_strategy == WeightingStrategy.ADAPTIVE_WEIGHTING

    def test_config_custom(self) -> None:
        cfg = IntelligenceConfig(
            min_observations=50,
            confidence_threshold=0.75,
            selection_criterion=SelectionCriterion.HIGHEST_SHARPE,
        )
        assert cfg.min_observations == 50
        assert cfg.confidence_threshold == 0.75
        assert cfg.selection_criterion == SelectionCriterion.HIGHEST_SHARPE


# =========================================================================
# Evaluation and Metrics Tests
# =========================================================================


class TestMetricsCalculator:
    def test_rmse_calculation(self) -> None:
        from backend.intelligence.evaluation import MetricsCalculator
        calc = MetricsCalculator()
        result = calc.evaluate(_make_request())
        assert result.rmse == pytest.approx(0.7, rel=1e-4)

    def test_mae_calculation(self) -> None:
        from backend.intelligence.evaluation import MetricsCalculator
        calc = MetricsCalculator()
        result = calc.evaluate(_make_request())
        assert result.mae == pytest.approx(0.7, rel=1e-4)

    def test_mape_calculation(self) -> None:
        from backend.intelligence.evaluation import MetricsCalculator
        calc = MetricsCalculator()
        result = calc.evaluate(_make_request())
        # MAPE for predictions=(100.7,101.7,102.7,103.7,104.7) against
        # actuals=(100.0,101.0,102.0,103.0,104.0) is mathematically
        # ~0.686%; assert the precise value rather than a rounded one.
        assert result.mape == pytest.approx(0.6864064780593978, rel=1e-4)

    def test_sharpe_calculation(self) -> None:
        from backend.intelligence.evaluation import MetricsCalculator
        calc = MetricsCalculator()
        prices = _prices(count=100, trend=0.01)
        returns = _returns(prices)
        result = calc.evaluate(
            EvaluationRequest(
                model_name="test",
                predictions=tuple(returns),
                actuals=tuple(returns),
            )
        )
        assert result.sharpe != 0.0

    def test_hit_ratio_calculation(self) -> None:
        from backend.intelligence.evaluation import MetricsCalculator
        calc = MetricsCalculator()
        result = calc.evaluate(_make_request())
        assert 0.0 <= result.hit_ratio <= 1.0

    def test_confidence_threshold(self) -> None:
        from backend.intelligence.evaluation import MetricsCalculator
        calc = MetricsCalculator()
        result = calc.evaluate(EvaluationRequest("test", (), ()))
        assert result.sample_count == 0


# =========================================================================
# Model Selection Tests
# =========================================================================


class TestChampionChallengerSelector:
    def test_default_initialization(self) -> None:
        selector = ChampionChallengerSelector()
        assert selector.champion is None
        assert selector.challengers == {}

    def test_register_champion(self) -> None:
        selector = ChampionChallengerSelector()
        champion = selector.register_champion(
            "champion", _make_evaluation("champion", sharpe=2.0)
        )
        assert champion.name == "champion"
        assert selector.champion is not None

    def test_register_challenger(self) -> None:
        selector = ChampionChallengerSelector()
        selector.register_challenger("challenger")
        assert "challenger" in selector.challengers
        assert len(selector.challengers) == 1

    def test_unregister_challenger(self) -> None:
        selector = ChampionChallengerSelector()
        selector.register_challenger("challenger")
        selector.unregister_challenger("challenger")
        assert "challenger" not in selector.challengers

    def test_delete_unknown_challenger(self) -> None:
        selector = ChampionChallengerSelector()
        with pytest.raises(ModelNotFoundError):
            selector.unregister_challenger("unknown")

    def test_evaluate(self) -> None:
        selector = ChampionChallengerSelector()
        request = _make_request("test")
        result = selector.evaluate(request)
        assert isinstance(result, EvaluationResult)
        assert result.model_name == "test"

    def test_select_best(self) -> None:
        selector = ChampionChallengerSelector()
        selector.register_challenger(
            "challenger", _make_evaluation("challenger", sharpe=2.0)
        )
        selector.register_champion("champion")
        name, result = selector.select_best()
        assert name in ("challenger", "champion")

    def test_check_replacement(self) -> None:
        selector = ChampionChallengerSelector()
        selector.register_champion(
            "champion", _make_evaluation("champion", sharpe=1.0)
        )
        selector.register_challenger(
            "challenger", _make_evaluation("challenger", sharpe=2.0)
        )
        should_replace, name = selector.check_replacement()
        assert should_replace is True
        assert name == "challenger"

    def test_no_replacement(self) -> None:
        selector = ChampionChallengerSelector()
        selector.register_champion(
            "champion", _make_evaluation("champion", sharpe=2.0)
        )
        should_replace, name = selector.check_replacement()
        assert should_replace is False
        assert name is None


# =========================================================================
# Ensemble Tests
# =========================================================================


class TestEnsembleEngine:
    def test_build_equal_weights(self) -> None:
        engine = EnsembleEngine()
        models = (
            EnsembleModel("model1", 1.0),
            EnsembleModel("model2", 1.0),
        )
        result = engine.build(models, WeightingStrategy.WEIGHTED_AVERAGE)
        assert result.model_count == 2
        assert abs(result.confidence - 0.5) < 0.5

    def test_build_weighted_average(self) -> None:
        engine = EnsembleEngine()
        models = (
            EnsembleModel("model1", 1.0, score=0.8, confidence=0.9),
            EnsembleModel("model2", 2.0, score=0.6, confidence=0.7),
        )
        result = engine.build(models, WeightingStrategy.WEIGHTED_AVERAGE)
        assert result.prediction == (0.8 * 1.0 + 0.6 * 2.0) / 3.0

    def test_build_confidence_weighting(self) -> None:
        engine = EnsembleEngine()
        models = (
            EnsembleModel("model1", 1.0, score=0.5, confidence=0.9),
            EnsembleModel("model2", 1.0, score=0.5, confidence=0.1),
        )
        engine.build(models, WeightingStrategy.CONFIDENCE_WEIGHTING)

    def test_regime_aware_weighting(self) -> None:
        engine = EnsembleEngine()
        models = (
            EnsembleModel("model1", 1.0, score=0.8, confidence=0.9),
            EnsembleModel("model2", 1.0, score=0.6, confidence=0.7),
        )
        result = engine.build(models, WeightingStrategy.REGIME_AWARE_WEIGHTING, regime="Bull")
        assert result.strategy == WeightingStrategy.REGIME_AWARE_WEIGHTING

    def test_ensemble_confidence(self) -> None:
        engine = EnsembleEngine()
        models = (
            EnsembleModel("model1", 1.0, score=0.8, confidence=0.9),
            EnsembleModel("model2", 1.0, score=0.7, confidence=0.8),
        )
        result = engine.build(models, WeightingStrategy.WEIGHTED_AVERAGE)
        assert 0.0 <= result.confidence <= 1.0


# =========================================================================
# Learning Tests
# =========================================================================


class TestLearningEngine:
    def test_update(self) -> None:
        engine = LearningEngine()
        result = _make_evaluation("test")
        history = engine.update("test", result, 1.5)
        assert history.model_name == "test"
        assert len(history.scores) == 1

    def test_rolling_statistics(self) -> None:
        engine = LearningEngine()
        result = _make_evaluation("test")
        engine.update("test", result, 1.5)
        stats = engine.rolling_statistics("test", window=10)
        assert "mean" in stats
        assert "std" in stats

    def test_detect_decay(self) -> None:
        engine = LearningEngine()
        result1 = _make_evaluation("test", sharpe=2.0)
        engine.update("test", result1, 2.0)
        result2 = _make_evaluation("test", sharpe=1.5)
        engine.update("test", result2, 1.5)
        assert engine.detect_decay("test", threshold=0.0)

    def test_adaptive_score(self) -> None:
        engine = LearningEngine()
        result = _make_evaluation("test", sharpe=1.5)
        engine.update("test", result, 1.5)
        score = engine.adaptive_score("test")
        assert 0.0 <= score <= 1.0


# =========================================================================
# Confidence Tests
# =========================================================================


class TestConfidenceEngine:
    def test_evaluate(self) -> None:
        engine = ConfidenceEngine()
        predictions = {"model1": 0.8, "model2": 0.7, "model3": 0.6}
        evaluations = {
            "model1": _make_evaluation("model1", sharpe=2.0),
            "model2": _make_evaluation("model2", sharpe=1.8),
            "model3": _make_evaluation("model3", sharpe=1.5),
        }
        score = engine.evaluate(0.7, predictions, evaluations, None)
        assert isinstance(score, ConfidenceScore)
        assert 0.0 <= score.confidence <= 1.0
        assert len(score.supporting_evidence) == 3

    def test_confidence_agreement(self) -> None:
        engine = ConfidenceEngine()
        predictions = {"model1": 0.8, "model2": 0.8}
        evaluations = {
            "model1": _make_evaluation("model1", sharpe=2.0),
            "model2": _make_evaluation("model2", sharpe=2.0),
        }
        score = engine.evaluate(0.8, predictions, evaluations, None)
        assert score.confidence > 0.5


# =========================================================================
# Intelligence Engine Tests
# =========================================================================


class TestIntelligenceEngine:
    def test_default_initialization(self) -> None:
        from backend.intelligence.engine import IntelligenceEngine
        engine = IntelligenceEngine()
        assert isinstance(engine.config, IntelligenceConfig)
        assert engine.selector.champion is None

    def test_evaluate(self) -> None:
        from backend.intelligence.engine import IntelligenceEngine
        engine = IntelligenceEngine()
        request = _make_request("test")
        result = engine.evaluate(request)
        assert isinstance(result, EvaluationResult)
        assert result.model_name == "test"

    def test_select_best(self) -> None:
        from backend.intelligence.engine import IntelligenceEngine
        engine = IntelligenceEngine()
        engine.selector.register_challenger("challenger")
        engine.selector.register_champion("champion")
        name, result = engine.select_best()
        assert name in ("challenger", "champion")

    def test_build_ensemble(self) -> None:
        from backend.intelligence.engine import IntelligenceEngine
        engine = IntelligenceEngine()
        models = (
            EnsembleModel("model1", 1.0, score=0.8),
            EnsembleModel("model2", 1.0, score=0.6),
        )
        result = engine.build_ensemble(models)
        assert isinstance(result, EnsembleResult)
        assert result.model_count == 2

    def test_adaptive_recommendation(self) -> None:
        from backend.intelligence.engine import IntelligenceEngine
        engine = IntelligenceEngine()
        recommendation = engine.adaptive_recommendation()
        assert isinstance(recommendation, AdaptiveRecommendation)


# =========================================================================
# Factory Tests
# =========================================================================


class TestIntelligenceFactory:
    def test_create_default(self) -> None:
        engine = IntelligenceFactory.create()
        assert isinstance(engine, IntelligenceEngine)
        assert isinstance(engine.config, IntelligenceConfig)

    def test_create_with_config(self) -> None:
        cfg = IntelligenceConfig(min_observations=50, confidence_threshold=0.75)
        engine = IntelligenceFactory.create(config=cfg)
        assert engine.config.min_observations == 50
        assert engine.config.confidence_threshold == 0.75

    def test_create_with_enums(self) -> None:
        cfg = IntelligenceConfig(
            selection_criterion=SelectionCriterion.HIGHEST_SHARPE,
            weighting_strategy=WeightingStrategy.REGIME_AWARE_WEIGHTING,
        )
        engine = IntelligenceFactory.create(config=cfg)
        assert engine.config.selection_criterion == SelectionCriterion.HIGHEST_SHARPE
        assert engine.config.weighting_strategy == WeightingStrategy.REGIME_AWARE_WEIGHTING


# =========================================================================
# Integration Tests
# =========================================================================


class TestIntegration:
    def test_full_workflow(self) -> None:
        engine = IntelligenceFactory.create()

        request1 = _make_request("model1")
        result1 = engine.evaluate(request1)
        assert isinstance(result1, EvaluationResult)

        request2 = _make_request("model2")
        result2 = engine.evaluate(request2)
        assert isinstance(result2, EvaluationResult)

        name, result = engine.select_best()
        assert name in ("model1", "model2")

        models = (
            EnsembleModel("model1", 1.0, score=result1.sharpe, confidence=0.9),
            EnsembleModel("model2", 1.0, score=result2.sharpe, confidence=0.8),
        )
        ensemble_result = engine.build_ensemble(models)
        assert isinstance(ensemble_result, EnsembleResult)
        assert ensemble_result.model_count == 2

        predictions = {m.name: m.score for m in models}
        evaluations = {result1.model_name: result1, result2.model_name: result2}
        confidence, evidence, reliability = engine.confidence(
            ensemble_result.prediction, predictions, evaluations
        )
        assert 0.0 <= confidence <= 1.0

        recommendation = engine.adaptive_recommendation()
        assert isinstance(recommendation, AdaptiveRecommendation)

    def test_error_handling(self) -> None:
        engine = IntelligenceFactory.create()

        empty_request = EvaluationRequest("test", (), ())
        with pytest.raises((InsufficientDataError, EvaluationError)):
            engine.evaluate(empty_request)

        with pytest.raises(ModelNotFoundError):
            engine.selector.unregister_challenger("unknown")

        with pytest.raises(EnsembleError):
            engine.build_ensemble(())


# =========================================================================
# Edge Cases and Error Handling
# =========================================================================


class TestEdgeCases:
    def test_insufficient_data(self) -> None:
        engine = IntelligenceFactory.create()
        empty_request = EvaluationRequest("test", (), ())
        with pytest.raises((InsufficientDataError, EvaluationError)):
            engine.evaluate(empty_request)

    def test_negative_scores(self) -> None:
        engine = ConfidenceEngine()
        predictions = {"model1": -0.5, "model2": -1.0}
        evaluations = {
            "model1": _make_evaluation("model1", sharpe=-1.0),
            "model2": _make_evaluation("model2", sharpe=-2.0),
        }
        score = engine.evaluate(-0.8, predictions, evaluations, None)
        assert score.confidence >= 0.0

    def test_zero_confidence(self) -> None:
        engine = ConfidenceEngine()
        predictions = {"model1": 0.5}
        evaluations = {"model1": _make_evaluation("model1", sharpe=0.0)}
        score = engine.evaluate(0.5, predictions, evaluations, None)
        assert score.confidence >= 0.0

    def test_many_models_ensemble(self) -> None:
        engine = EnsembleEngine()
        models = tuple(
            EnsembleModel(f"model{i}", 1.0, score=0.5 + i * 0.01, confidence=0.5 + i * 0.01)
            for i in range(10)
        )
        result = engine.build(models)
        assert result.model_count == 10


# =========================================================================
# Summary and Reporting
# =========================================================================


class TestReporting:
    def test_engine_summary(self) -> None:
        engine = IntelligenceFactory.create()
        request = _make_request("summary_test")
        result = engine.evaluate(request)
        assert hasattr(result, "sharpe")
        assert hasattr(result, "hit_ratio")
        assert hasattr(result, "rmse")


# =========================================================================
# NO LONGER NEEDS ADDITIONAL PLUGINS FOR UPSTOX/FX/CRYPTO
# Maturity in Sprint 40 volatility, real-market exposure ready.
# Sprint 41 focuses on adaptive intelligence, not provider expansion.
# =========================================================================


if __name__ == "__main__":
    pytest.main(["-v", __file__])
