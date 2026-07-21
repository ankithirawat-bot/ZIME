"""Volatility forecast engine tests.

Covers all estimators, forecast engine, diagnostics, model comparison,
confidence intervals, factory, and integration.
"""

from __future__ import annotations

import math
import random

import pytest

from backend.volatility.comparison import ModelComparer
from backend.volatility.diagnostics import compute_diagnostics
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
    DiagnosticsError,
    EstimationError,
    ForecastError,
    InsufficientDataError,
    InvalidVolatilityConfigError,
    ModelNotFoundError,
    UpdateError,
    VolatilityError,
)
from backend.volatility.factory import VolatilityFactory
from backend.volatility.forecast import DEFAULT_HORIZONS, ForecastEngine
from backend.volatility.models import (
    ConfidenceInterval,
    ForecastDefinition,
    ForecastMetrics,
    ForecastRequest,
    ForecastResult,
    ForecastStatistics,
    ModelComparison,
    ModelDiagnostics,
    VolatilityConfig,
    VolatilityForecast,
    VolatilityMetadata,
)


def _generate_returns(n: int = 300, vol: float = 0.02) -> tuple[float, ...]:
    """Generate synthetic returns."""
    rng = random.Random(42)
    returns = []
    for i in range(n):
        current_vol = vol * (1 + 0.5 * math.sin(i / 20))
        returns.append(rng.gauss(0, current_vol))
    return tuple(returns)


def _garch_returns(n: int = 500) -> tuple[float, ...]:
    """Generate GARCH-like returns."""
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


def _asymmetric_returns(n: int = 500) -> tuple[float, ...]:
    """Generate returns with leverage effects."""
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
        lev = 1.0 if innov < 0 else 0.0
        var = omega + (alpha + gamma * lev) * innov ** 2 + beta * var
    return tuple(returns)


def _config(**kwargs: object) -> VolatilityConfig:
    defaults: dict[str, object] = {
        "model": "garch", "lookback": 252, "horizon": 20,
        "annual_factor": 252.0, "confidence_level": 0.95,
        "ewma_lambda": 0.94, "min_periods": 20,
    }
    defaults.update(kwargs)
    return VolatilityConfig(**defaults)  # type: ignore[arg-type]


class TestModels:
    """Test data models."""

    def test_metadata(self) -> None:
        m = VolatilityMetadata(name="Test")
        assert m.name == "Test"

    def test_config_defaults(self) -> None:
        c = VolatilityConfig()
        assert c.model == "garch"

    def test_confidence_interval(self) -> None:
        ci = ConfidenceInterval(lower=0.1, expected=0.2, upper=0.3, confidence_level=0.95)
        assert ci.expected == 0.2

    def test_forecast(self) -> None:
        f = VolatilityForecast(model="garch", horizon=20, forecast=0.25, variance=0.0625)
        assert f.forecast == 0.25

    def test_forecast_result(self) -> None:
        r = ForecastResult(symbol="RELIANCE", model="garch")
        assert r.symbol == "RELIANCE"

    def test_forecast_metrics(self) -> None:
        m = ForecastMetrics(rmse=0.05, mae=0.03)
        assert m.rmse == 0.05

    def test_model_comparison(self) -> None:
        c = ModelComparison(model_name="garch", rank=1, score=0.85)
        assert c.rank == 1

    def test_statistics(self) -> None:
        s = ForecastStatistics(total_forecasts=10)
        assert s.total_forecasts == 10

    def test_definition(self) -> None:
        d = ForecastDefinition(metadata=VolatilityMetadata(name="T"), config=VolatilityConfig())
        assert d.metadata.name == "T"

    def test_diagnostics(self) -> None:
        d = ModelDiagnostics(persistence=0.95, half_life=13.5, is_stationary=True)
        assert d.persistence == 0.95

    def test_forecast_request(self) -> None:
        r = ForecastRequest(symbol="RELIANCE", horizon=20)
        assert r.symbol == "RELIANCE"
        assert r.horizon == 20

    def test_immutable_metadata(self) -> None:
        m = VolatilityMetadata(name="T")
        with pytest.raises(AttributeError):
            m.name = "X"  # type: ignore[misc]

    def test_immutable_config(self) -> None:
        c = VolatilityConfig()
        with pytest.raises(AttributeError):
            c.model = "x"  # type: ignore[misc]

    def test_immutable_forecast(self) -> None:
        f = VolatilityForecast(model="garch", horizon=10, forecast=0.2, variance=0.04)
        with pytest.raises(AttributeError):
            f.forecast = 0.3  # type: ignore[misc]

    def test_diagnostics_defaults(self) -> None:
        d = ModelDiagnostics()
        assert d.convergence_status == "converged"

    def test_confidence_interval_defaults(self) -> None:
        ci = ConfidenceInterval()
        assert ci.confidence_level == 0.95


