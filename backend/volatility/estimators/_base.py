"""Shared helper functions for volatility estimators."""

from __future__ import annotations

import math

from backend.volatility.models import ConfidenceInterval, VolatilityConfig


def _mean(values: tuple[float, ...]) -> float:
    """Compute mean."""
    return sum(values) / len(values) if values else 0.0


def _variance(values: tuple[float, ...], ddof: int = 1) -> float:
    """Compute variance."""
    if len(values) < 2:
        return 0.0
    m = _mean(values)
    return sum((v - m) ** 2 for v in values) / (len(values) - ddof)


def _stdev(values: tuple[float, ...], ddof: int = 1) -> float:
    """Compute standard deviation."""
    return math.sqrt(_variance(values, ddof))


def _annualize(vol: float, config: VolatilityConfig) -> float:
    """Annualize volatility."""
    return vol * math.sqrt(config.annual_factor)


def _confidence_interval(
    forecast: float,
    variance: float,
    config: VolatilityConfig,
) -> ConfidenceInterval:
    """Compute confidence interval."""
    z = 1.96 if config.confidence_level >= 0.95 else 1.645
    std_err = math.sqrt(variance) if variance > 0 else forecast * 0.1
    return ConfidenceInterval(
        lower=max(0.0, forecast - z * std_err),
        expected=forecast,
        upper=forecast + z * std_err,
        confidence_level=config.confidence_level,
    )


def _log_likelihood_gaussian(
    returns: tuple[float, ...],
    variances: tuple[float, ...],
) -> float:
    """Compute Gaussian log-likelihood."""
    n = min(len(returns), len(variances))
    if n == 0:
        return 0.0
    ll = 0.0
    for i in range(n):
        if variances[i] > 0:
            ll += -0.5 * (math.log(2 * math.pi * variances[i]) + returns[i] ** 2 / variances[i])
    return ll


def _aic(log_likelihood: float, n_params: int) -> float:
    """Compute Akaike Information Criterion."""
    if log_likelihood == 0:
        return 0.0
    return 2 * n_params - 2 * log_likelihood


def _bic(log_likelihood: float, n_params: int, n_obs: int) -> float:
    """Compute Bayesian Information Criterion."""
    if n_obs <= 0 or log_likelihood == 0:
        return 0.0
    return math.log(n_obs) * n_params - 2 * log_likelihood
