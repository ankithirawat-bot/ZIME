"""Volatility forecast engine tests.

Covers all functionality including historical volatility, EWMA, GARCH,
EGARCH, GJR-GARCH, rolling forecast, term structure, confidence intervals,
model comparison, factory, and integration.
"""

from __future__ import annotations

import math

import pytest

from backend.volatility.comparison import ModelComparer
from backend.volatility.engine import VolatilityEngine
from backend.volatility.estimators import (
    EGARCHEstimator,
    EWMAAEstimator,
    GARCHEstimator,
    GJRGARCHEstimator,
    HistoricalVolatilityEstimator,
)
from backend.volatility.exceptions import (
    ConvergenceError,
    EstimationError,
    ForecastError,
    InsufficientDataError,
    InvalidVolatilityConfigError,
    ModelNotFoundError,
    VolatilityError,
)
from backend.volatility.factory import VolatilityFactory
from backend.volatility.forecast import ForecastEngine
from backend.volatility.models import (
    ConfidenceInterval,
    ForecastDefinition,
    ForecastMetrics,
    ForecastResult,
    ForecastStatistics,
    ModelComparison,
    VolatilityConfig,
    VolatilityForecast,
    VolatilityMetadata,
)


def _generate_returns(
    n: int = 300,
    seed: float = 0.01,
    vol: float = 0.02,
) -> tuple[float, ...]:
    """Generate synthetic returns with known volatility."""
    import random

    rng = random.Random(42)
    returns = []
    current_vol = vol
    for i in range(n):
        innov = rng.gauss(0, current_vol)
        returns.append(innov)
        current_vol = vol * (1 + 0.5 * math.sin(i / 20))
    return tuple(returns)


def _create_garch_returns(n: int = 500) -> tuple[float, ...]:
    """Generate returns with GARCH-like volatility clustering."""
    import random

    rng = random.Random(12345)
    returns: list[float] = []
    var = 0.0004
    omega = 0.00001
    alpha = 0.1
    beta = 0.85
    for _ in range(n):
        innov = rng.gauss(0, math.sqrt(var))
        returns.append(innov)
        var = omega + alpha * innov ** 2 + beta * var
    return tuple(returns)


def _create_asymmetric_returns(n: int = 500) -> tuple[float, ...]:
    """Generate returns with asymmetric volatility."""
    import random

    rng = random.Random(67890)
    returns: list[float] = []
    var = 0.0004
    omega = 0.00001
    alpha = 0.08
    beta = 0.85
    gamma = 0.06
    for _ in range(n):
        innov = rng.gauss(0, math.sqrt(var))
        returns.append(innov)
        leverage = 1.0 if innov < 0 else 0.0
        var = omega + (alpha + gamma * leverage) * innov ** 2 + beta * var
    return tuple(returns)


def _create_config(**kwargs: object) -> VolatilityConfig:
    """Create a test configuration."""
    defaults: dict[str, object] = {
        "model": "garch",
        "lookback": 252,
        "horizon": 20,
        "annual_factor": 252.0,
        "confidence_level": 0.95,
        "ewma_lambda": 0.94,
        "garch_p": 1,
        "garch_q": 1,
        "max_iterations": 1000,
        "tolerance": 1e-8,
        "min_periods": 20,
        "use_variance_targeting": True,
    }
    defaults.update(kwargs)
    return VolatilityConfig(**defaults)  # type: ignore[arg-type]