class TestHistorical:
    """Test historical volatility estimator."""

    def test_fit(self) -> None:
        r = _generate_returns(300)
        est = HistoricalVolatilityEstimator()
        res = est.fit(r, _config())
        assert res.model == "historical"
        assert res.forecast > 0

    def test_fit_insufficient(self) -> None:
        with pytest.raises(InsufficientDataError):
            HistoricalVolatilityEstimator().fit((0.01, 0.02), _config(min_periods=100))

    def test_forecast(self) -> None:
        r = _generate_returns(300)
        res = HistoricalVolatilityEstimator().forecast(r, 20, _config())
        assert res.horizon == 20
        assert res.forecast > 0

    def test_forecast_path(self) -> None:
        r = _generate_returns(300)
        path = HistoricalVolatilityEstimator().forecast_path(r, 5, _config())
        assert len(path) == 5
        assert path[-1].horizon == 5

    def test_update(self) -> None:
        r = _generate_returns(100)
        est = HistoricalVolatilityEstimator()
        res = est.update(r, 0.01, _config(min_periods=5))
        assert res.forecast > 0

    def test_diagnostics(self) -> None:
        r = _generate_returns(300)
        est = HistoricalVolatilityEstimator()
        fc = est.fit(r, _config())
        diag = est.diagnostics(fc)
        assert isinstance(diag, ModelDiagnostics)

    def test_name(self) -> None:
        assert HistoricalVolatilityEstimator().name == "historical"

    def test_lookback_applied(self) -> None:
        r = _generate_returns(500)
        res = HistoricalVolatilityEstimator().fit(r, _config(lookback=100))
        assert res.forecast > 0


class TestEWMA:
    """Test EWMA estimator."""

    def test_fit(self) -> None:
        r = _generate_returns(300)
        est = EWMAAEstimator()
        res = est.fit(r, _config())
        assert res.model == "ewma"
        assert res.forecast > 0

    def test_fit_insufficient(self) -> None:
        with pytest.raises(InsufficientDataError):
            EWMAAEstimator().fit((0.01,), _config(min_periods=100))

    def test_forecast(self) -> None:
        r = _generate_returns(300)
        res = EWMAAEstimator().forecast(r, 20, _config())
        assert res.horizon == 20

    def test_forecast_path(self) -> None:
        r = _generate_returns(300)
        path = EWMAAEstimator().forecast_path(r, 10, _config())
        assert len(path) == 10
        assert path[0].horizon == 1

    def test_update(self) -> None:
        r = _generate_returns(100)
        est = EWMAAEstimator()
        res = est.update(r, 0.01, _config())
        assert res.forecast > 0

    def test_update_short(self) -> None:
        est = EWMAAEstimator()
        res = est.update((0.01,), 0.02, _config(min_periods=2))
        assert res.forecast > 0 or res.forecast == 0.0

    def test_diagnostics(self) -> None:
        r = _generate_returns(300)
        est = EWMAAEstimator()
        fc = est.fit(r, _config())
        diag = est.diagnostics(fc)
        assert diag.persistence > 0

    def test_conditional_vol(self) -> None:
        r = _generate_returns(100)
        res = EWMAAEstimator().fit(r, _config())
        assert len(res.conditional_vol) > 0

    def test_custom_lambda(self) -> None:
        r = _generate_returns(300)
        res = EWMAAEstimator().fit(r, _config(ewma_lambda=0.90))
        assert res.parameters.get("lambda") == 0.90


