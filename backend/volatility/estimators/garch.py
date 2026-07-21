"""GARCH(1,1) volatility estimator.

Standard GARCH model with grid-search parameter estimation
and variance targeting.
"""

from __future__ import annotations

import math

from backend.volatility.diagnostics import compute_diagnostics
from backend.volatility.exceptions import (
    InsufficientDataError,
)
from backend.volatility.models import (
    ModelDiagnostics,
    VolatilityConfig,
    VolatilityForecast,
)

from ._base import (
    _annualize,
    _confidence_interval,
    _log_likelihood_gaussian,
    _mean,
)


class GARCHEstimator:
    """GARCH(1,1) volatility estimator.

    Uses grid search over alpha/beta with variance targeting
    to estimate parameters via maximum likelihood.
    """

    @property
    def name(self) -> str:
        return "garch"

    def _estimate_params(
        self,
        returns: tuple[float, ...],
        config: VolatilityConfig,
    ) -> dict[str, float]:
        n = len(returns)
        if n < config.min_periods:
            raise InsufficientDataError(
                f"Need at least {config.min_periods} returns, got {n}"
            )
        squared = [r ** 2 for r in returns]
        unconditional_var = _mean(squared)
        if unconditional_var <= 0:
            unconditional_var = 1e-8

        best_ll = -float("inf")
        best: dict[str, float] = {
            "omega": unconditional_var * 0.05,
            "alpha": 0.1,
            "beta": 0.85,
        }

        alphas = [0.05, 0.08, 0.1, 0.12, 0.15, 0.18, 0.2]
        betas = [0.75, 0.8, 0.85, 0.88, 0.9, 0.92, 0.94]

        for alpha in alphas:
            for beta in betas:
                if alpha + beta >= 1.0:
                    continue
                omega = unconditional_var * (1.0 - alpha - beta)
                if omega <= 0:
                    continue
                current_var = unconditional_var
                var_series: list[float] = []
                for sq in squared:
                    current_var = omega + alpha * sq + beta * current_var
                    var_series.append(current_var)
                ll = _log_likelihood_gaussian(returns, tuple(var_series))
                if ll > best_ll:
                    best_ll = ll
                    best = {"omega": omega, "alpha": alpha, "beta": beta}
        best["unconditional_var"] = unconditional_var
        best["log_likelihood"] = best_ll
        return best

    def _compute_cond_var(
        self,
        returns: tuple[float, ...],
        params: dict[str, float],
    ) -> tuple[float, ...]:
        omega = params["omega"]
        alpha = params["alpha"]
        beta = params["beta"]
        squared = [r ** 2 for r in returns]
        init_var = _mean(squared)
        var_series: list[float] = []
        current_var = init_var
        for sq in squared:
            current_var = omega + alpha * sq + beta * current_var
            var_series.append(current_var)
        return tuple(var_series)

    def fit(
        self,
        returns: tuple[float, ...],
        config: VolatilityConfig,
    ) -> VolatilityForecast:
        params = self._estimate_params(returns, config)
        cond_var = self._compute_cond_var(returns, params)
        latest_var = cond_var[-1] if cond_var else 0.0
        vol = math.sqrt(latest_var) if latest_var > 0 else 0.0
        annualized = _annualize(vol, config)
        ll = params.pop("log_likelihood", 0.0)
        return VolatilityForecast(
            model=self.name, horizon=1, forecast=annualized,
            variance=latest_var * config.annual_factor,
            confidence=_confidence_interval(annualized, latest_var, config),
            conditional_vol=tuple(
                math.sqrt(v) * math.sqrt(config.annual_factor) for v in cond_var
            ),
            parameters=params, converged=True, log_likelihood=ll,
        )

    def forecast(
        self,
        returns: tuple[float, ...],
        horizon: int,
        config: VolatilityConfig,
    ) -> VolatilityForecast:
        base = self.fit(returns, config)
        alpha = base.parameters.get("alpha", 0.1)
        beta = base.parameters.get("beta", 0.85)
        omega = base.parameters.get("omega", 0.0)
        latest_var = base.variance / config.annual_factor if config.annual_factor > 0 else 0.0
        fv = latest_var
        for _ in range(horizon):
            fv = omega + (alpha + beta) * fv
        fvol = math.sqrt(fv) if fv > 0 else 0.0
        annualized = fvol * math.sqrt(config.annual_factor)
        return VolatilityForecast(
            model=self.name, horizon=horizon, forecast=annualized,
            variance=fv * config.annual_factor,
            confidence=_confidence_interval(annualized, fv, config),
            parameters=base.parameters, converged=True,
            log_likelihood=base.log_likelihood,
        )

    def forecast_path(
        self,
        returns: tuple[float, ...],
        horizon: int,
        config: VolatilityConfig,
    ) -> tuple[VolatilityForecast, ...]:
        base = self.fit(returns, config)
        alpha = base.parameters.get("alpha", 0.1)
        beta = base.parameters.get("beta", 0.85)
        omega = base.parameters.get("omega", 0.0)
        fv = base.variance / config.annual_factor if config.annual_factor > 0 else 0.0
        results: list[VolatilityForecast] = []
        for h in range(1, horizon + 1):
            fv = omega + (alpha + beta) * fv
            fvol = math.sqrt(fv) if fv > 0 else 0.0
            ann = fvol * math.sqrt(config.annual_factor)
            results.append(VolatilityForecast(
                model=self.name, horizon=h, forecast=ann,
                variance=fv * config.annual_factor,
                confidence=_confidence_interval(ann, fv, config),
                parameters=base.parameters, converged=True,
            ))
        return tuple(results)

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