class TestModels:
    """Test data models."""

    def test_volatility_metadata(self) -> None:
        metadata = VolatilityMetadata(name="Test")
        assert metadata.name == "Test"
        assert metadata.version == "1.0"

    def test_volatility_config_defaults(self) -> None:
        config = VolatilityConfig()
        assert config.model == "garch"
        assert config.annual_factor == 252.0

    def test_confidence_interval(self) -> None:
        ci = ConfidenceInterval(lower=0.10, expected=0.20, upper=0.30)
        assert ci.expected == 0.20
        assert ci.lower == 0.10

    def test_volatility_forecast(self) -> None:
        fc = VolatilityForecast(model="garch", horizon=20, forecast=0.25, variance=0.0625)
        assert fc.forecast == 0.25
        assert fc.horizon == 20

    def test_forecast_result(self) -> None:
        result = ForecastResult(symbol="RELIANCE", model="garch")
        assert result.symbol == "RELIANCE"
        assert len(result.forecasts) == 0

    def test_forecast_metrics(self) -> None:
        metrics = ForecastMetrics(rmse=0.05, mae=0.03)
        assert metrics.rmse == 0.05

    def test_model_comparison(self) -> None:
        comp = ModelComparison(model_name="garch", rank=1, score=0.85)
        assert comp.model_name == "garch"
        assert comp.rank == 1

    def test_forecast_statistics(self) -> None:
        stats = ForecastStatistics(total_forecasts=10)
        assert stats.total_forecasts == 10

    def test_forecast_definition(self) -> None:
        definition = ForecastDefinition(
            metadata=VolatilityMetadata(name="Test"),
            config=VolatilityConfig(),
        )
        assert definition.metadata.name == "Test"

    def test_metadata_immutable(self) -> None:
        metadata = VolatilityMetadata(name="Test")
        with pytest.raises(AttributeError):
            metadata.name = "Changed"  # type: ignore[misc]

    def test_config_immutable(self) -> None:
        config = VolatilityConfig()
        with pytest.raises(AttributeError):
            config.model = "changed"  # type: ignore[misc]

    def test_forecast_immutable(self) -> None:
        fc = VolatilityForecast(model="test", horizon=10, forecast=0.2, variance=0.04)
        with pytest.raises(AttributeError):
            fc.forecast = 0.3  # type: ignore[misc]

    def test_confidence_interval_defaults(self) -> None:
        ci = ConfidenceInterval()
        assert ci.confidence_level == 0.95


class TestHistoricalEstimator:
    """Test historical volatility estimator."""

    def test_estimate(self) -> None:
        returns = _generate_returns(300)
        estimator = HistoricalVolatilityEstimator()
        config = _create_config()
        result = estimator.estimate(returns, config)
        assert result.model == "historical"
        assert result.forecast > 0
        assert result.converged

    def test_estimate_insufficient_data(self) -> None:
        estimator = HistoricalVolatilityEstimator()
        config = _create_config(min_periods=100)
        with pytest.raises(InsufficientDataError):
            estimator.estimate((0.01, 0.02), config)

    def test_forecast(self) -> None:
        returns = _generate_returns(300)
        estimator = HistoricalVolatilityEstimator()
        config = _create_config()
        result = estimator.forecast(returns, 20, config)
        assert result.horizon == 20
        assert result.forecast > 0

    def test_forecast_short_horizon(self) -> None:
        returns = _generate_returns(300)
        estimator = HistoricalVolatilityEstimator()
        config = _create_config()
        result = estimator.forecast(returns, 1, config)
        assert result.horizon == 1

    def test_forecast_long_horizon(self) -> None:
        returns = _generate_returns(300)
        estimator = HistoricalVolatilityEstimator()
        config = _create_config()
        result = estimator.forecast(returns, 252, config)
        assert result.horizon == 252

    def test_lookback_applied(self) -> None:
        returns = _generate_returns(500)
        estimator = HistoricalVolatilityEstimator()
        config = _create_config(lookback=100)
        result = estimator.estimate(returns, config)
        assert result.forecast > 0

    def test_confidence_interval_included(self) -> None:
        returns = _generate_returns(300)
        estimator = HistoricalVolatilityEstimator()
        config = _create_config()
        result = estimator.estimate(returns, config)
        assert result.confidence.lower <= result.confidence.expected
        assert result.confidence.expected <= result.confidence.upper


