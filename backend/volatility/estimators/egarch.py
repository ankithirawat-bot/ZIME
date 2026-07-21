"""EGARCH(1,1) volatility estimator.

Exponential GARCH with asymmetric volatility modelling.
"""

from __future__ import annotations

import math

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
    _stdev,
)


class EGARCHEstimator:
    """EGARCH(1,1) volatility estimator.

    Models log-variance with asymmetric response to positive/negative shocks.
    """

    @property
    def name(self) -> str:
        return "egarch"

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
        m = _mean(returns)
        s = max(_stdev(returns), 1e-8)
        std_ret = [(r - m) / s for r in returns]
        unconditional_var = _mean(squared)
        if unconditional_var <= 0:
            unconditional_var = 1e-8

        best_ll = -float("inf")
        best: dict[str, float] = {
            "omega": math.log(unconditional_var) * 0.1,
            "alpha": 0.15,
            "beta": 0.85,
            "gamma": -0.05,
        }

        alphas = [0.05, 0.1, 0.15, 0.2]
        betas = [0.8, 0.85, 0.9, 0.93]
        gammas = [-0.1, -0.05, 0.0, 0.05, 0.1]
        sqrt_2pi = math.sqrt(2.0 / math.pi)

        for alpha in alphas:
            for beta in betas:
                if beta >= 1.0:
                    continue
                for gamma in gammas:
                    omega = math.log(unconditional_var) * (1.0 - beta) - alpha * sqrt_2pi
                    log_var = math.log(unconditional_var)
                    log_vars: list[float] = []
                    for i in range(len(returns)):
                        z = std_ret[i]
                        log_var = (
                            omega + beta * log_var
                            + alpha * (abs(z) - sqrt_2pi)
                            + gamma * z
                        )
                        log_vars.append(log_var)
                    var_series = [math.exp(lv) for lv in log_vars]
                    ll = _log_likelihood_gaussian(returns, tuple(var_series))
                    if ll > best_ll:
                        best_ll = ll
                        best = {"omega": omega, "alpha": alpha, "beta": beta, "gamma": gamma}
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
        gamma = params["gamma"]
        m = _mean(returns)
        s = max(_stdev(returns), 1e-8)
        std_ret = [(r - m) / s for r in returns]
        sqrt_2pi = math.sqrt(2.0 / math.pi)
        init_var = _mean([r ** 2 for r in returns])
        log_var = math.log(max(init_var, 1e-12))
        log_vars: list[float] = []
        for i in range(len(returns)):
            z = std_ret[i]
            log_var = (
                omega + beta * log_var
                + alpha * (abs(z) - sqrt_2pi)
                + gamma * z
            )
            log_vars.append(log_var)
        return tuple(math.exp(lv) for lv in log_vars)

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
        alpha = base.parameters.get("alpha", 0.15)
        beta = base.parameters.get("beta", 0.85)
        gamma_p = base.parameters.get("gamma", -0.05)
        omega = base.parameters.get("omega", 0.0)
        latest_var = base.variance / config.annual_factor if config.annual_factor > 0 else 0.0
        log_var = math.log(max(latest_var, 1e-12))
        sqrt_2pi = math.sqrt(2.0 / math.pi)
        expected_asym = alpha * (sqrt_2pi - sqrt_2pi) + gamma_p * 0.0
        for _ in range(horizon):
            log_var = omega + beta * log_var + expected_asym
        fv = math.exp(log_var)
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
        omega = base.parameters.get("omega", 0.0)
        beta = base.parameters.get("beta", 0.85)
        latest_var = base.variance / config.annual_factor if config.annual_factor > 0 else 0.0
        log_var = math.log(max(latest_var, 1e-12))
        results: list[VolatilityForecast] = []
        for h in range(1, horizon + 1):
            log_var = omega + beta * log_var
            fv = math.exp(log_var)
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
        beta = forecast.parameters.get("beta", 0.0)
        persistence = beta
        half_life = -math.log(2) / math.log(beta) if 0 < beta < 1 else 0.0
        return ModelDiagnostics(
            persistence=persistence,
            half_life=half_life,
            is_stationary=beta < 1.0,
            convergence_status="converged" if forecast.converged else "failed",
            n_observations=len(forecast.conditional_vol) if forecast.conditional_vol else 0,
            n_parameters=4,
        )
