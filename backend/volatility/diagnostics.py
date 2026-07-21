"""Volatility model diagnostics.

Computes residual variance, persistence, half-life, stationarity checks,
and information criteria for fitted volatility models.
"""

from __future__ import annotations

import math

from backend.volatility.models import ModelDiagnostics, VolatilityForecast


def compute_diagnostics(
    forecast: VolatilityForecast,
    residuals: tuple[float, ...],
) -> ModelDiagnostics:
    """Compute diagnostics for a volatility forecast.

    Args:
        forecast:  Fitted volatility forecast.
        residuals: Model residuals (empty if not available).

    Returns:
        ModelDiagnostics with diagnostic information.
    """
    n = len(forecast.conditional_vol) if forecast.conditional_vol else 0
    n_params = len(forecast.parameters) if forecast.parameters else 0

    residual_variance = 0.0
    if residuals and len(residuals) > 1:
        mean_r = sum(residuals) / len(residuals)
        residual_variance = sum((r - mean_r) ** 2 for r in residuals) / (len(residuals) - 1)

    persistence = _compute_persistence(forecast)
    half_life = _compute_half_life(persistence)
    is_stationary = persistence < 1.0 if persistence > 0 else True

    ic: dict[str, float] = {}
    ll = forecast.log_likelihood
    if ll != 0:
        ic["aic"] = 2 * n_params - 2 * ll if n_params > 0 else 0.0
        ic["bic"] = (math.log(max(n, 1)) * n_params - 2 * ll) if n > 0 else 0.0

    conv_status = "converged" if forecast.converged else "failed"

    return ModelDiagnostics(
        residual_variance=residual_variance,
        persistence=persistence,
        half_life=half_life,
        is_stationary=is_stationary,
        information_criteria=ic,
        convergence_status=conv_status,
        n_observations=n,
        n_parameters=n_params,
    )


def _compute_persistence(forecast: VolatilityForecast) -> float:
    """Compute model persistence from parameters."""
    params = forecast.parameters
    model = forecast.model

    if model == "historical":
        return 0.0
    elif model == "ewma":
        return params.get("lambda", 0.94)
    elif model == "garch":
        return params.get("alpha", 0.0) + params.get("beta", 0.0)
    elif model == "egarch":
        return params.get("beta", 0.0)
    elif model == "gjrgarch":
        alpha = params.get("alpha", 0.0)
        beta = params.get("beta", 0.0)
        gamma_p = params.get("gamma", 0.0)
        return alpha + beta + 0.5 * gamma_p
    return 0.0


def _compute_half_life(persistence: float) -> float:
    """Compute volatility half-life in days."""
    if persistence <= 0 or persistence >= 1:
        return 0.0
    return -math.log(2) / math.log(persistence)