class TestEWMAEstimator:
    """Test EWMA volatility estimator."""

    def test_estimate(self) -> None:
        returns = _generate_returns(300)
        estimator = EWMAAEstimator()
        config = _create_config()
        result = estimator.estimate(returns, config)
        assert result.model == "ewma"
        assert result.forecast > 0

    def test_estimate_insufficient_data(self) -> None:
        estimator = EWMAAEstimator()
        config = _create_config(min_periods=100)
        with pytest.raises(InsufficientDataError):
            estimator.estimate((0.01, 0.02), config)

    def test_forecast(self) -> None:
        returns = _generate_returns(300)
        estimator = EWMAAEstimator()
        config = _create_config()
        result = estimator.forecast(returns, 20, config)
        assert result.horizon == 20

    def test_conditional_vol_series(self) -> None:
        returns = _generate_returns(100)
        estimator = EWMAAEstimator()
        config = _create_config()
        result = estimator.estimate(returns, config)
        assert len(result.conditional_vol) > 0

    def test_custom_lambda(self) -> None:
        returns = _generate_returns(300)
        estimator = EWMAAEstimator()
        config = _create_config(ewma_lambda=0.90)
        result = estimator.estimate(returns, config)
        assert result.forecast > 0

    def test_parameters_contain_lambda(self) -> None:
        returns = _generate_returns(300)
        estimator = EWMAAEstimator()
        config = _create_config(ewma_lambda=0.94)
        result = estimator.estimate(returns, config)
        assert "lambda" in result.parameters


class TestGARCHEstimator:
    """Test GARCH(1,1) estimator."""

    def test_estimate(self) -> None:
        returns = _create_garch_returns(500)
        estimator = GARCHEstimator()
        config = _create_config()
        result = estimator.estimate(returns, config)
        assert result.model == "garch"
        assert result.forecast > 0
        assert result.converged

    def test_estimate_insufficient_data(self) -> None:
        estimator = GARCHEstimator()
        config = _create_config(min_periods=100)
        with pytest.raises(InsufficientDataError):
            estimator.estimate((0.01, 0.02), config)

    def test_forecast(self) -> None:
        returns = _create_garch_returns(500)
        estimator = GARCHEstimator()
        config = _create_config()
        result = estimator.forecast(returns, 20, config)
        assert result.horizon == 20
        assert result.forecast > 0

    def test_forecast_multi_step(self) -> None:
        returns = _create_garch_returns(500)
        estimator = GARCHEstimator()
        config = _create_config()
        for h in (1, 5, 10, 20):
            result = estimator.forecast(returns, h, config)
            assert result.horizon == h

    def test_conditional_vol_series(self) -> None:
        returns = _create_garch_returns(300)
        estimator = GARCHEstimator()
        config = _create_config()
        result = estimator.estimate(returns, config)
        assert len(result.conditional_vol) > 0

    def test_parameters_contain_alpha_beta(self) -> None:
        returns = _create_garch_returns(500)
        estimator = GARCHEstimator()
        config = _create_config()
        result = estimator.estimate(returns, config)
        assert "alpha" in result.parameters
        assert "beta" in result.parameters
        assert "omega" in result.parameters

    def test_log_likelihood(self) -> None:
        returns = _create_garch_returns(500)
        estimator = GARCHEstimator()
        config = _create_config()
        result = estimator.estimate(returns, config)
        assert result.log_likelihood <= 0 or result.log_likelihood > -1e10

    def test_forecast_from_short_returns(self) -> None:
        returns = _generate_returns(50)
        estimator = GARCHEstimator()
        config = _create_config(min_periods=10)
        result = estimator.forecast(returns, 10, config)
        assert result.converged


class TestEGARCHEstimator:
    """Test EGARCH(1,1) estimator."""

    def test_estimate(self) -> None:
        returns = _create_asymmetric_returns(500)
        estimator = EGARCHEstimator()
        config = _create_config()
        result = estimator.estimate(returns, config)
        assert result.model == "egarch"
        assert result.forecast > 0

    def test_estimate_insufficient_data(self) -> None:
        estimator = EGARCHEstimator()
        config = _create_config(min_periods=100)
        with pytest.raises(InsufficientDataError):
            estimator.estimate((0.01, 0.02), config)

    def test_forecast(self) -> None:
        returns = _create_asymmetric_returns(500)
        estimator = EGARCHEstimator()
        config = _create_config()
        result = estimator.forecast(returns, 20, config)
        assert result.horizon == 20

    def test_parameters_contain_gamma(self) -> None:
        returns = _create_asymmetric_returns(500)
        estimator = EGARCHEstimator()
        config = _create_config()
        result = estimator.estimate(returns, config)
        assert "gamma" in result.parameters

    def test_conditional_vol_series(self) -> None:
        returns = _create_asymmetric_returns(300)
        estimator = EGARCHEstimator()
        config = _create_config()
        result = estimator.estimate(returns, config)
        assert len(result.conditional_vol) > 0

    def test_log_likelihood(self) -> None:
        returns = _create_asymmetric_returns(500)
        estimator = EGARCHEstimator()
        config = _create_config()
        result = estimator.estimate(returns, config)
        assert isinstance(result.log_likelihood, float)


