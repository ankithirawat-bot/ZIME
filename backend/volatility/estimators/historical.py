"""Historical volatility estimator.

Rolling standard deviation with configurable lookback and annualization.
"""

from __future__ import annotations

import math

from backend.volatility.diagnostics import compute_diagnostics
from backend.volatility.exceptions import InsufficientDataError
from backend.volatility.models import (
    ModelDiagnostics,
    VolatilityConfig,
    VolatilityForecast,
)

from ._base import (
    _annualize,
    _confidence_interval,
    _stdev,
)


class HistoricalVolatilityEstimator:
    """Historical volatility estimator using rolling standard deviation."""

    @property
    def name(self) -> str:
        return "historical"

    def fit(
        self,
        returns: tuple[float, ...],
        config: VolatilityConfig,
    ) -> VolatilityForecast:
        if len(returns) < config.min_periods:
            raise InsufficientDataError(
                f"Need at least {config.min_periods} returns, got {len(returns)}"
            )
        lookback = min(config.lookback, len(returns))
        recent = returns[-lookback:]
        vol = _stdev(recent)
        annualized = _annualize(vol, config)
        var_est = vol ** 2
        return VolatilityForecast(
            model=self.name,
            horizon=1,
            forecast=annualized,
            variance=var_est * config.annual_factor,
            confidence=_confidence_interval(annualized, var_est, config),
            parameters={"lookback": float(lookback), "volatility": vol},
            converged=True,
        )

    def forecast(
        self,
        returns: tuple[float, ...],
        horizon: int,
        config: VolatilityConfig,
    ) -> VolatilityForecast:
        base = self.fit(returns, config)
        annual_var = base.variance
        horizon_var = annual_var * (horizon / config.annual_factor) if horizon > 0 else 0.0
        horizon_vol = math.sqrt(horizon_var) if horizon_var > 0 else 0.0
        ann = math.sqrt(config.annual_factor / max(horizon, 1))
        fc = horizon_vol * ann
        return VolatilityForecast(
            model=self.name,
            horizon=horizon,
            forecast=fc,
            variance=horizon_var * (config.annual_factor / max(horizon, 1)),
            confidence=_confidence_interval(fc, horizon_var, config),
            parameters=base.parameters,
            converged=True,
        )

    def forecast_path(
        self,
        returns: tuple[float, ...],
        horizon: int,
        config: VolatilityConfig,
    ) -> tuple[VolatilityForecast, ...]:
        return tuple(self.forecast(returns, h + 1, config) for h in range(horizon))

    def update(
        self,
        returns: tuple[float, ...],
        new_return: float,
        config: VolatilityConfig,
    ) -> VolatilityForecast:
        updated = returns + (new_return,)
        return self.fit(updated, config)

    def diagnostics(
        self,
        forecast: VolatilityForecast,
    ) -> ModelDiagnostics:
        return compute_diagnostics(forecast, ())