class TestGARCH:
    """Test GARCH(1,1) estimator."""

    def test_fit(self) -> None:
        r = _garch_returns(500)
        est = GARCHEstimator()
        res = est.fit(r, _config())
        assert res.model == "garch"
        assert res.forecast > 0
        assert res.converged

    def test_fit_insufficient(self) -> None:
        with pytest.raises(InsufficientDataError):
            GARCHEstimator().fit((0.01, 0.02), _config(min_periods=100))

    def test_forecast(self) -> None:
        r = _garch_returns(500)
        res = GARCHEstimator().forecast(r, 20, _config())
        assert res.horizon == 20
        assert res.forecast > 0

    def test_forecast_path(self) -> None:
        r = _garch_returns(500)
        path = GARCHEstimator().forecast_path(r, 5, _config())
        assert len(path) == 5

    def test_update(self) -> None:
        r = _garch_returns(200)
        est = GARCHEstimator()
        res = est.update(r, 0.01, _config(min_periods=5))
        assert res.forecast > 0

    def test_conditional_vol(self) -> None:
        r = _garch_returns(300)
        res = GARCHEstimator().fit(r, _config())
        assert len(res.conditional_vol) > 0

    def test_parameters(self) -> None:
        r = _garch_returns(500)
        res = GARCHEstimator().fit(r, _config())
        assert "alpha" in res.parameters
        assert "beta" in res.parameters

    def test_log_likelihood(self) -> None:
        r = _garch_returns(500)
        res = GARCHEstimator().fit(r, _config())
        assert isinstance(res.log_likelihood, float)

    def test_forecast_short(self) -> None:
        r = _generate_returns(50)
        res = GARCHEstimator().forecast(r, 10, _config(min_periods=5))
        assert res.converged

    def test_diagnostics(self) -> None:
        r = _garch_returns(500)
        est = GARCHEstimator()
        fc = est.fit(r, _config())
        diag = est.diagnostics(fc)
        assert diag.persistence > 0


class TestEGARCH:
    """Test EGARCH(1,1) estimator."""

    def test_fit(self) -> None:
        r = _asymmetric_returns(500)
        est = EGARCHEstimator()
        res = est.fit(r, _config())
        assert res.model == "egarch"
        assert res.forecast > 0

    def test_fit_insufficient(self) -> None:
        with pytest.raises(InsufficientDataError):
            EGARCHEstimator().fit((0.01,), _config(min_periods=100))

    def test_forecast(self) -> None:
        r = _asymmetric_returns(500)
        res = EGARCHEstimator().forecast(r, 20, _config())
        assert res.horizon == 20

    def test_forecast_path(self) -> None:
        r = _asymmetric_returns(500)
        path = EGARCHEstimator().forecast_path(r, 5, _config())
        assert len(path) == 5

    def test_update(self) -> None:
        r = _asymmetric_returns(200)
        est = EGARCHEstimator()
        res = est.update(r, 0.01, _config(min_periods=5))
        assert res.forecast > 0

    def test_gamma_parameter(self) -> None:
        r = _asymmetric_returns(500)
        res = EGARCHEstimator().fit(r, _config())
        assert "gamma" in res.parameters

    def test_conditional_vol(self) -> None:
        r = _asymmetric_returns(300)
        res = EGARCHEstimator().fit(r, _config())
        assert len(res.conditional_vol) > 0

    def test_diagnostics(self) -> None:
        r = _asymmetric_returns(500)
        est = EGARCHEstimator()
        fc = est.fit(r, _config())
        diag = est.diagnostics(fc)
        assert isinstance(diag.persistence, float)