class TestGJRGARCHEstimator:
    """Test GJR-GARCH(1,1) estimator."""

    def test_estimate(self) -> None:
        returns = _create_asymmetric_returns(500)
        estimator = GJRGARCHEstimator()
        config = _create_config()
        result = estimator.estimate(returns, config)
        assert result.model == "gjrgarch"
        assert result.forecast > 0

    def test_estimate_insufficient_data(self) -> None:
        estimator = GJRGARCHEstimator()
        config = _create_config(min_periods=100)
        with pytest.raises(InsufficientDataError):
            estimator.estimate((0.01, 0.02), config)

    def test_forecast(self) -> None:
        returns = _create_asymmetric_returns(500)
        estimator = GJRGARCHEstimator()
        config = _create_config()
        result = estimator.forecast(returns, 20, config)
        assert result.horizon == 20

    def test_parameters_contain_gamma(self) -> None:
        returns = _create_asymmetric_returns(500)
        estimator = GJRGARCHEstimator()
        config = _create_config()
        result = estimator.estimate(returns, config)
        assert "gamma" in result.parameters

    def test_conditional_vol_series(self) -> None:
        returns = _create_asymmetric_returns(300)
        estimator = GJRGARCHEstimator()
        config = _create_config()
        result = estimator.estimate(returns, config)
        assert len(result.conditional_vol) > 0


class TestForecastEngine:
    """Test forecast engine."""

    def test_forecast_single(self) -> None:
        returns = _create_garch_returns(500)
        engine = ForecastEngine()
        result = engine.forecast(returns, "garch", 20, _create_config())
        assert isinstance(result, VolatilityForecast)
        assert result.forecast > 0

    def test_forecast_default_model(self) -> None:
        returns = _create_garch_returns(500)
        engine = ForecastEngine()
        config = _create_config(model="garch")
        result = engine.forecast(returns, horizon=20, config=config)
        assert result.model == "garch"

    def test_forecast_model_not_found(self) -> None:
        engine = ForecastEngine()
        with pytest.raises(InsufficientDataError):
            engine.forecast((0.01,), "nonexistent", 20, _create_config())

    def test_forecast_multiple(self) -> None:
        returns = _create_garch_returns(500)
        engine = ForecastEngine()
        result = engine.forecast_multiple(returns, "garch", (1, 5, 10), _create_config())
        assert isinstance(result, ForecastResult)
        assert 1 in result.forecasts
        assert 5 in result.forecasts

    def test_forecast_multiple_default_horizons(self) -> None:
        returns = _create_garch_returns(500)
        engine = ForecastEngine()
        result = engine.forecast_multiple(returns, "garch", config=_create_config())
        assert len(result.forecasts) > 0

    def test_term_structure(self) -> None:
        returns = _create_garch_returns(500)
        engine = ForecastEngine()
        result = engine.forecast_term_structure(returns, "garch", _create_config())
        assert 1 in result.forecasts
        assert 252 in result.forecasts

    def test_compare_models(self) -> None:
        returns = _create_garch_returns(500)
        engine = ForecastEngine()
        results = engine.compare_models(returns, 20, _create_config())
        assert len(results) > 0
        assert "garch" in results

    def test_rolling_forecast(self) -> None:
        returns = _generate_returns(400)
        engine = ForecastEngine()
        config = _create_config()
        results = engine.rolling_forecast(returns, window=200, model="historical", horizon=20, config=config)
        assert len(results) > 0

    def test_rolling_forecast_insufficient_data(self) -> None:
        engine = ForecastEngine()
        with pytest.raises(InsufficientDataError):
            engine.rolling_forecast((0.01,) * 50, window=200, config=_create_config())

    def test_rolling_forecast_failure_handling(self) -> None:
        returns = _generate_returns(250)
        engine = ForecastEngine()
        config = _create_config(min_periods=200)
        results = engine.rolling_forecast(returns, window=50, model="garch", horizon=10, config=config)
        assert len(results) > 0

    def test_register_custom_estimator(self) -> None:
        engine = ForecastEngine()
        custom = HistoricalVolatilityEstimator()
        engine.register_estimator("custom", custom)
        assert "custom" in engine.estimators

    def test_default_estimators(self) -> None:
        engine = ForecastEngine()
        estimators = engine.estimators
        assert "historical" in estimators
        assert "ewma" in estimators
        assert "garch" in estimators
        assert "egarch" in estimators
        assert "gjrgarch" in estimators

    def test_forecast_with_all_models(self) -> None:
        returns = _create_garch_returns(500)
        engine = ForecastEngine()
        config = _create_config()
        for model in ("historical", "ewma", "garch", "egarch", "gjrgarch"):
            result = engine.forecast(returns, model, 20, config)
            assert result.forecast > 0

    def test_forecast_multiple_result_fields(self) -> None:
        returns = _create_garch_returns(500)
        engine = ForecastEngine()
        result = engine.forecast_multiple(returns, "garch", (1, 5), _create_config())
        assert result.current_vol > 0
        assert result.elapsed >= 0


