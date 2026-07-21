"""Volatility forecast models.

Frozen dataclasses for volatility definitions, configurations,
forecasts, results, and protocols.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from datetime import datetime
from typing import Protocol, runtime_checkable


@dataclass(frozen=True)
class VolatilityMetadata:
    """Metadata for a volatility forecast definition.

    Attributes:
        name:        Volatility analysis name.
        description: Volatility analysis description.
        version:     Schema version.
        author:      Volatility analysis author.
        created_at:  Creation timestamp.
        tags:        Searchable tags.
    """

    name: str
    description: str = ""
    version: str = "1.0"
    author: str = ""
    created_at: datetime = field(default_factory=lambda: datetime.now().astimezone())
    tags: tuple[str, ...] = field(default_factory=tuple)


@dataclass(frozen=True)
class VolatilityConfig:
    """Configuration for volatility forecasting.

    Attributes:
        model:           Default volatility model name.
        lookback:        Lookback window for historical calculations.
        horizon:         Default forecast horizon in days.
        annual_factor:   Annualization factor (252 for daily data).
        confidence_level: Confidence level for intervals (default 0.95).
        ewma_lambda:     EWMA decay factor (default 0.94).
        garch_p:         GARCH lag order p (default 1).
        garch_q:         GARCH lag order q (default 1).
        max_iterations:  Maximum iterations for parameter estimation.
        tolerance:       Convergence tolerance.
        min_periods:     Minimum number of observations required.
        use_variance_targeting: Whether to use variance targeting.
    """

    model: str = "garch"
    lookback: int = 252
    horizon: int = 20
    annual_factor: float = 252.0
    confidence_level: float = 0.95
    ewma_lambda: float = 0.94
    garch_p: int = 1
    garch_q: int = 1
    max_iterations: int = 1000
    tolerance: float = 1e-8
    min_periods: int = 20
    use_variance_targeting: bool = True


@dataclass(frozen=True)
class ConfidenceInterval:
    """Confidence interval for a volatility forecast.

    Attributes:
        lower:          Lower bound.
        expected:       Expected (central) volatility.
        upper:          Upper bound.
        confidence_level: Confidence level.
    """

    lower: float = 0.0
    expected: float = 0.0
    upper: float = 0.0
    confidence_level: float = 0.95


@dataclass(frozen=True)
class VolatilityForecast:
    """Volatility forecast result.

    Attributes:
        model:           Model name used for forecast.
        horizon:         Forecast horizon in days.
        forecast:        Forecast volatility (annualized).
        variance:        Forecast variance.
        confidence:      Confidence interval.
        conditional_vol: Conditional volatility series (in-sample).
        parameters:      Model parameters.
        converged:       Whether estimation converged.
        iterations:      Number of iterations used.
        log_likelihood:  Log-likelihood of the model.
    """

    model: str = ""
    horizon: int = 20
    forecast: float = 0.0
    variance: float = 0.0
    confidence: ConfidenceInterval = field(default_factory=ConfidenceInterval)
    conditional_vol: tuple[float, ...] = field(default_factory=tuple)
    parameters: dict[str, float] = field(default_factory=dict)
    converged: bool = True
    iterations: int = 0
    log_likelihood: float = 0.0


@dataclass(frozen=True)
class ForecastResult:
    """Complete forecast result for one or more horizons.

    Attributes:
        symbol:       Ticker symbol.
        model:        Model name used.
        forecasts:    Forecasts by horizon.
        current_vol:  Current volatility estimate.
        long_term_vol: Long-term average volatility.
        errors:       Forecast errors (if actuals available).
        elapsed:      Calculation time in seconds.
    """

    symbol: str = ""
    model: str = ""
    forecasts: dict[int, VolatilityForecast] = field(default_factory=dict)
    current_vol: float = 0.0
    long_term_vol: float = 0.0
    errors: dict[str, float] = field(default_factory=dict)
    elapsed: float = 0.0


@dataclass(frozen=True)
class ForecastMetrics:
    """Forecast quality metrics.

    Attributes:
        rmse:           Root Mean Squared Error.
        mae:            Mean Absolute Error.
        mape:           Mean Absolute Percentage Error.
        bias:           Forecast bias (mean error).
        stability:      Forecast stability (std of errors).
        log_likelihood: Log-likelihood.
        aic:            Akaike Information Criterion.
        bic:            Bayesian Information Criterion.
        n_observations: Number of observations used.
        n_parameters:   Number of model parameters.
    """

    rmse: float = 0.0
    mae: float = 0.0
    mape: float = 0.0
    bias: float = 0.0
    stability: float = 0.0
    log_likelihood: float = 0.0
    aic: float = 0.0
    bic: float = 0.0
    n_observations: int = 0
    n_parameters: int = 0


@dataclass(frozen=True)
class ModelComparison:
    """Model comparison result.

    Attributes:
        model_name:  Model name.
        rank:        Overall rank (1 = best).
        metrics:     ForecastMetrics for this model.
        score:       Composite score.
    """

    model_name: str = ""
    rank: int = 0
    metrics: ForecastMetrics = field(default_factory=ForecastMetrics)
    score: float = 0.0


@dataclass(frozen=True)
class ForecastStatistics:
    """Volatility forecast statistics.

    Attributes:
        total_forecasts:   Total forecasts performed.
        failed_models:     Number of model failures.
        warnings:          Forecast warnings.
        errors:            Forecast error details.
        elapsed_seconds:   Calculation time.
    """

    total_forecasts: int = 0
    failed_models: int = 0
    warnings: tuple[str, ...] = field(default_factory=tuple)
    errors: tuple[str, ...] = field(default_factory=tuple)
    elapsed_seconds: float = 0.0


@dataclass(frozen=True)
class ForecastDefinition:
    """Complete volatility forecast definition.

    Attributes:
        metadata: Forecast metadata.
        config:   Forecast configuration.
    """

    metadata: VolatilityMetadata
    config: VolatilityConfig


@runtime_checkable
class VolatilityEstimator(Protocol):
    """Protocol for volatility estimation models."""

    @property
    def name(self) -> str:
        """Model name identifier."""
        ...

    def estimate(
        self,
        returns: tuple[float, ...],
        config: VolatilityConfig,
    ) -> VolatilityForecast:
        """Estimate volatility from returns.

        Args:
            returns: Historical returns.
            config:  Volatility configuration.

        Returns:
            VolatilityForecast with estimated volatility.
        """
        ...

    def forecast(
        self,
        returns: tuple[float, ...],
        horizon: int,
        config: VolatilityConfig,
    ) -> VolatilityForecast:
        """Forecast volatility for a given horizon.

        Args:
            returns: Historical returns.
            horizon: Forecast horizon in days.
            config:  Volatility configuration.

        Returns:
            VolatilityForecast with forecast.
        """
        ...