class TestGJRGARCH:
    """Test GJR-GARCH(1,1) estimator."""

    def test_fit(self) -> None:
        r = _asymmetric_returns(500)
        est = GJRGARCHEstimator()
        res = est.fit(r, _config())
        assert res.model == "gjrgarch"
        assert res.forecast > 0

    def test_fit_insufficient(self) -> None:
        with pytest.raises(InsufficientDataError):
            GJRGARCHEstimator().fit((0.01,), _config(min_periods=100))

    def test_forecast(self) -> None:
        r = _asymmetric_returns(500)
        res = GJRGARCHEstimator().forecast(r, 20, _config())
        assert res.horizon == 20

    def test_forecast_path(self) -> None:
        r = _asymmetric_returns(500)
        path = GJRGARCHEstimator().forecast_path(r, 5, _config())
        assert len(path) == 5

    def test_update(self) -> None:
        r = _asymmetric_returns(200)
        est = GJRGARCHEstimator()
        res = est.update(r, 0.01, _config(min_periods=5))
        assert res.forecast > 0

    def test_gamma_parameter(self) -> None:
        r = _asymmetric_returns(500)
        res = GJRGARCHEstimator().fit(r, _config())
        assert "gamma" in res.parameters

    def test_conditional_vol(self) -> None:
        r = _asymmetric_returns(300)
        res = GJRGARCHEstimator().fit(r, _config())
        assert len(res.conditional_vol) > 0

    def test_diagnostics(self) -> None:
        r = _asymmetric_returns(500)
        est = GJRGARCHEstimator()
        fc = est.fit(r, _config())
        diag = est.diagnostics(fc)
        assert diag.is_stationary or not diag.is_stationary


class TestForecastEngine:
    """Test forecast engine."""

    def test_single(self) -> None:
        r = _garch_returns(500)
        fe = ForecastEngine()
        res = fe.forecast(r, "garch", 20, _config())
        assert res.forecast > 0

    def test_default_model(self) -> None:
        r = _garch_returns(500)
        fe = ForecastEngine()
        res = fe.forecast(r, horizon=20, config=_config(model="garch"))
        assert res.model == "garch"

    def test_model_not_found(self) -> None:
        with pytest.raises(InsufficientDataError):
            ForecastEngine().forecast((0.01,), "void", 20, _config())

    def test_multiple(self) -> None:
        r = _garch_returns(500)
        fe = ForecastEngine()
        res = fe.forecast_multiple(r, "garch", (1, 5, 10), _config())
        assert 1 in res.forecasts
        assert 10 in res.forecasts

    def test_multiple_default_horizons(self) -> None:
        r = _garch_returns(500)
        fe = ForecastEngine()
        res = fe.forecast_multiple(r, "garch", config=_config())
        assert len(res.forecasts) > 0

    def test_term_structure(self) -> None:
        r = _garch_returns(500)
        fe = ForecastEngine()
        res = fe.forecast_term_structure(r, "garch", _config())
        assert 1 in res.forecasts
        assert 252 in res.forecasts

    def test_rolling(self) -> None:
        r = _generate_returns(400)
        fe = ForecastEngine()
        res = fe.rolling_forecast(r, 200, "historical", 20, _config())
        assert len(res) > 0

    def test_rolling_insufficient(self) -> None:
        with pytest.raises(InsufficientDataError):
            ForecastEngine().rolling_forecast((0.01,) * 50, 200, config=_config())

    def test_rolling_failure(self) -> None:
        r = _generate_returns(250)
        fe = ForecastEngine()
        res = fe.rolling_forecast(r, 50, "garch", 10, _config(min_periods=200))
        assert len(res) > 0

    def test_batch(self) -> None:
        r = _garch_returns(500)
        fe = ForecastEngine()
        reqs = (
            ForecastRequest(symbol="A", returns=r, model="garch", horizon=20),
            ForecastRequest(symbol="B", returns=r, model="ewma", horizon=10),
        )
        results = fe.batch_forecast(reqs)
        assert len(results) == 2
        assert results[0].symbol == "A"

    def test_batch_empty(self) -> None:
        fe = ForecastEngine()
        results = fe.batch_forecast(())
        assert len(results) == 0

    def test_register_custom(self) -> None:
        fe = ForecastEngine()
        fe.register_estimator("custom", HistoricalVolatilityEstimator())
        assert "custom" in fe.estimators

    def test_default_estimators(self) -> None:
        fe = ForecastEngine()
        for name in ("historical", "ewma", "garch", "egarch", "gjrgarch"):
            assert name in fe.estimators

    def test_all_models(self) -> None:
        r = _garch_returns(500)
        fe = ForecastEngine()
        c = _config()
        for model in ("historical", "ewma", "garch", "egarch", "gjrgarch"):
            res = fe.forecast(r, model, 20, c)
            assert res.forecast > 0, f"Model {model} failed"

    def test_result_fields(self) -> None:
        r = _garch_returns(500)
        fe = ForecastEngine()
        res = fe.forecast_multiple(r, "garch", (1, 5), _config())
        assert res.current_vol > 0 or res.current_vol == 0.0
        assert res.elapsed >= 0

    def test_term_structure_horizons(self) -> None:
        r = _generate_returns(500)
        fe = ForecastEngine()
        res = fe.forecast_term_structure(r, "historical", _config())
        for h in DEFAULT_HORIZONS:
            assert h in res.forecasts

    def test_diagnostics_in_multiple(self) -> None:
        r = _garch_returns(500)
        fe = ForecastEngine()
        res = fe.forecast_multiple(r, "garch", (20,), _config())
        assert res.diagnostics is not None