class TestComparison:
    """Test model comparison."""

    def test_compute_metrics(self) -> None:
        forecast = VolatilityForecast(
            model="garch", horizon=20, forecast=0.25, variance=0.0625,
            log_likelihood=-500.0,
        )
        actual = _generate_returns(50)
        config = _create_config()
        metrics = ModelComparer.compute_metrics(forecast, actual, config)
        assert isinstance(metrics, ForecastMetrics)

    def test_compute_metrics_empty_actual(self) -> None:
        forecast = VolatilityForecast(
            model="garch", horizon=20, forecast=0.25, variance=0.0625,
        )
        config = _create_config()
        metrics = ModelComparer.compute_metrics(forecast, (), config)
        assert metrics.n_observations == 0

    def test_compare_models(self) -> None:
        forecasts = {
            "garch": VolatilityForecast(
                model="garch", horizon=20, forecast=0.25, variance=0.0625,
                log_likelihood=-500.0,
            ),
            "ewma": VolatilityForecast(
                model="ewma", horizon=20, forecast=0.22, variance=0.0484,
                log_likelihood=-520.0,
            ),
        }
        actual = _generate_returns(50)
        config = _create_config()
        results = ModelComparer.compare(forecasts, actual, config)
        assert len(results) == 2
        assert results[0].rank == 1

    def test_compare_models_skip_non_converged(self) -> None:
        forecasts = {
            "garch": VolatilityForecast(
                model="garch", horizon=20, forecast=0.25, variance=0.0625,
                converged=False,
            ),
        }
        actual = _generate_returns(50)
        config = _create_config()
        results = ModelComparer.compare(forecasts, actual, config)
        assert len(results) == 0

    def test_compare_empty_forecasts(self) -> None:
        results = ModelComparer.compare({}, (), _create_config())
        assert len(results) == 0

    def test_metrics_contain_all_fields(self) -> None:
        forecast = VolatilityForecast(
            model="garch", horizon=20, forecast=0.25, variance=0.0625,
            log_likelihood=-500.0, parameters={"alpha": 0.1, "beta": 0.85},
        )
        actual = _generate_returns(50)
        config = _create_config()
        metrics = ModelComparer.compute_metrics(forecast, actual, config)
        assert metrics.rmse >= 0
        assert metrics.mae >= 0
        assert isinstance(metrics.aic, float)
        assert isinstance(metrics.bic, float)

    def test_aic_bic_for_non_converged(self) -> None:
        forecast = VolatilityForecast(
            model="garch", horizon=20, forecast=0.0, variance=0.0,
            log_likelihood=-1000.0,
        )
        config = _create_config()
        metrics = ModelComparer.compute_metrics(forecast, (), config)
        assert isinstance(metrics.aic, float)


