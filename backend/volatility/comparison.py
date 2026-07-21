"""Volatility model comparison.

Compares models using RMSE, MAE, MAPE, AIC, BIC, bias, and stability.
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


def _realized_vol(returns: tuple[float, ...], annual_factor: float) -> float:
    """Compute realized volatility from a window of returns."""
    if len(returns) < 2:
        return 0.0
    mean_ret = sum(returns) / len(returns)
    variance = sum((r - mean_ret) ** 2 for r in returns) / (len(returns) - 1)
    return math.sqrt(variance) * math.sqrt(annual_factor) if variance > 0 else 0.0


class ModelComparer:
    """Model comparison engine.

    Evaluates and ranks volatility models using standard
    forecast evaluation metrics.
    """

    @staticmethod
    def compute_metrics(
        forecast: VolatilityForecast,
        actual_returns: tuple[float, ...],
        config: VolatilityConfig,
    ) -> ForecastMetrics:
        """Compute forecast quality metrics.

        Args:
            forecast:       Forecast.
            actual_returns: Actual subsequent returns.
            config:         Configuration.

        Returns:
            ForecastMetrics.
        """
        n_obs = len(actual_returns)
        n_params = max(len(forecast.parameters) if forecast.parameters else 1, 1)

        if n_obs == 0:
            ll = forecast.log_likelihood
            return ForecastMetrics(
                log_likelihood=ll,
                aic=_aic(ll, n_params),
                bic=_bic(ll, n_params, 1),
                n_observations=n_obs,
                n_parameters=n_params,
            )

        annual_factor = config.annual_factor
        window_size = min(20, n_obs)
        realized = []
        forecasted = []

        for i in range(window_size, n_obs + 1):
            window_ret = actual_returns[i - window_size:i]
            rv = _realized_vol(tuple(window_ret), annual_factor)
            realized.append(rv)
            forecasted.append(forecast.forecast)

        min_len = min(len(realized), len(forecasted))
        realized = realized[:min_len]
        forecasted = forecasted[:min_len]

        if min_len == 0:
            ll = forecast.log_likelihood
            return ForecastMetrics(
                log_likelihood=ll,
                aic=_aic(ll, n_params),
                bic=_bic(ll, n_params, n_obs),
                n_observations=n_obs,
                n_parameters=n_params,
            )

        errors = [rv - fv for rv, fv in zip(realized, forecasted)]
        abs_err = [abs(e) for e in errors]
        pct_err = [
            abs(e) / max(abs(rv), EPSILON) for e, rv in zip(errors, realized)
        ]

        rmse = math.sqrt(sum(e ** 2 for e in errors) / min_len)
        mae = sum(abs_err) / min_len
        mape = sum(pct_err) / min_len
        bias = sum(errors) / min_len
        mean_e = bias
        stability = (
            math.sqrt(sum((e - mean_e) ** 2 for e in errors) / max(min_len - 1, 1))
            if min_len > 1 else 0.0
        )

        ll = forecast.log_likelihood
        return ForecastMetrics(
            rmse=rmse, mae=mae, mape=mape, bias=bias,
            stability=stability, log_likelihood=ll,
            aic=_aic(ll, n_params),
            bic=_bic(ll, n_params, n_obs),
            n_observations=n_obs, n_parameters=n_params,
        )

    @staticmethod
    def compare(
        forecasts: dict[str, VolatilityForecast],
        actual_returns: tuple[float, ...],
        config: VolatilityConfig,
    ) -> tuple[ModelComparison, ...]:
        """Compare multiple models and return ranked results.

        Args:
            forecasts:      Model name -> forecast.
            actual_returns: Actual returns for evaluation.

        Returns:
            Tuple of ModelComparison sorted by rank.
        """
        comparisons: list[ModelComparison] = []
        for model_name, forecast in forecasts.items():
            if not forecast.converged:
                continue
            metrics = ModelComparer.compute_metrics(forecast, actual_returns, config)
            comparisons.append(
                ModelComparison(model_name=model_name, rank=0, metrics=metrics, score=0.0)
            )

        if not comparisons:
            return ()

        scores = []
        for comp in comparisons:
            rmse_s = 1.0 / (1.0 + comp.metrics.rmse) if comp.metrics.rmse > 0 else 1.0
            mae_s = 1.0 / (1.0 + comp.metrics.mae) if comp.metrics.mae > 0 else 1.0
            bias_s = 1.0 / (1.0 + abs(comp.metrics.bias)) if comp.metrics.bias != 0 else 1.0
            ll_s = (
                1.0 / (1.0 + abs(comp.metrics.log_likelihood))
                if comp.metrics.log_likelihood < 0
                else min(comp.metrics.log_likelihood / 100, 1.0)
            )
            score = rmse_s * 0.3 + mae_s * 0.2 + bias_s * 0.2 + ll_s * 0.15
            scores.append(score)

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


def _aic(log_likelihood: float, n_params: int) -> float:
    """Compute AIC."""
    if log_likelihood == 0:
        return 0.0
    return 2 * n_params - 2 * log_likelihood


def _bic(log_likelihood: float, n_params: int, n_obs: int) -> float:
    """Compute BIC."""
    if n_obs <= 0 or log_likelihood == 0:
        return 0.0
    return math.log(n_obs) * n_params - 2 * log_likelihood