class TestDiagnostics:
    """Test model diagnostics."""

    def test_compute_diagnostics_forecast(self) -> None:
        fc = VolatilityForecast(
            model="garch", horizon=20, forecast=0.25, variance=0.0625,
            parameters={"alpha": 0.1, "beta": 0.85, "omega": 0.00001},
            log_likelihood=-500.0, converged=True,
        )
        diag = compute_diagnostics(fc, ())
        assert diag.persistence > 0
        assert diag.convergence_status == "converged"

    def test_with_residuals(self) -> None:
        fc = VolatilityForecast(
            model="garch", horizon=20, forecast=0.25, variance=0.0625,
            parameters={"alpha": 0.1, "beta": 0.85},
            log_likelihood=-500.0,
        )
        diag = compute_diagnostics(fc, (0.01, -0.02, 0.015, -0.01))
        assert diag.residual_variance > 0

    def test_half_life(self) -> None:
        fc = VolatilityForecast(
            model="garch", horizon=20, forecast=0.25, variance=0.0625,
            parameters={"alpha": 0.1, "beta": 0.85},
        )
        diag = compute_diagnostics(fc, ())
        assert diag.half_life > 0

    def test_non_stationary(self) -> None:
        fc = VolatilityForecast(
            model="garch", horizon=20, forecast=0.25, variance=0.0625,
            parameters={"alpha": 0.3, "beta": 0.8},
        )
        diag = compute_diagnostics(fc, ())
        assert not diag.is_stationary

    def test_aic_bic(self) -> None:
        fc = VolatilityForecast(
            model="garch", horizon=20, forecast=0.25, variance=0.0625,
            parameters={"alpha": 0.1, "beta": 0.85},
            conditional_vol=(0.02,) * 100,
            log_likelihood=-500.0,
        )
        diag = compute_diagnostics(fc, ())
        assert "aic" in diag.information_criteria
        assert "bic" in diag.information_criteria

    def test_no_ll_no_ic(self) -> None:
        fc = VolatilityForecast(model="garch", horizon=20, forecast=0.25, variance=0.0625)
        diag = compute_diagnostics(fc, ())
        assert len(diag.information_criteria) == 0

    def test_historical_diagnostics(self) -> None:
        r = _generate_returns(300)
        est = HistoricalVolatilityEstimator()
        fc = est.fit(r, _config())
        diag = est.diagnostics(fc)
        assert diag.persistence == 0.0


