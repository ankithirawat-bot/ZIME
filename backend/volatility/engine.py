"""Volatility forecast engine.

Core volatility forecasting engine for estimating future volatility
using multiple statistical models.
"""

from __future__ import annotations

from typing import Any

from backend.volatility.comparison import ModelComparer
from backend.volatility.forecast import ForecastEngine
from backend.volatility.models import (
    ForecastMetrics,
    ForecastResult,
    ForecastStatistics,
    ModelComparison,
    VolatilityConfig,
    VolatilityForecast,
)


class VolatilityEngine:
    """Core volatility forecasting engine.

    Provides unified access to multiple volatility models for forecasting,
    comparison, and analysis. Optionally integrates with portfolio, risk,
    sizing, strategy, and backtesting engines.
    """

    def __init__(
        self,
        config: VolatilityConfig | None = None,
        forecast_engine: ForecastEngine | None = None,
        comparer: ModelComparer | None = None,
        portfolio_engine: Any | None = None,
        risk_engine: Any | None = None,
        sizing_engine: Any | None = None,
        strategy_engine: Any | None = None,
        backtesting_engine: Any | None = None,
    ) -> None:
        """Initialize the engine.

        Args:
            config:             Volatility configuration (defaults created).
            forecast_engine:    Forecast engine (defaults created).
            comparer:           Model comparer (defaults created).
            portfolio_engine:   Optional portfolio engine.
            risk_engine:        Optional risk engine.
            sizing_engine:      Optional sizing engine.
            strategy_engine:    Optional strategy engine.
            backtesting_engine: Optional backtesting engine.
        """
        self._config = config or VolatilityConfig()
        self._forecast_engine = forecast_engine or ForecastEngine()
        self._comparer = comparer or ModelComparer()
        self._portfolio_engine = portfolio_engine
        self._risk_engine = risk_engine
        self._sizing_engine = sizing_engine
        self._strategy_engine = strategy_engine
        self._backtesting_engine = backtesting_engine
        self._total_forecasts = 0

    @property
    def config(self) -> VolatilityConfig:
        """Current configuration."""
        return self._config

    @property
    def forecast_engine(self) -> ForecastEngine:
        """Access the underlying forecast engine."""
        return self._forecast_engine

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
            config:  Volatility configuration (default from engine).

        Returns:
            VolatilityForecast with forecast.
        """
        self._total_forecasts += 1
        cfg = config or self._config
        return self._forecast_engine.forecast(returns, model, horizon, cfg)

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
            config:   Volatility configuration (default from engine).

        Returns:
            ForecastResult with forecasts by horizon.
        """
        self._total_forecasts += 1
        cfg = config or self._config
        return self._forecast_engine.forecast_multiple(returns, model, horizons, cfg)

    def compare_models(
        self,
        returns: tuple[float, ...],
        actual_returns: tuple[float, ...],
        horizon: int = 20,
        config: VolatilityConfig | None = None,
    ) -> tuple[ModelComparison, ...]:
        """Compare all models and return ranked results.

        Args:
            returns:         Historical returns for estimation.
            actual_returns:  Actual subsequent returns for evaluation.
            horizon:         Forecast horizon in days.
            config:          Volatility configuration (default from engine).

        Returns:
            Tuple of ModelComparison sorted by rank.
        """
        cfg = config or self._config
        forecasts = self._forecast_engine.compare_models(returns, horizon, cfg)
        return self._comparer.compare(forecasts, actual_returns, cfg)

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
            config:   Volatility configuration (default from engine).

        Returns:
            Tuple of VolatilityForecast for each window.
        """
        self._total_forecasts += 1
        cfg = config or self._config
        return self._forecast_engine.rolling_forecast(
            returns, window, model, horizon, cfg
        )

    def forecast_term_structure(
        self,
        returns: tuple[float, ...],
        model: str | None = None,
        config: VolatilityConfig | None = None,
    ) -> ForecastResult:
        """Generate the full volatility term structure.

        Args:
            returns: Historical returns.
            model:   Model name (default from config).
            config:  Volatility configuration (default from engine).

        Returns:
            ForecastResult with term structure forecasts.
        """
        self._total_forecasts += 1
        cfg = config or self._config
        return self._forecast_engine.forecast_term_structure(returns, model, cfg)

    def compute_metrics(
        self,
        forecast: VolatilityForecast,
        actual_returns: tuple[float, ...],
        config: VolatilityConfig | None = None,
    ) -> ForecastMetrics:
        """Compute forecast quality metrics for a single forecast.

        Args:
            forecast:       Volatility forecast.
            actual_returns: Actual subsequent returns.
            config:         Volatility configuration (default from engine).

        Returns:
            ForecastMetrics with quality metrics.
        """
        cfg = config or self._config
        return self._comparer.compute_metrics(forecast, actual_returns, cfg)

    def generate_statistics(
        self,
        elapsed: float,
        failed_models: int = 0,
        warnings: tuple[str, ...] = (),
        errors: tuple[str, ...] = (),
    ) -> ForecastStatistics:
        """Generate forecast statistics.

        Args:
            elapsed:       Elapsed time in seconds.
            failed_models: Number of model failures.
            warnings:      Forecast warnings.
            errors:        Forecast error details.

        Returns:
            ForecastStatistics with calculation stats.
        """
        return ForecastStatistics(
            total_forecasts=self._total_forecasts,
            failed_models=failed_models,
            warnings=warnings,
            errors=errors,
            elapsed_seconds=elapsed,
        )
