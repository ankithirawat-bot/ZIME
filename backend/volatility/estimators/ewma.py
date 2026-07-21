"""EWMA volatility estimator.

Exponentially Weighted Moving Average with configurable lambda.
"""

from __future__ import annotations

import math

from backend.volatility.exceptions import InsufficientDataError
from backend.volatility.models import (
    ModelDiagnostics,
    VolatilityConfig,
    VolatilityForecast,
)

from ._base import (
    _annualize,
    _confidence_interval,
    _mean,
)


class EWMAAEstimator:
    """EWMA volatility estimator.

    Uses exponential weighting with configurable decay factor lambda.
    Default lambda of 0.94 is standard for daily returns (RiskMetrics).
    """

    @property
    def name(self) -> str:
        return "ewma"

    def _compute_var_series(
        self,
        returns: tuple[float, ...],
        lam: float,
    ) -> list[float]:
        """Compute EWMA variance series."""
        squared = [r ** 2 for r in returns]
        init_var = _mean(squared[:min(20, len(squared))])
        var_series: list[float] = []
        current_var = init_var
        for sq in squared:
            current_var = lam * current_var + (1 - lam) * sq
            var_series.append(current_var)
        return var_series

    def fit(
        self,
        returns: tuple[float, ...],
        config: VolatilityConfig,
    ) -> VolatilityForecast:
        if len(returns) < config.min_periods:
            raise InsufficientDataError(
                f"Need at least {config.min_periods} returns, got {len(returns)}"
            )
        lam = config.ewma_lambda
        var_series = self._compute_var_series(returns, lam)
        latest_var = var_series[-1] if var_series else 0.0
        vol = math.sqrt(latest_var) if latest_var > 0 else 0.0
        annualized = _annualize(vol, config)
        return VolatilityForecast(
            model=self.name,
            horizon=1,
            forecast=annualized,
            variance=latest_var * config.annual_factor,
            confidence=_confidence_interval(annualized, latest_var, config),
            conditional_vol=tuple(
                math.sqrt(v) * math.sqrt(config.annual_factor) for v in var_series
            ),
            parameters={"lambda": lam},
            converged=True,
        )

    def forecast(
        self,
        returns: tuple[float, ...],
        horizon: int,
        config: VolatilityConfig,
    ) -> VolatilityForecast:
        base = self.fit(returns, config)
        lam = config.ewma_lambda
        ann_var = base.variance
        forecast_var = ann_var
        for _ in range(horizon):
            forecast_var = lam * forecast_var + (1 - lam) * ann_var
        forecast_vol = math.sqrt(forecast_var) if forecast_var > 0 else 0.0
        return VolatilityForecast(
            model=self.name,
            horizon=horizon,
            forecast=forecast_vol,
            variance=forecast_var,
            confidence=_confidence_interval(forecast_vol, forecast_var, config),
            parameters=base.parameters,
            converged=True,
        )

    def forecast_path(
        self,
        returns: tuple[float, ...],
        horizon: int,
        config: VolatilityConfig,
    ) -> tuple[VolatilityForecast, ...]:
        base = self.fit(returns, config)
        lam = config.ewma_lambda
        ann_var = base.variance
        results: list[VolatilityForecast] = []
        fv = ann_var
        for h in range(1, horizon + 1):
            fv = lam * fv + (1 - lam) * ann_var
            v = math.sqrt(fv) if fv > 0 else 0.0
            results.append(VolatilityForecast(
                model=self.name, horizon=h, forecast=v, variance=fv,
                confidence=_confidence_interval(v, fv, config),
                parameters=base.parameters, converged=True,
            ))
        return tuple(results)

    def update(
        self,
        returns: tuple[float, ...],
        new_return: float,
        config: VolatilityConfig,
    ) -> VolatilityForecast:
        if len(returns) < config.min_periods:
            return self.fit(returns + (new_return,), config)
        lam = config.ewma_lambda
        var_series = self._compute_var_series(returns, lam)
        last_var = var_series[-1] if var_series else 0.0
        new_var = lam * last_var + (1 - lam) * new_return ** 2
        vol = math.sqrt(new_var) if new_var > 0 else 0.0
        annualized = _annualize(vol, config)
        return VolatilityForecast(
            model=self.name, horizon=1, forecast=annualized,
            variance=new_var * config.annual_factor,
            confidence=_confidence_interval(annualized, new_var, config),
            parameters={"lambda": lam}, converged=True,
        )

    def diagnostics(
        self,
        forecast: VolatilityForecast,
    ) -> ModelDiagnostics:
        lam = forecast.parameters.get("lambda", 0.94)
        persistence = lam
        half_life = -math.log(2) / math.log(lam) if 0 < lam < 1 else 0.0
        return ModelDiagnostics(
            persistence=persistence,
            half_life=half_life,
            is_stationary=lam < 1.0,
            convergence_status="converged",
            n_observations=len(forecast.conditional_vol) if forecast.conditional_vol else 0,
            n_parameters=1,
        )