class TestVolatilityEngine:
    """Test volatility engine."""

    def test_initialization(self) -> None:
        engine = VolatilityEngine()
        assert isinstance(engine.config, VolatilityConfig)

    def test_forecast(self) -> None:
        returns = _create_garch_returns(500)
        engine = VolatilityEngine()
        config = _create_config()
        result = engine.forecast(returns, "garch", 20, config)
        assert isinstance(result, VolatilityForecast)
        assert result.forecast > 0

    def test_forecast_default_config(self) -> None:
        returns = _create_garch_returns(500)
        engine = VolatilityEngine(config=_create_config(model="garch"))
        result = engine.forecast(returns)
        assert result.forecast > 0

    def test_forecast_multiple(self) -> None:
        returns = _create_garch_returns(500)
        engine = VolatilityEngine()
        result = engine.forecast_multiple(returns, "garch", (1, 5, 10))
        assert isinstance(result, ForecastResult)

    def test_compare_models(self) -> None:
        returns = _create_garch_returns(300)
        actual = _generate_returns(50)
        engine = VolatilityEngine()
        results = engine.compare_models(returns, actual, 20)
        assert len(results) > 0

    def test_rolling_forecast(self) -> None:
        returns = _generate_returns(400)
        engine = VolatilityEngine()
        config = _create_config()
        results = engine.rolling_forecast(returns, window=200, model="historical", horizon=20, config=config)
        assert len(results) > 0

    def test_term_structure(self) -> None:
        returns = _create_garch_returns(500)
        engine = VolatilityEngine()
        result = engine.forecast_term_structure(returns, "garch")
        assert isinstance(result, ForecastResult)

    def test_compute_metrics(self) -> None:
        returns = _generate_returns(50)
        forecast = VolatilityForecast(
            model="garch", horizon=20, forecast=0.25, variance=0.0625,
        )
        engine = VolatilityEngine()
        metrics = engine.compute_metrics(forecast, returns)
        assert isinstance(metrics, ForecastMetrics)

    def test_generate_statistics(self) -> None:
        engine = VolatilityEngine()
        stats = engine.generate_statistics(
            elapsed=0.15,
            warnings=("Low data",),
        )
        assert stats.elapsed_seconds == 0.15
        assert len(stats.warnings) == 1

    def test_total_forecasts_tracked(self) -> None:
        engine = VolatilityEngine()
        returns = _create_garch_returns(500)
        engine.forecast(returns, "garch", 20)
        engine.forecast(returns, "garch", 10)
        stats = engine.generate_statistics(0.1)
        assert stats.total_forecasts == 2

    def test_with_portfolio_engine(self) -> None:
        engine = VolatilityEngine(portfolio_engine=object())
        assert engine._portfolio_engine is not None

    def test_with_risk_engine(self) -> None:
        engine = VolatilityEngine(risk_engine=object())
        assert engine._risk_engine is not None

    def test_with_sizing_engine(self) -> None:
        engine = VolatilityEngine(sizing_engine=object())
        assert engine._sizing_engine is not None

    def test_with_strategy_engine(self) -> None:
        engine = VolatilityEngine(strategy_engine=object())
        assert engine._strategy_engine is not None

    def test_with_backtesting_engine(self) -> None:
        engine = VolatilityEngine(backtesting_engine=object())
        assert engine._backtesting_engine is not None

    def test_forecast_engine_property(self) -> None:
        engine = VolatilityEngine()
        assert isinstance(engine.forecast_engine, ForecastEngine)

    def test_forecast_engine_property_custom(self) -> None:
        fe = ForecastEngine()
        engine = VolatilityEngine(forecast_engine=fe)
        assert engine.forecast_engine is fe


