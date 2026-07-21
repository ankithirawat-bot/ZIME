"""Volatility forecast engine.

Multi-horizon forecasting, rolling forecasts, term structures,
and batch forecasting using registered estimators.
"""

from __future__ import annotations

import time
from typing import Any

from backend.volatility.estimators import (
    EGARCHEstimator,
    EWMAAEstimator,
    GARCHEstimator,
    GJRGARCHEstimator,
    HistoricalVolatilityEstimator,
)
from backend.volatility.exceptions import InsufficientDataError
from backend.volatility.models import (
    ForecastRequest,
    ForecastResult,
    VolatilityConfig,
    VolatilityForecast,
)

DEFAULT_HORIZONS: tuple[int, ...] = (1, 5, 10, 20, 60, 120, 252)


def _default_estimators() -> dict[str, Any]:
    """Create default volatility estimators."""
    return {
        "historical": HistoricalVolatilityEstimator(),
        "ewma": EWMAAEstimator(),
        "garch": GARCHEstimator(),
        "egarch": EGARCHEstimator(),
        "gjrgarch": GJRGARCHEstimator(),
    }


class ForecastEngine:
    """Multi-horizon volatility forecast engine.

    Generates single, multi-horizon, rolling, term structure,
    and batch forecasts using registered estimators.
    """

    def __init__(
        self,
        estimators: dict[str, Any] | None = None,
    ) -> None:
        """Initialize the forecast engine.

        Args:
            estimators: Dictionary of estimators (name -> instance).
        """
        self._estimators = estimators or _default_estimators()

    @property
    def estimators(self) -> dict[str, Any]:
        """Registered estimators."""
        return dict(self._estimators)

    def register_estimator(self, name: str, estimator: Any) -> None:
        """Register a custom estimator.

        Args:
            name:       Estimator name.
            estimator:  Estimator instance.
        """
        self._estimators[name] = estimator

    def forecast(
        self,
        returns: tuple[float, ...],
        model: str | None = None,
        horizon: int | None = None,
        config: VolatilityConfig | None = None,
    ) -> VolatilityForecast:
        """Forecast volatility for a single horizon.

        Args:
            returns: Historical returns.
            model:   Model name (default from config).
            horizon: Forecast horizon (default from config).
            config:  Configuration (defaults created).

        Returns:
            VolatilityForecast.
        """
        cfg = config or VolatilityConfig()
        model_name = model or cfg.model
        h = horizon if horizon is not None else cfg.horizon
        if model_name not in self._estimators:
            raise InsufficientDataError(f"Model '{model_name}' not found")
        return self._estimators[model_name].forecast(returns, h, cfg)

    def forecast_multiple(
        self,
        returns: tuple[float, ...],
        model: str | None = None,
        horizons: tuple[int, ...] | None = None,
        config: VolatilityConfig | None = None,
    ) -> ForecastResult:
        """Forecast at multiple horizons.

        Args:
            returns:  Historical returns.
            model:    Model name.
            horizons: Horizons (default: 1,5,10,20,60,120,252).
            config:   Configuration.

        Returns:
            ForecastResult with forecasts by horizon.
        """
        cfg = config or VolatilityConfig()
        model_name = model or cfg.model
        hrs = horizons or DEFAULT_HORIZONS
        start = time.perf_counter()

        estimator = self._estimators.get(model_name)
        if estimator is None:
            raise InsufficientDataError(f"Model '{model_name}' not found")

        forecasts: dict[int, VolatilityForecast] = {}
        for h in hrs:
            forecasts[h] = estimator.forecast(returns, h, cfg)

        base = forecasts.get(1, next(iter(forecasts.values())) if forecasts else VolatilityForecast())
        base_fit = estimator.fit(returns, cfg)
        diag = estimator.diagnostics(base_fit)
        elapsed = time.perf_counter() - start

        return ForecastResult(
            model=model_name,
            forecasts=forecasts,
            current_vol=base.forecast,
            long_term_vol=forecasts.get(max(hrs), base).forecast if forecasts else 0.0,
            diagnostics=diag,
            elapsed=elapsed,
        )

    def rolling_forecast(
        self,
        returns: tuple[float, ...],
        window: int = 252,
        model: str | None = None,
        horizon: int = 20,
        config: VolatilityConfig | None = None,
    ) -> tuple[VolatilityForecast, ...]:
        """Generate rolling volatility forecasts.

        Args:
            returns:  Historical returns.
            window:   Rolling window size.
            model:    Model name.
            horizon:  Forecast horizon.
            config:   Configuration.

        Returns:
            Tuple of forecasts for each window.
        """
        cfg = config or VolatilityConfig()
        model_name = model or cfg.model
        if model_name not in self._estimators:
            raise InsufficientDataError(f"Model '{model_name}' not found")
        estimator = self._estimators[model_name]

        if len(returns) < window + 1:
            raise InsufficientDataError(
                f"Need at least {window + 1} returns, got {len(returns)}"
            )

        forecasts: list[VolatilityForecast] = []
        for i in range(window, len(returns)):
            window_ret = returns[i - window:i]
            try:
                fc = estimator.forecast(window_ret, horizon, cfg)
                forecasts.append(fc)
            except Exception:
                forecasts.append(
                    VolatilityForecast(model=model_name, horizon=horizon, converged=False)
                )
        return tuple(forecasts)

    def forecast_term_structure(
        self,
        returns: tuple[float, ...],
        model: str | None = None,
        config: VolatilityConfig | None = None,
    ) -> ForecastResult:
        """Generate full volatility term structure.

        Args:
            returns: Historical returns.
            model:   Model name.
            config:  Configuration.

        Returns:
            ForecastResult with term structure.
        """
        return self.forecast_multiple(returns, model, DEFAULT_HORIZONS, config)

    def batch_forecast(
        self,
        requests: tuple[ForecastRequest, ...],
    ) -> tuple[ForecastResult, ...]:
        """Run multiple forecast requests in batch.

        Args:
            requests: Forecast requests.

        Returns:
            Tuple of forecast results.
        """
        results: list[ForecastResult] = []
        for req in requests:
            cfg = req.config or VolatilityConfig()
            model_name = req.model or cfg.model
            try:
                result = self.forecast_multiple(
                    req.returns, model_name, (req.horizon,), cfg
                )
                if req.symbol:
                    result = ForecastResult(
                        symbol=req.symbol, model=result.model,
                        forecasts=result.forecasts,
                        current_vol=result.current_vol,
                        long_term_vol=result.long_term_vol,
                        diagnostics=result.diagnostics,
                        elapsed=result.elapsed,
                    )
                results.append(result)
            except Exception:
                results.append(
                    ForecastResult(
                        symbol=req.symbol, model=model_name,
                        elapsed=0.0,
                    )
                )
        return tuple(results)

    def compare_models(
        self,
        returns: tuple[float, ...],
        horizon: int = 20,
        config: VolatilityConfig | None = None,
    ) -> dict[str, VolatilityForecast]:
        """Run all models and return forecasts for comparison.

        Args:
            returns:  Historical returns.
            horizon:  Forecast horizon.
            config:   Configuration.

        Returns:
            Dict of model name -> forecast.
        """
        cfg = config or VolatilityConfig()
        results: dict[str, VolatilityForecast] = {}
        for name, estimator in self._estimators.items():
            try:
                results[name] = estimator.forecast(returns, horizon, cfg)
            except Exception:
                results[name] = VolatilityForecast(
                    model=name, horizon=horizon, converged=False,
                )
        return results
