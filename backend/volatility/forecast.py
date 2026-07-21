"""Volatility forecast engine.

Multi-horizon forecasting, rolling forecasts, and term structure generation.
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
    ForecastResult,
    VolatilityConfig,
    VolatilityForecast,
)

DEFAULT_HORIZONS: tuple[int, ...] = (1, 5, 10, 20, 60, 252)


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

    Generates forecasts at multiple horizons, rolling forecasts,
    and term structures using registered estimators.
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
            horizon: Forecast horizon in days (default from config).
            config:  Volatility configuration (defaults created).

        Returns:
            VolatilityForecast with forecast.
        """
        cfg = config or VolatilityConfig()
        model_name = model or cfg.model
        h = horizon if horizon is not None else cfg.horizon

        if model_name not in self._estimators:
            raise InsufficientDataError(
                f"Model '{model_name}' not found"
            )

        estimator = self._estimators[model_name]
        return estimator.forecast(returns, h, cfg)

    def forecast_multiple(
        self,
        returns: tuple[float, ...],
        model: str | None = None,
        horizons: tuple[int, ...] | None = None,
        config: VolatilityConfig | None = None,
    ) -> ForecastResult:
        """Forecast volatility at multiple horizons.

        Args:
            returns:  Historical returns.
            model:    Model name (default from config).
            horizons: Forecast horizons (default: 1, 5, 10, 20, 60, 252).
            config:   Volatility configuration (defaults created).

        Returns:
            ForecastResult with forecasts by horizon.
        """
        cfg = config or VolatilityConfig()
        model_name = model or cfg.model
        hrs = horizons or DEFAULT_HORIZONS
        start = time.perf_counter()

        forecasts: dict[int, VolatilityForecast] = {}
        for h in hrs:
            forecast = self.forecast(returns, model_name, h, cfg)
            forecasts[h] = forecast

        base = forecasts.get(1, list(forecasts.values())[0] if forecasts else VolatilityForecast())
        elapsed = time.perf_counter() - start

        return ForecastResult(
            model=model_name,
            forecasts=forecasts,
            current_vol=base.forecast,
            long_term_vol=forecasts.get(max(hrs), base).forecast if forecasts else 0.0,
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
            model:    Model name (default from config).
            horizon:  Forecast horizon in days.
            config:   Volatility configuration (defaults created).

        Returns:
            Tuple of VolatilityForecast for each window.
        """
        cfg = config or VolatilityConfig()
        model_name = model or cfg.model
        forecasts: list[VolatilityForecast] = []

        if len(returns) < window + 1:
            raise InsufficientDataError(
                f"Need at least {window + 1} returns for rolling forecast, got {len(returns)}"
            )

        for i in range(window, len(returns)):
            window_returns = returns[i - window:i]
            try:
                fc = self.forecast(window_returns, model_name, horizon, cfg)
                forecasts.append(fc)
            except (InsufficientDataError, Exception):
                forecasts.append(
                    VolatilityForecast(
                        model=model_name,
                        horizon=horizon,
                        converged=False,
                    )
                )

        return tuple(forecasts)

    def forecast_term_structure(
        self,
        returns: tuple[float, ...],
        model: str | None = None,
        config: VolatilityConfig | None = None,
    ) -> ForecastResult:
        """Generate the full volatility term structure.

        Computes forecasted volatility at 1, 5, 10, 20, 60, and 252 days.

        Args:
            returns: Historical returns.
            model:   Model name (default from config).
            config:  Volatility configuration (defaults created).

        Returns:
            ForecastResult with term structure forecasts.
        """
        return self.forecast_multiple(returns, model, DEFAULT_HORIZONS, config)

    def compare_models(
        self,
        returns: tuple[float, ...],
        horizon: int = 20,
        config: VolatilityConfig | None = None,
    ) -> dict[str, VolatilityForecast]:
        """Run all models and return their forecasts.

        Args:
            returns:  Historical returns.
            horizon:  Forecast horizon in days.
            config:   Volatility configuration (defaults created).

        Returns:
            Dictionary of model name -> VolatilityForecast.
        """
        cfg = config or VolatilityConfig()
        results: dict[str, VolatilityForecast] = {}
        for name, estimator in self._estimators.items():
            try:
                results[name] = estimator.forecast(returns, horizon, cfg)
            except Exception:
                results[name] = VolatilityForecast(
                    model=name,
                    horizon=horizon,
                    converged=False,
                )
        return results