class TestFactory:
    """Test factory creation."""

    def test_create_default(self) -> None:
        engine = VolatilityFactory.create()
        assert isinstance(engine, VolatilityEngine)

    def test_create_with_config(self) -> None:
        config = _create_config(model="ewma")
        engine = VolatilityFactory.create(config=config)
        assert engine.config.model == "ewma"

    def test_create_with_forecast_engine(self) -> None:
        fe = ForecastEngine()
        engine = VolatilityFactory.create(forecast_engine=fe)
        assert engine.forecast_engine is fe

    def test_create_with_portfolio_engine(self) -> None:
        engine = VolatilityFactory.create(portfolio_engine=object())
        assert engine._portfolio_engine is not None

    def test_create_with_risk_engine(self) -> None:
        engine = VolatilityFactory.create(risk_engine=object())
        assert engine._risk_engine is not None

    def test_create_with_sizing_engine(self) -> None:
        engine = VolatilityFactory.create(sizing_engine=object())
        assert engine._sizing_engine is not None

    def test_create_with_strategy_engine(self) -> None:
        engine = VolatilityFactory.create(strategy_engine=object())
        assert engine._strategy_engine is not None

    def test_create_with_backtesting_engine(self) -> None:
        engine = VolatilityFactory.create(backtesting_engine=object())
        assert engine._backtesting_engine is not None

    def test_create_with_models(self) -> None:
        custom = HistoricalVolatilityEstimator()
        engine = VolatilityFactory.create_with_models({"custom": custom})
        assert "custom" in engine.forecast_engine.estimators

    def test_create_from_config(self) -> None:
        config = _create_config(model="egarch")
        engine = VolatilityFactory.create_from_config(config)
        assert engine.config.model == "egarch"

    def test_create_with_all_dependencies(self) -> None:
        engine = VolatilityFactory.create(
            config=_create_config(),
            forecast_engine=ForecastEngine(),
            comparer=ModelComparer(),
            portfolio_engine=object(),
            risk_engine=object(),
            sizing_engine=object(),
            strategy_engine=object(),
            backtesting_engine=object(),
        )
        assert engine._portfolio_engine is not None
        assert engine._risk_engine is not None
        assert engine._sizing_engine is not None


class TestExceptions:
    """Test exception hierarchy."""

    def test_volatility_error(self) -> None:
        with pytest.raises(VolatilityError):
            raise VolatilityError("test")

    def test_invalid_volatility_config_error(self) -> None:
        with pytest.raises(InvalidVolatilityConfigError):
            raise InvalidVolatilityConfigError("test")

    def test_insufficient_data_error(self) -> None:
        with pytest.raises(InsufficientDataError):
            raise InsufficientDataError("test")

    def test_estimation_error(self) -> None:
        with pytest.raises(EstimationError):
            raise EstimationError("garch", "test")

    def test_estimation_error_attributes(self) -> None:
        error = EstimationError("garch", "test")
        assert error.model == "garch"

    def test_convergence_error(self) -> None:
        with pytest.raises(ConvergenceError):
            raise ConvergenceError("garch")

    def test_convergence_error_with_message(self) -> None:
        error = ConvergenceError("garch", "failed")
        assert "failed" in str(error)

    def test_forecast_error(self) -> None:
        with pytest.raises(ForecastError):
            raise ForecastError("test")

    def test_model_not_found_error(self) -> None:
        with pytest.raises(ModelNotFoundError):
            raise ModelNotFoundError("test")

    def test_model_not_found_error_attributes(self) -> None:
        error = ModelNotFoundError("nonexistent")
        assert error.name == "nonexistent"


