"""Volatility estimators.

Implementations of all volatility estimation models including historical,
EWMA, GARCH(1,1), EGARCH(1,1), and GJR-GARCH(1,1).
"""

from __future__ import annotations

import math

from backend.volatility.exceptions import InsufficientDataError
from backend.volatility.models import ConfidenceInterval, VolatilityConfig, VolatilityForecast


def _mean(values: tuple[float, ...]) -> float:
    """Compute mean of a tuple of values."""
    return sum(values) / len(values) if values else 0.0


def _variance(values: tuple[float, ...], ddof: int = 1) -> float:
    """Compute variance of a tuple of values."""
    if len(values) < 2:
        return 0.0
    m = _mean(values)
    return sum((v - m) ** 2 for v in values) / (len(values) - ddof)


def _stdev(values: tuple[float, ...], ddof: int = 1) -> float:
    """Compute standard deviation."""
    return math.sqrt(_variance(values, ddof))


def _annualize(vol: float, config: VolatilityConfig) -> float:
    """Annualize a volatility estimate."""
    return vol * math.sqrt(config.annual_factor)


def _confidence_interval(
    forecast: float,
    variance: float,
    config: VolatilityConfig,
) -> ConfidenceInterval:
    """Compute confidence interval for a volatility forecast."""
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
    """Compute log-likelihood under Gaussian assumption."""
    if len(returns) == 0 or len(variances) == 0:
        return 0.0
    n = min(len(returns), len(variances))
    ll = 0.0
    for i in range(n):
        if variances[i] > 0:
            ll += -0.5 * (math.log(2 * math.pi * variances[i]) + returns[i] ** 2 / variances[i])
    return ll


class HistoricalVolatilityEstimator:
    """Historical (rolling) volatility estimator."""

    @property
    def name(self) -> str:
        return "historical"

    def estimate(
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
            parameters={
                "lookback": float(lookback),
                "volatility": vol,
            },
            converged=True,
        )

    def forecast(
        self,
        returns: tuple[float, ...],
        horizon: int,
        config: VolatilityConfig,
    ) -> VolatilityForecast:
        base = self.estimate(returns, config)
        annual_var = base.variance
        horizon_var = annual_var * (horizon / config.annual_factor) if horizon > 0 else 0.0
        horizon_vol = math.sqrt(horizon_var) if horizon_var > 0 else 0.0
        return VolatilityForecast(
            model=self.name,
            horizon=horizon,
            forecast=horizon_vol * math.sqrt(config.annual_factor / max(horizon, 1)),
            variance=horizon_var * (config.annual_factor / max(horizon, 1)),
            confidence=_confidence_interval(
                horizon_vol * math.sqrt(config.annual_factor / max(horizon, 1)),
                horizon_var,
                config,
            ),
            parameters=base.parameters,
            converged=True,
        )


class EWMAAEstimator:
    """Exponentially Weighted Moving Average volatility estimator."""

    @property
    def name(self) -> str:
        return "ewma"

    def estimate(
        self,
        returns: tuple[float, ...],
        config: VolatilityConfig,
    ) -> VolatilityForecast:
        if len(returns) < config.min_periods:
            raise InsufficientDataError(
                f"Need at least {config.min_periods} returns, got {len(returns)}"
            )
        lam = config.ewma_lambda
        squared = [r ** 2 for r in returns]
        init_var = _mean(squared[:min(20, len(squared))])
        var_series: list[float] = []
        current_var = init_var
        for sq in squared:
            current_var = lam * current_var + (1 - lam) * sq
            var_series.append(current_var)
        latest_var = var_series[-1] if var_series else init_var
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
            parameters={
                "lambda": lam,
                "initial_variance": init_var,
            },
            converged=True,
        )

    def forecast(
        self,
        returns: tuple[float, ...],
        horizon: int,
        config: VolatilityConfig,
    ) -> VolatilityForecast:
        base = self.estimate(returns, config)
        lam = config.ewma_lambda
        ann_var = base.variance
        long_term_var = ann_var
        forecast_var = 0.0
        for h in range(1, horizon + 1):
            forecast_var = lam * long_term_var + (1 - lam) * ann_var
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