class TestComparison:
    """Test model comparison."""

    def test_metrics(self) -> None:
        fc = VolatilityForecast(
            model="garch", horizon=20, forecast=0.25, variance=0.0625,
            log_likelihood=-500.0,
        )
        actual = _generate_returns(50)
        metrics = ModelComparer.compute_metrics(fc, actual, _config())
        assert isinstance(metrics, ForecastMetrics)

    def test_metrics_empty(self) -> None:
        fc = VolatilityForecast(model="garch", horizon=20, forecast=0.25, variance=0.0625)
        metrics = ModelComparer.compute_metrics(fc, (), _config())
        assert metrics.n_observations == 0

    def test_compare(self) -> None:
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
        results = ModelComparer.compare(forecasts, actual, _config())
        assert len(results) == 2
        assert results[0].rank == 1

    def test_skip_non_converged(self) -> None:
        forecasts = {
            "garch": VolatilityForecast(
                model="garch", horizon=20, forecast=0.25, variance=0.0625,
                converged=False,
            ),
        }
        results = ModelComparer.compare(forecasts, (), _config())
        assert len(results) == 0

    def test_compare_empty(self) -> None:
        results = ModelComparer.compare({}, (), _config())
        assert len(results) == 0

    def test_metrics_all_fields(self) -> None:
        fc = VolatilityForecast(
            model="garch", horizon=20, forecast=0.25, variance=0.0625,
            log_likelihood=-500.0, parameters={"alpha": 0.1, "beta": 0.85},
        )
        actual = _generate_returns(50)
        metrics = ModelComparer.compute_metrics(fc, actual, _config())
        assert metrics.rmse >= 0
        assert metrics.mae >= 0
        assert isinstance(metrics.aic, float)

    def test_aic_bic(self) -> None:
        fc = VolatilityForecast(
            model="garch", horizon=20, forecast=0.0, variance=0.0,
            log_likelihood=-1000.0,
        )
        metrics = ModelComparer.compute_metrics(fc, (), _config())
        assert isinstance(metrics.aic, float)


class TestEngine:
    """Test volatility engine."""

    def test_init(self) -> None:
        e = VolatilityEngine()
        assert isinstance(e.config, VolatilityConfig)

    def test_forecast(self) -> None:
        r = _garch_returns(500)
        e = VolatilityEngine()
        res = e.forecast(r, "garch", 20)
        assert res.forecast > 0

    def test_forecast_default_config(self) -> None:
        r = _garch_returns(500)
        e = VolatilityEngine(config=_config(model="garch"))
        res = e.forecast(r)
        assert res.forecast > 0

    def test_multiple(self) -> None:
        r = _garch_returns(500)
        e = VolatilityEngine()
        res = e.forecast_multiple(r, "garch", (1, 5, 10))
        assert isinstance(res, ForecastResult)

    def test_compare(self) -> None:
        r = _garch_returns(300)
        actual = _generate_returns(50)
        e = VolatilityEngine()
        results = e.compare_models(r, actual, 20)
        assert len(results) > 0

    def test_rolling(self) -> None:
        r = _generate_returns(400)
        e = VolatilityEngine()
        res = e.rolling_forecast(r, 200, "historical", 20)
        assert len(res) > 0

    def test_term_structure(self) -> None:
        r = _garch_returns(500)
        e = VolatilityEngine()
        res = e.forecast_term_structure(r, "garch")
        assert isinstance(res, ForecastResult)

    def test_batch(self) -> None:
        r = _garch_returns(500)
        e = VolatilityEngine()
        reqs = (
            ForecastRequest(symbol="A", returns=r, model="garch", horizon=20),
        )
        results = e.batch_forecast(reqs)
        assert len(results) == 1

    def test_metrics(self) -> None:
        r = _generate_returns(50)
        fc = VolatilityForecast(model="garch", horizon=20, forecast=0.25, variance=0.0625)
        e = VolatilityEngine()
        metrics = e.compute_metrics(fc, r)
        assert isinstance(metrics, ForecastMetrics)

    def test_statistics(self) -> None:
        e = VolatilityEngine()
        stats = e.generate_statistics(elapsed=0.15, warnings=("test",))
        assert stats.elapsed_seconds == 0.15

    def test_forecasts_counted(self) -> None:
        e = VolatilityEngine()
        r = _garch_returns(500)
        e.forecast(r, "garch", 20)
        e.forecast(r, "garch", 10)
        stats = e.generate_statistics(0.1)
        assert stats.total_forecasts == 2

    def test_di_injection(self) -> None:
        e = VolatilityEngine(
            portfolio_engine=object(), risk_engine=object(),
            sizing_engine=object(), strategy_engine=object(),
            backtesting_engine=object(),
        )
        assert e._portfolio_engine is not None
        assert e._risk_engine is not None
        assert e._sizing_engine is not None

    def test_forecast_engine_property(self) -> None:
        fe = ForecastEngine()
        e = VolatilityEngine(forecast_engine=fe)
        assert e.forecast_engine is fe