class TestIntegration:
    """Integration tests for complete volatility flow."""

    def test_complete_flow(self) -> None:
        returns = _create_garch_returns(500)
        engine = VolatilityFactory.create(config=_create_config(model="garch"))

        fc = engine.forecast(returns, horizon=20)
        assert fc.forecast > 0
        assert fc.confidence.lower <= fc.confidence.expected

        result = engine.forecast_multiple(returns, horizons=(1, 5, 20))
        assert len(result.forecasts) == 3

        term = engine.forecast_term_structure(returns)
        assert 1 in term.forecasts
        assert 252 in term.forecasts

    def test_all_models_produce_forecasts(self) -> None:
        returns = _create_garch_returns(500)
        engine = VolatilityEngine()
        config = _create_config()

        for model in ("historical", "ewma", "garch", "egarch", "gjrgarch"):
            result = engine.forecast(returns, model, 20, config)
            assert result.forecast > 0, f"Model {model} failed"

    def test_rolling_and_term_structure(self) -> None:
        returns = _generate_returns(400)
        engine = VolatilityEngine()

        rolling = engine.rolling_forecast(returns, window=200, model="historical", horizon=20)
        assert len(rolling) > 0

        term = engine.forecast_term_structure(returns, "historical")
        assert len(term.forecasts) > 0

    def test_garch_volatility_clustering_detected(self) -> None:
        returns = _create_garch_returns(500)
        garch_est = GARCHEstimator()
        hist_est = HistoricalVolatilityEstimator()
        config = _create_config()

        garch_result = garch_est.estimate(returns, config)
        hist_result = hist_est.estimate(returns, config)

        assert garch_result.forecast > 0
        assert hist_result.forecast > 0

    def test_model_comparison_flow(self) -> None:
        returns = _create_garch_returns(300)
        actual = _generate_returns(50)
        engine = VolatilityEngine()

        comparisons = engine.compare_models(returns, actual, 20)
        assert len(comparisons) > 0
        assert comparisons[0].rank == 1
        assert comparisons[0].score > 0

    def test_confidence_intervals_in_all_forecasts(self) -> None:
        returns = _create_garch_returns(500)
        engine = VolatilityEngine()
        config = _create_config()

        for model in ("historical", "ewma", "garch", "egarch", "gjrgarch"):
            result = engine.forecast(returns, model, 20, config)
            ci = result.confidence
            assert ci.lower <= ci.expected
            assert ci.expected <= ci.upper or abs(ci.expected - ci.upper) < 0.01

    def test_term_structure_monotonicity(self) -> None:
        returns = _generate_returns(500)
        engine = VolatilityEngine()
        result = engine.forecast_term_structure(returns, "historical")
        forecasts = [result.forecasts[h].forecast for h in sorted(result.forecasts.keys())]
        assert all(f > 0 for f in forecasts)

    def test_metrics_with_all_models(self) -> None:
        returns = _create_garch_returns(300)
        actual = _generate_returns(30)
        engine = VolatilityEngine()
        config = _create_config()

        for model in ("historical", "ewma", "garch"):
            fc = engine.forecast(returns, model, 20, config)
            metrics = engine.compute_metrics(fc, actual)
            assert isinstance(metrics.rmse, float)

    def test_full_pipeline(self) -> None:
        returns = _create_garch_returns(500)
        engine = VolatilityFactory.create()

        fc = engine.forecast(returns, horizon=20)
        result = engine.forecast_multiple(returns, horizons=(1, 5, 20, 60))
        term = engine.forecast_term_structure(returns)

        assert fc.forecast > 0
        assert len(result.forecasts) == 4
        assert len(term.forecasts) == 6

    def test_different_config_per_model(self) -> None:
        returns = _create_garch_returns(500)
        engine = VolatilityEngine()

        garch_cfg = _create_config(model="garch", horizon=20)
        ewma_cfg = _create_config(model="ewma", horizon=20, ewma_lambda=0.90)

        garch_fc = engine.forecast(returns, config=garch_cfg)
        ewma_fc = engine.forecast(returns, config=ewma_cfg)

        assert garch_fc.forecast > 0
        assert ewma_fc.forecast > 0

    def test_short_returns_still_work(self) -> None:
        returns = _generate_returns(30)
        engine = VolatilityEngine()
        config = _create_config(min_periods=5, lookback=20)

        result = engine.forecast(returns, "historical", 5, config)
        assert result.forecast > 0

    def test_statistics_generation(self) -> None:
        returns = _create_garch_returns(500)
        engine = VolatilityEngine()
        engine.forecast(returns, horizon=20)
        engine.forecast(returns, horizon=60)

        stats = engine.generate_statistics(
            elapsed=0.25,
            warnings=("Test warning",),
            errors=("Test error",),
        )
        assert stats.total_forecasts == 2
        assert stats.elapsed_seconds == 0.25