class GARCHEstimator:
    """GARCH(1,1) volatility estimator.

    Uses variance targeting and grid search for parameter estimation.
    """

    @property
    def name(self) -> str:
        return "garch"

    def _estimate_garch_params(
        self,
        returns: tuple[float, ...],
        config: VolatilityConfig,
    ) -> dict[str, float]:
        """Estimate GARCH(1,1) parameters using grid search."""
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
        best_params: dict[str, float] = {
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
                init_var = unconditional_var
                var_series: list[float] = []
                current_var = init_var
                for sq in squared:
                    current_var = omega + alpha * sq + beta * current_var
                    var_series.append(current_var)
                ll = _log_likelihood_gaussian(returns, tuple(var_series))
                if ll > best_ll:
                    best_ll = ll
                    best_params = {
                        "omega": omega,
                        "alpha": alpha,
                        "beta": beta,
                    }
        best_params["unconditional_var"] = unconditional_var
        best_params["log_likelihood"] = best_ll
        return best_params

    def _compute_conditional_variance(
        self,
        returns: tuple[float, ...],
        params: dict[str, float],
    ) -> tuple[float, ...]:
        """Compute conditional variance series."""
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

    def estimate(
        self,
        returns: tuple[float, ...],
        config: VolatilityConfig,
    ) -> VolatilityForecast:
        params = self._estimate_garch_params(returns, config)
        cond_var = self._compute_conditional_variance(returns, params)
        latest_var = cond_var[-1] if cond_var else 0.0
        vol = math.sqrt(latest_var) if latest_var > 0 else 0.0
        annualized = _annualize(vol, config)
        ll = params.pop("log_likelihood", 0.0)
        return VolatilityForecast(
            model=self.name,
            horizon=1,
            forecast=annualized,
            variance=latest_var * config.annual_factor,
            confidence=_confidence_interval(annualized, latest_var, config),
            conditional_vol=tuple(
                math.sqrt(v) * math.sqrt(config.annual_factor) for v in cond_var
            ),
            parameters=params,
            converged=True,
            log_likelihood=ll,
        )

    def forecast(
        self,
        returns: tuple[float, ...],
        horizon: int,
        config: VolatilityConfig,
    ) -> VolatilityForecast:
        base = self.estimate(returns, config)
        alpha = base.parameters.get("alpha", 0.1)
        beta = base.parameters.get("beta", 0.85)
        omega = base.parameters.get("omega", 0.0)
        latest_var = base.variance / config.annual_factor if config.annual_factor > 0 else 0.0
        forecast_var = latest_var
        for _ in range(horizon):
            forecast_var = omega + (alpha + beta) * forecast_var
        forecast_vol = math.sqrt(forecast_var) if forecast_var > 0 else 0.0
        annualized = forecast_vol * math.sqrt(config.annual_factor)
        return VolatilityForecast(
            model=self.name,
            horizon=horizon,
            forecast=annualized,
            variance=forecast_var * config.annual_factor,
            confidence=_confidence_interval(annualized, forecast_var, config),
            parameters=base.parameters,
            converged=True,
            log_likelihood=base.log_likelihood,
        )


class EGARCHEstimator:
    """EGARCH(1,1) volatility estimator with asymmetric effects."""

    @property
    def name(self) -> str:
        return "egarch"

    def _estimate_egarch_params(
        self,
        returns: tuple[float, ...],
        config: VolatilityConfig,
    ) -> dict[str, float]:
        """Estimate EGARCH(1,1) parameters using grid search."""
        n = len(returns)
        if n < config.min_periods:
            raise InsufficientDataError(
                f"Need at least {config.min_periods} returns, got {n}"
            )
        squared = [r ** 2 for r in returns]
        std_returns = [
            (r - _mean(tuple(returns))) / max(_stdev(tuple(returns)), 1e-8)
            for r in returns
        ]
        unconditional_var = _mean(squared)
        if unconditional_var <= 0:
            unconditional_var = 1e-8

        best_ll = -float("inf")
        best_params: dict[str, float] = {
            "omega": math.log(unconditional_var) * 0.1,
            "alpha": 0.15,
            "beta": 0.85,
            "gamma": -0.05,
        }

        alphas = [0.05, 0.1, 0.15, 0.2]
        betas = [0.8, 0.85, 0.9, 0.93]
        gammas = [-0.1, -0.05, 0.0, 0.05, 0.1]

        for alpha in alphas:
            for beta in betas:
                for gamma in gammas:
                    if beta >= 1.0:
                        continue
                    omega = math.log(unconditional_var) * (1.0 - beta) - alpha * math.sqrt(2.0 / math.pi)
                    init_log_var = math.log(unconditional_var)
                    log_var_series: list[float] = []
                    current_log_var = init_log_var
                    for i, sq in enumerate(squared):
                        z = std_returns[i] if i < len(std_returns) else 0.0
                        abs_z = abs(z)
                        current_log_var = (
                            omega
                            + beta * current_log_var
                            + alpha * (abs_z - math.sqrt(2.0 / math.pi))
                            + gamma * z
                        )
                        log_var_series.append(current_log_var)
                    var_series = [math.exp(lv) for lv in log_var_series]
                    ll = _log_likelihood_gaussian(returns, tuple(var_series))
                    if ll > best_ll:
                        best_ll = ll
                        best_params = {
                            "omega": omega,
                            "alpha": alpha,
                            "beta": beta,
                            "gamma": gamma,
                        }
        best_params["unconditional_var"] = unconditional_var
        best_params["log_likelihood"] = best_ll
        return best_params

    def _compute_conditional_variance(
        self,
        returns: tuple[float, ...],
        params: dict[str, float],
    ) -> tuple[float, ...]:
        """Compute EGARCH conditional variance series."""
        omega = params["omega"]
        alpha = params["alpha"]
        beta = params["beta"]
        gamma = params["gamma"]
        squared = [r ** 2 for r in returns]
        std_returns = [
            (r - _mean(tuple(returns))) / max(_stdev(tuple(returns)), 1e-8)
            for r in returns
        ]
        init_log_var = math.log(_mean(squared) + 1e-12)
        log_var_series: list[float] = []
        current_log_var = init_log_var
        for i, sq in enumerate(squared):
            z = std_returns[i] if i < len(std_returns) else 0.0
            abs_z = abs(z)
            current_log_var = (
                omega
                + beta * current_log_var
                + alpha * (abs_z - math.sqrt(2.0 / math.pi))
                + gamma * z
            )
            log_var_series.append(current_log_var)
        return tuple(math.exp(lv) for lv in log_var_series)

    def estimate(
        self,
        returns: tuple[float, ...],
        config: VolatilityConfig,
    ) -> VolatilityForecast:
        params = self._estimate_egarch_params(returns, config)
        cond_var = self._compute_conditional_variance(returns, params)
        latest_var = cond_var[-1] if cond_var else 0.0
        vol = math.sqrt(latest_var) if latest_var > 0 else 0.0
        annualized = _annualize(vol, config)
        ll = params.pop("log_likelihood", 0.0)
        return VolatilityForecast(
            model=self.name,
            horizon=1,
            forecast=annualized,
            variance=latest_var * config.annual_factor,
            confidence=_confidence_interval(annualized, latest_var, config),
            conditional_vol=tuple(
                math.sqrt(v) * math.sqrt(config.annual_factor) for v in cond_var
            ),
            parameters=params,
            converged=True,
            log_likelihood=ll,
        )

    def forecast(
        self,
        returns: tuple[float, ...],
        horizon: int,
        config: VolatilityConfig,
    ) -> VolatilityForecast:
        base = self.estimate(returns, config)
        alpha = base.parameters.get("alpha", 0.15)
        beta = base.parameters.get("beta", 0.85)
        gamma = base.parameters.get("gamma", -0.05)
        omega = base.parameters.get("omega", 0.0)
        latest_var = base.variance / config.annual_factor if config.annual_factor > 0 else 0.0
        latest_log_var = math.log(latest_var + 1e-12)
        expected_abs_z = math.sqrt(2.0 / math.pi)
        forecast_log_var = latest_log_var
        for _ in range(horizon):
            forecast_log_var = (
                omega
                + beta * forecast_log_var
                + alpha * (expected_abs_z - expected_abs_z)
                + gamma * 0.0
            )
        forecast_var = math.exp(forecast_log_var)
        forecast_vol = math.sqrt(forecast_var) if forecast_var > 0 else 0.0
        annualized = forecast_vol * math.sqrt(config.annual_factor)
        return VolatilityForecast(
            model=self.name,
            horizon=horizon,
            forecast=annualized,
            variance=forecast_var * config.annual_factor,
            confidence=_confidence_interval(annualized, forecast_var, config),
            parameters=base.parameters,
            converged=True,
            log_likelihood=base.log_likelihood,
        )


class GJRGARCHEstimator:
    """GJR-GARCH(1,1) volatility estimator with leverage effects."""

    @property
    def name(self) -> str:
        return "gjrgarch"

    def _estimate_gjrgarch_params(
        self,
        returns: tuple[float, ...],
        config: VolatilityConfig,
    ) -> dict[str, float]:
        """Estimate GJR-GARCH(1,1) parameters using grid search."""
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
        best_params: dict[str, float] = {
            "omega": unconditional_var * 0.05,
            "alpha": 0.05,
            "beta": 0.85,
            "gamma": 0.05,
        }

        alphas = [0.02, 0.05, 0.08, 0.1]
        betas = [0.8, 0.85, 0.9, 0.92]
        gammas = [0.02, 0.05, 0.08, 0.1, 0.12]

        for alpha in alphas:
            for beta in betas:
                for gamma in gammas:
                    if alpha + beta + 0.5 * gamma >= 1.0:
                        continue
                    omega = unconditional_var * (1.0 - alpha - beta - 0.5 * gamma)
                    if omega <= 0:
                        continue
                    init_var = unconditional_var
                    var_series: list[float] = []
                    current_var = init_var
                    for sq in squared:
                        # Use previous return sign for leverage
                        pass
                    var_series = []
                    current_var = init_var
                    for i, sq in enumerate(squared):
                        z = 1.0 if (i > 0 and returns[i - 1] < 0) else 0.0
                        current_var = omega + (alpha + gamma * z) * sq + beta * current_var
                        var_series.append(current_var)
                    ll = _log_likelihood_gaussian(returns, tuple(var_series))
                    if ll > best_ll:
                        best_ll = ll
                        best_params = {
                            "omega": omega,
                            "alpha": alpha,
                            "beta": beta,
                            "gamma": gamma,
                        }
        best_params["unconditional_var"] = unconditional_var
        best_params["log_likelihood"] = best_ll
        return best_params

    def _compute_conditional_variance(
        self,
        returns: tuple[float, ...],
        params: dict[str, float],
    ) -> tuple[float, ...]:
        """Compute GJR-GARCH conditional variance series."""
        omega = params["omega"]
        alpha = params["alpha"]
        beta = params["beta"]
        gamma = params["gamma"]
        squared = [r ** 2 for r in returns]
        init_var = _mean(squared)
        var_series: list[float] = []
        current_var = init_var
        for i, sq in enumerate(squared):
            z = 1.0 if (i > 0 and returns[i - 1] < 0) else 0.0
            current_var = omega + (alpha + gamma * z) * sq + beta * current_var
            var_series.append(current_var)
        return tuple(var_series)

    def estimate(
        self,
        returns: tuple[float, ...],
        config: VolatilityConfig,
    ) -> VolatilityForecast:
        params = self._estimate_gjrgarch_params(returns, config)
        cond_var = self._compute_conditional_variance(returns, params)
        latest_var = cond_var[-1] if cond_var else 0.0
        vol = math.sqrt(latest_var) if latest_var > 0 else 0.0
        annualized = _annualize(vol, config)
        ll = params.pop("log_likelihood", 0.0)
        return VolatilityForecast(
            model=self.name,
            horizon=1,
            forecast=annualized,
            variance=latest_var * config.annual_factor,
            confidence=_confidence_interval(annualized, latest_var, config),
            conditional_vol=tuple(
                math.sqrt(v) * math.sqrt(config.annual_factor) for v in cond_var
            ),
            parameters=params,
            converged=True,
            log_likelihood=ll,
        )

    def forecast(
        self,
        returns: tuple[float, ...],
        horizon: int,
        config: VolatilityConfig,
    ) -> VolatilityForecast:
        base = self.estimate(returns, config)
        alpha = base.parameters.get("alpha", 0.05)
        beta = base.parameters.get("beta", 0.85)
        gamma = base.parameters.get("gamma", 0.05)
        omega = base.parameters.get("omega", 0.0)
        latest_var = base.variance / config.annual_factor if config.annual_factor > 0 else 0.0
        forecast_var = latest_var
        persistence = alpha + beta + 0.5 * gamma
        for _ in range(horizon):
            forecast_var = omega + persistence * forecast_var
        forecast_vol = math.sqrt(forecast_var) if forecast_var > 0 else 0.0
        annualized = forecast_vol * math.sqrt(config.annual_factor)
        return VolatilityForecast(
            model=self.name,
            horizon=horizon,
            forecast=annualized,
            variance=forecast_var * config.annual_factor,
            confidence=_confidence_interval(annualized, forecast_var, config),
            parameters=base.parameters,
            converged=True,
            log_likelihood=base.log_likelihood,
        )


def _compute_aic(log_likelihood: float, n_params: int, n_obs: int) -> float:
    """Compute Akaike Information Criterion."""
    if n_obs == 0:
        return 0.0
    return 2 * n_params - 2 * log_likelihood


def _compute_bic(log_likelihood: float, n_params: int, n_obs: int) -> float:
    """Compute Bayesian Information Criterion."""
    if n_obs == 0:
        return 0.0
    return math.log(n_obs) * n_params - 2 * log_likelihood