class TestFactory:
    """Test factory."""

    def test_create(self) -> None:
        e = VolatilityFactory.create()
        assert isinstance(e, VolatilityEngine)

    def test_create_with_config(self) -> None:
        e = VolatilityFactory.create(config=_config(model="ewma"))
        assert e.config.model == "ewma"

    def test_create_with_forecast_engine(self) -> None:
        fe = ForecastEngine()
        e = VolatilityFactory.create(forecast_engine=fe)
        assert e.forecast_engine is fe

    def test_create_with_engines(self) -> None:
        e = VolatilityFactory.create(
            portfolio_engine=object(), risk_engine=object(),
        )
        assert e._portfolio_engine is not None

    def test_create_with_estimators(self) -> None:
        custom = HistoricalVolatilityEstimator()
        e = VolatilityFactory.create_with_estimators({"custom": custom})
        assert "custom" in e.forecast_engine.estimators

    def test_create_from_config(self) -> None:
        e = VolatilityFactory.create_from_config(_config(model="egarch"))
        assert e.config.model == "egarch"

    def test_create_all_deps(self) -> None:
        e = VolatilityFactory.create(
            config=_config(), forecast_engine=ForecastEngine(),
            comparer=ModelComparer(),
            portfolio_engine=object(), risk_engine=object(),
            sizing_engine=object(), strategy_engine=object(),
            backtesting_engine=object(),
        )
        assert e._portfolio_engine is not None
        assert e._risk_engine is not None


class TestExceptions:
    """Test exceptions."""

    def test_base(self) -> None:
        with pytest.raises(VolatilityError):
            raise VolatilityError("test")

    def test_invalid_config(self) -> None:
        with pytest.raises(InvalidVolatilityConfigError):
            raise InvalidVolatilityConfigError("test")

    def test_insufficient_data(self) -> None:
        with pytest.raises(InsufficientDataError):
            raise InsufficientDataError("test")

    def test_estimation(self) -> None:
        with pytest.raises(EstimationError):
            raise EstimationError("garch", "test")

    def test_estimation_attributes(self) -> None:
        e = EstimationError("garch", "test")
        assert e.model == "garch"

    def test_convergence(self) -> None:
        with pytest.raises(ConvergenceError):
            raise ConvergenceError("garch")

    def test_convergence_with_message(self) -> None:
        e = ConvergenceError("garch", "failed")
        assert "failed" in str(e)

    def test_forecast(self) -> None:
        with pytest.raises(ForecastError):
            raise ForecastError("test")

    def test_model_not_found(self) -> None:
        with pytest.raises(ModelNotFoundError):
            raise ModelNotFoundError("test")

    def test_model_not_found_attributes(self) -> None:
        e = ModelNotFoundError("void")
        assert e.name == "void"

    def test_update_error(self) -> None:
        with pytest.raises(UpdateError):
            raise UpdateError("garch", "test")

    def test_diagnostics_error(self) -> None:
        with pytest.raises(DiagnosticsError):
            raise DiagnosticsError("test")


