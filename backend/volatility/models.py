"""Volatility forecast models.

Frozen dataclasses for definitions, requests, forecasts, diagnostics,
comparison results, and estimator protocols.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from datetime import datetime
from typing import Protocol, runtime_checkable

from backend.core.constants import DEFAULT_MAX_ITERATIONS, DEFAULT_TOLERANCE


@dataclass(frozen=True)
class VolatilityMetadata:
    """Metadata for a volatility definition.

    Attributes:
        name:        Name.
        description: Description.
        version:     Schema version.
        author:      Author.
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
        model:           Default model name.
        lookback:        Lookback window.
        horizon:         Default forecast horizon in days.
        annual_factor:   Annualization factor (default 252).
        confidence_level: Confidence level (default 0.95).
        ewma_lambda:     EWMA decay factor (default 0.94).
        garch_p:         GARCH lag p (default 1).
        garch_q:         GARCH lag q (default 1).
        max_iterations:  Max iterations for estimation.
        tolerance:       Convergence tolerance.
        min_periods:     Minimum observations required.
    """

    model: str = "garch"
    lookback: int = 252
    horizon: int = 20
    annual_factor: float = 252.0
    confidence_level: float = 0.95
    ewma_lambda: float = 0.94
    garch_p: int = 1
    garch_q: int = 1
    max_iterations: int = DEFAULT_MAX_ITERATIONS
    tolerance: float = DEFAULT_TOLERANCE
    min_periods: int = 20


@dataclass(frozen=True)
class ForecastDefinition:
    """Complete forecast definition.

    Attributes:
        metadata: Metadata.
        config:   Configuration.
    """

    metadata: VolatilityMetadata
    config: VolatilityConfig


@dataclass(frozen=True)
class ForecastRequest:
    """Request for a volatility forecast.

    Attributes:
        symbol:       Ticker symbol.
        returns:      Historical returns.
        model:        Model name override.
        horizon:      Forecast horizon override.
        config:       Configuration override.
        use_diagnostics: Whether to compute diagnostics.
    """

    symbol: str = ""
    returns: tuple[float, ...] = field(default_factory=tuple)
    model: str = ""
    horizon: int = 20
    config: VolatilityConfig | None = None
    use_diagnostics: bool = False


@dataclass(frozen=True)
class ConfidenceInterval:
    """Confidence interval for a volatility forecast.

    Attributes:
        lower:           Lower bound.
        expected:        Expected volatility.
        upper:           Upper bound.
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
        model:           Model name.
        horizon:         Forecast horizon in days.
        forecast:        Forecast volatility (annualized).
        variance:        Forecast variance.
        confidence:      Confidence interval.
        conditional_vol: In-sample conditional volatility.
        parameters:      Model parameters.
        converged:       Whether estimation converged.
        iterations:      Iterations used.
        log_likelihood:  Log-likelihood.
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
    """Complete forecast result.

    Attributes:
        symbol:        Ticker symbol.
        model:         Model name.
        forecasts:     Forecasts by horizon.
        current_vol:   Current volatility estimate.
        long_term_vol: Long-term average volatility.
        diagnostics:   Model diagnostics.
        elapsed:       Calculation time in seconds.
    """

    symbol: str = ""
    model: str = ""
    forecasts: dict[int, VolatilityForecast] = field(default_factory=dict)
    current_vol: float = 0.0
    long_term_vol: float = 0.0
    diagnostics: ModelDiagnostics | None = None
    elapsed: float = 0.0


@dataclass(frozen=True)
class ModelDiagnostics:
    """Model diagnostic information.

    Attributes:
        residual_variance: Variance of residuals.
        persistence:       Model persistence (alpha+beta for GARCH).
        half_life:         Volatility half-life in days.
        is_stationary:     Whether model satisfies stationarity.
        information_criteria: Information criteria dict.
        convergence_status: Convergence status description.
        n_observations:    Number of observations used.
        n_parameters:      Number of model parameters.
    """

    residual_variance: float = 0.0
    persistence: float = 0.0
    half_life: float = 0.0
    is_stationary: bool = True
    information_criteria: dict[str, float] = field(default_factory=dict)
    convergence_status: str = "converged"
    n_observations: int = 0
    n_parameters: int = 0


@dataclass(frozen=True)
class ForecastMetrics:
    """Forecast quality metrics.

    Attributes:
        rmse:           Root Mean Squared Error.
        mae:            Mean Absolute Error.
        mape:           Mean Absolute Percentage Error.
        bias:           Forecast bias.
        stability:      Forecast stability.
        log_likelihood: Log-likelihood.
        aic:            Akaike Information Criterion.
        bic:            Bayesian Information Criterion.
        n_observations: Observations used.
        n_parameters:   Model parameters.
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
    """Model comparison entry.

    Attributes:
        model_name: Model name.
        rank:       Rank (1 = best).
        metrics:    Forecast metrics.
        score:      Composite score.
    """

    model_name: str = ""
    rank: int = 0
    metrics: ForecastMetrics = field(default_factory=ForecastMetrics)
    score: float = 0.0


@dataclass(frozen=True)
class ForecastStatistics:
    """Forecast statistics.

    Attributes:
        total_forecasts: Total forecasts performed.
        failed_models:   Number of failures.
        warnings:        Warnings.
        errors:          Error details.
        elapsed_seconds: Calculation time.
    """

    total_forecasts: int = 0
    failed_models: int = 0
    warnings: tuple[str, ...] = field(default_factory=tuple)
    errors: tuple[str, ...] = field(default_factory=tuple)
    elapsed_seconds: float = 0.0


@runtime_checkable
class VolatilityEstimator(Protocol):
    """Protocol for volatility estimators."""

    @property
    def name(self) -> str:
        ...

    def fit(
        self,
        returns: tuple[float, ...],
        config: VolatilityConfig,
    ) -> VolatilityForecast:
        """Fit model and return in-sample estimate."""
        ...

    def forecast(
        self,
        returns: tuple[float, ...],
        horizon: int,
        config: VolatilityConfig,
    ) -> VolatilityForecast:
        """Forecast volatility for given horizon."""
        ...

    def forecast_path(
        self,
        returns: tuple[float, ...],
        horizon: int,
        config: VolatilityConfig,
    ) -> tuple[VolatilityForecast, ...]:
        """Return forecast for each step up to horizon."""
        ...

    def update(
        self,
        returns: tuple[float, ...],
        new_return: float,
        config: VolatilityConfig,
    ) -> VolatilityForecast:
        """Recursively update with a single new return."""
        ...

    def diagnostics(
        self,
        forecast: VolatilityForecast,
    ) -> ModelDiagnostics:
        """Compute diagnostics for a fitted model."""
        ...
