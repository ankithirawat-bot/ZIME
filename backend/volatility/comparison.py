"""Volatility model comparison.

Compares volatility models using RMSE, MAE, MAPE, AIC, BIC,
forecast bias, and stability metrics.
"""

from __future__ import annotations

import math

from backend.volatility.models import (
    ForecastMetrics,
    ModelComparison,
    VolatilityConfig,
    VolatilityForecast,
)

EPSILON = 1e-10


class ModelComparer:
    """Model comparison engine for volatility forecasts.

    Evaluates and ranks volatility models using standard forecast
    evaluation metrics.
    """

    @staticmethod
    def compute_metrics(
        forecast: VolatilityForecast,
        actual_returns: tuple[float, ...],
        config: VolatilityConfig,
    ) -> ForecastMetrics:
        """Compute forecast quality metrics.

        Args:
            forecast:       Volatility forecast.
            actual_returns: Actual subsequent returns.
            config:         Volatility configuration.

        Returns:
            ForecastMetrics with quality metrics.
        """
        n_obs = len(actual_returns)
        n_params = len(forecast.parameters) if forecast.parameters else 1

        if n_obs == 0:
            return ForecastMetrics(
                log_likelihood=forecast.log_likelihood,
                aic=ModelComparer._aic(forecast.log_likelihood, n_params),
                bic=ModelComparer._bic(forecast.log_likelihood, n_params, max(n_obs, 1)),
                n_observations=n_obs,
                n_parameters=n_params,
            )

        annual_factor = config.annual_factor
        realized_vol = []
        forecast_vol = []
        window_size = min(20, n_obs)

        for i in range(window_size, n_obs + 1):
            window_ret = actual_returns[i - window_size:i]
            rv = _realized_vol(tuple(window_ret), annual_factor)
            realized_vol.append(rv)
            fv = forecast.forecast if n_obs > 0 else 0.0
            forecast_vol.append(fv)

        min_len = min(len(realized_vol), len(forecast_vol))
        realized_vol = realized_vol[:min_len]
        forecast_vol = forecast_vol[:min_len]

        if min_len == 0:
            return ForecastMetrics(
                log_likelihood=forecast.log_likelihood,
                aic=ModelComparer._aic(forecast.log_likelihood, n_params),
                bic=ModelComparer._bic(forecast.log_likelihood, n_params, max(n_obs, 1)),
                n_observations=n_obs,
                n_parameters=n_params,
            )

        errors = [rv - fv for rv, fv in zip(realized_vol, forecast_vol)]
        abs_errors = [abs(e) for e in errors]
        pct_errors = [
            abs(e) / max(abs(rv), EPSILON) for e, rv in zip(errors, realized_vol)
        ]

        rmse = math.sqrt(sum(e ** 2 for e in errors) / min_len) if min_len > 0 else 0.0
        mae = sum(abs_errors) / min_len if min_len > 0 else 0.0
        mape = sum(pct_errors) / min_len if min_len > 0 else 0.0
        bias = sum(errors) / min_len if min_len > 0 else 0.0
        mean_error = bias
        stability = (
            math.sqrt(sum((e - mean_error) ** 2 for e in errors) / max(min_len - 1, 1))
            if min_len > 1
            else 0.0
        )

        ll = forecast.log_likelihood
        n_params_adj = max(n_params, 1)
        n_obs_adj = max(n_obs, 1)

        return ForecastMetrics(
            rmse=rmse,
            mae=mae,
            mape=mape,
            bias=bias,
            stability=stability,
            log_likelihood=ll,
            aic=ModelComparer._aic(ll, n_params_adj),
            bic=ModelComparer._bic(ll, n_params_adj, n_obs_adj),
            n_observations=n_obs,
            n_parameters=n_params,
        )

    @staticmethod
    def _aic(log_likelihood: float, n_params: int) -> float:
        """Compute Akaike Information Criterion."""
        return 2 * n_params - 2 * log_likelihood if log_likelihood != 0 else 0.0

    @staticmethod
    def _bic(log_likelihood: float, n_params: int, n_obs: int) -> float:
        """Compute Bayesian Information Criterion."""
        if n_obs <= 0 or log_likelihood == 0:
            return 0.0
        return math.log(n_obs) * n_params - 2 * log_likelihood

    @staticmethod
    def compare(
        forecasts: dict[str, VolatilityForecast],
        actual_returns: tuple[float, ...],
        config: VolatilityConfig,
    ) -> tuple[ModelComparison, ...]:
        """Compare multiple models and return ranked results.

        Args:
            forecasts:       Dictionary of model name -> forecast.
            actual_returns:  Actual subsequent returns.
            config:          Volatility configuration.

        Returns:
            Tuple of ModelComparison sorted by rank (best first).
        """
        comparisons: list[ModelComparison] = []

        for model_name, forecast in forecasts.items():
            if not forecast.converged:
                continue
            metrics = ModelComparer.compute_metrics(
                forecast, actual_returns, config
            )
            comparisons.append(
                ModelComparison(
                    model_name=model_name,
                    rank=0,
                    metrics=metrics,
                    score=0.0,
                )
            )

        if not comparisons:
            return ()

        scores = []
        for comp in comparisons:
            rmse_score = 1.0 / (1.0 + comp.metrics.rmse) if comp.metrics.rmse > 0 else 1.0
            mae_score = 1.0 / (1.0 + comp.metrics.mae) if comp.metrics.mae > 0 else 1.0
            bias_score = 1.0 / (1.0 + abs(comp.metrics.bias)) if comp.metrics.bias != 0 else 1.0
            ll_score = (
                1.0 / (1.0 + abs(comp.metrics.log_likelihood))
                if comp.metrics.log_likelihood < 0
                else min(comp.metrics.log_likelihood / 100, 1.0)
            )
            weight = (
                rmse_score * 0.3
                + mae_score * 0.2
                + bias_score * 0.2
                + ll_score * 0.15
            )
            scores.append(weight)

        ranked = sorted(
            [
                ModelComparison(
                    model_name=comp.model_name,
                    rank=i + 1,
                    metrics=comp.metrics,
                    score=scores[idx],
                )
                for i, (idx, comp) in enumerate(
                    sorted(
                        enumerate(comparisons),
                        key=lambda x: scores[x[0]],
                        reverse=True,
                    )
                )
            ],
            key=lambda x: x.rank,
        )

        return tuple(ranked)


def _realized_vol(returns: tuple[float, ...], annual_factor: float) -> float:
    """Compute realized volatility from a window of returns."""
    if len(returns) < 2:
        return 0.0
    mean_ret = sum(returns) / len(returns)
    variance = sum((r - mean_ret) ** 2 for r in returns) / (len(returns) - 1)
    return math.sqrt(variance) * math.sqrt(annual_factor) if variance > 0 else 0.0