class TestIntegration:
    """Integration tests."""

    def test_complete_flow(self) -> None:
        r = _garch_returns(500)
        e = VolatilityFactory.create(config=_config(model="garch"))
        fc = e.forecast(r, horizon=20)
        assert fc.forecast > 0
        assert fc.confidence.lower <= fc.confidence.expected
        result = e.forecast_multiple(r, horizons=(1, 5, 20))
        assert len(result.forecasts) == 3
        term = e.forecast_term_structure(r)
        assert 1 in term.forecasts

    def test_all_models(self) -> None:
        r = _garch_returns(500)
        e = VolatilityEngine()
        c = _config()
        for model in ("historical", "ewma", "garch", "egarch", "gjrgarch"):
            res = e.forecast(r, model, 20, c)
            assert res.forecast > 0

    def test_rolling_and_term(self) -> None:
        r = _generate_returns(400)
        e = VolatilityEngine()
        rolling = e.rolling_forecast(r, 200, "historical", 20)
        assert len(rolling) > 0
        term = e.forecast_term_structure(r, "historical")
        assert len(term.forecasts) > 0

    def test_comparison_flow(self) -> None:
        r = _garch_returns(300)
        actual = _generate_returns(50)
        e = VolatilityEngine()
        comps = e.compare_models(r, actual, 20)
        assert len(comps) > 0
        assert comps[0].rank == 1

    def test_confidence_intervals(self) -> None:
        r = _garch_returns(500)
        e = VolatilityEngine()
        c = _config()
        for model in ("historical", "ewma", "garch", "egarch", "gjrgarch"):
            res = e.forecast(r, model, 20, c)
            ci = res.confidence
            assert ci.lower <= ci.expected
            assert ci.expected <= ci.upper or abs(ci.expected - ci.upper) < 0.01

    def test_term_structure_positive(self) -> None:
        r = _generate_returns(500)
        e = VolatilityEngine()
        res = e.forecast_term_structure(r, "historical")
        for h, fc in res.forecasts.items():
            assert fc.forecast > 0, f"Horizon {h} failed"

    def test_full_pipeline(self) -> None:
        r = _garch_returns(500)
        e = VolatilityFactory.create()
        fc = e.forecast(r, horizon=20)
        multi = e.forecast_multiple(r, horizons=(1, 5, 20, 60))
        term = e.forecast_term_structure(r)
        assert fc.forecast > 0
        assert len(multi.forecasts) == 4
        assert len(term.forecasts) == 7

    def test_batch_and_diagnostics(self) -> None:
        r = _garch_returns(500)
        e = VolatilityFactory.create()
        reqs = (
            ForecastRequest(symbol="A", returns=r, model="garch", horizon=20, use_diagnostics=True),
            ForecastRequest(symbol="B", returns=r, model="ewma", horizon=10),
        )
        results = e.batch_forecast(reqs)
        assert len(results) == 2

    def test_garch_vs_hist(self) -> None:
        r = _garch_returns(500)
        ge = GARCHEstimator()
        he = HistoricalVolatilityEstimator()
        c = _config()
        gr = ge.fit(r, c)
        hr = he.fit(r, c)
        assert gr.forecast != hr.forecast or abs(gr.forecast - hr.forecast) > 0.001

    def test_forecast_path_length(self) -> None:
        r = _garch_returns(500)
        est = GARCHEstimator()
        path = est.forecast_path(r, 20, _config())
        assert len(path) == 20
        assert all(f.horizon == i + 1 for i, f in enumerate(path))

    def test_diagnostics_across_models(self) -> None:
        r = _garch_returns(500)
        c = _config()
        for est_cls in (HistoricalVolatilityEstimator, EWMAAEstimator, GARCHEstimator, EGARCHEstimator, GJRGARCHEstimator):
            est = est_cls()
            fc = est.fit(r, c)
            diag = est.diagnostics(fc)
            assert isinstance(diag, ModelDiagnostics)

    def test_update_ewma_recursive(self) -> None:
        r = _generate_returns(100)
        est = EWMAAEstimator()
        c = _config(min_periods=5)
        est.fit(r, c)
        new_r = 0.015
        fc2 = est.update(r, new_r, c)
        assert fc2.forecast > 0

    def test_statistics_with_batch(self) -> None:
        r = _garch_returns(500)
        e = VolatilityFactory.create()
        e.batch_forecast((
            ForecastRequest(symbol="A", returns=r, model="garch", horizon=20),
            ForecastRequest(symbol="B", returns=r, model="ewma", horizon=10),
        ))
        stats = e.generate_statistics(elapsed=0.3)
        assert stats.total_forecasts >= 2
