"""Risk models.

Frozen dataclasses for risk definitions, exposure, VaR, stress tests, and results.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from datetime import datetime
from enum import StrEnum
from typing import Protocol, runtime_checkable


class VaRMethod(StrEnum):
    """Value at Risk calculation methods."""

    HISTORICAL = "HISTORICAL"
    PARAMETRIC = "PARAMETRIC"
    MONTE_CARLO = "MONTE_CARLO"


class ConfidenceLevel(StrEnum):
    """Confidence levels for VaR."""

    P95 = "95"
    P99 = "99"


class StressScenario(StrEnum):
    """Pre-defined stress scenarios."""

    MARKET_CRASH = "MARKET_CRASH"
    SECTOR_CRASH = "SECTOR_CRASH"
    INTEREST_RATE_SHOCK = "INTEREST_RATE_SHOCK"
    VOLATILITY_EXPANSION = "VOLATILITY_EXPANSION"
    LIQUIDITY_SHOCK = "LIQUIDITY_SHOCK"
    CUSTOM = "CUSTOM"


@dataclass(frozen=True)
class RiskMetadata:
    """Metadata for a risk definition.

    Attributes:
        name:        Risk analysis name.
        description: Risk analysis description.
        version:     Schema version.
        author:      Risk analysis author.
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
class RiskConfig:
    """Configuration for risk analysis.

    Attributes:
        var_method:            VaR calculation method.
        confidence_level:      Confidence level.
        lookback_period:       Lookback period in trading days.
        risk_free_rate:        Risk-free rate.
        maximum_var:           Maximum VaR limit.
        maximum_position_size: Maximum position size limit.
        maximum_sector_exposure: Maximum sector exposure limit.
        maximum_drawdown:      Maximum drawdown limit.
        maximum_volatility:    Maximum portfolio volatility limit.
        maximum_concentration: Maximum concentration index limit.
        monte_carlo_simulations: Number of Monte Carlo simulations.
        stress_shock_size:     Shock size for stress tests.
    """

    var_method: VaRMethod = VaRMethod.HISTORICAL
    confidence_level: ConfidenceLevel = ConfidenceLevel.P95
    lookback_period: int = 252
    risk_free_rate: float = 0.06
    maximum_var: float = 0.05
    maximum_position_size: float = 0.25
    maximum_sector_exposure: float = 0.30
    maximum_drawdown: float = 0.20
    maximum_volatility: float = 0.25
    maximum_concentration: float = 0.25
    monte_carlo_simulations: int = 10000
    stress_shock_size: float = 0.20


@dataclass(frozen=True)
class RiskDefinition:
    """Complete risk definition.

    Attributes:
        metadata: Risk metadata.
        config:   Risk configuration.
    """

    metadata: RiskMetadata
    config: RiskConfig


@dataclass(frozen=True)
class Exposure:
    """Portfolio exposure metrics.

    Attributes:
        gross_exposure:      Gross exposure (sum of absolute weights).
        net_exposure:        Net exposure (long - short).
        long_exposure:       Long exposure.
        short_exposure:      Short exposure (future).
        cash_exposure:       Cash exposure.
        sector_exposure:     Sector exposure breakdown.
        industry_exposure:   Industry exposure breakdown.
        position_exposure:   Position exposure breakdown.
        concentration_index: Herfindahl-Hirschman Index.
    """

    gross_exposure: float = 0.0
    net_exposure: float = 0.0
    long_exposure: float = 0.0
    short_exposure: float = 0.0
    cash_exposure: float = 0.0
    sector_exposure: dict[str, float] = field(default_factory=dict)
    industry_exposure: dict[str, float] = field(default_factory=dict)
    position_exposure: dict[str, float] = field(default_factory=dict)
    concentration_index: float = 0.0


@dataclass(frozen=True)
class VaRResult:
    """Value at Risk result.

    Attributes:
        method:           VaR method used.
        confidence_level: Confidence level.
        var:              Value at Risk.
        cvar:             Conditional VaR (Expected Shortfall).
        worst_loss:       Worst loss in the period.
        tail_mean:        Mean of tail losses.
        tail_std:         Standard deviation of tail losses.
        lookback_period:  Lookback period used.
    """

    method: VaRMethod = VaRMethod.HISTORICAL
    confidence_level: ConfidenceLevel = ConfidenceLevel.P95
    var: float = 0.0
    cvar: float = 0.0
    worst_loss: float = 0.0
    tail_mean: float = 0.0
    tail_std: float = 0.0
    lookback_period: int = 252


@dataclass(frozen=True)
class StressTestResult:
    """Stress test result.

    Attributes:
        scenario:       Stress scenario name.
        portfolio_impact: Portfolio impact (negative = loss).
        position_impacts: Position-level impacts.
        recovery_days:  Estimated recovery days.
        description:    Scenario description.
    """

    scenario: str = ""
    portfolio_impact: float = 0.0
    position_impacts: dict[str, float] = field(default_factory=dict)
    recovery_days: int = 0
    description: str = ""


@dataclass(frozen=True)
class ScenarioResult:
    """Scenario analysis result.

    Attributes:
        scenario_name:   Scenario name.
        factors:         Factor changes applied.
        portfolio_return: Expected portfolio return.
        position_returns: Position-level returns.
        variance:        Portfolio variance.
        contribution:    Factor contribution to variance.
    """

    scenario_name: str = ""
    factors: dict[str, float] = field(default_factory=dict)
    portfolio_return: float = 0.0
    position_returns: dict[str, float] = field(default_factory=dict)
    variance: float = 0.0
    contribution: dict[str, float] = field(default_factory=dict)


@dataclass(frozen=True)
class RiskMetrics:
    """Risk metrics.

    Attributes:
        exposure:          Exposure metrics.
        var:               VaR result.
        stress_tests:      Stress test results.
        scenarios:         Scenario analysis results.
        volatility:        Portfolio volatility.
        beta:              Portfolio beta.
        alpha:             Portfolio alpha.
        sharpe_ratio:      Sharpe ratio.
        sortino_ratio:     Sortino ratio.
        maximum_drawdown:  Maximum drawdown.
        tracking_error:    Tracking error.
        information_ratio: Information ratio.
    """

    exposure: Exposure = field(default_factory=Exposure)
    var: VaRResult = field(default_factory=VaRResult)
    stress_tests: tuple[StressTestResult, ...] = field(default_factory=tuple)
    scenarios: tuple[ScenarioResult, ...] = field(default_factory=tuple)
    volatility: float = 0.0
    beta: float = 0.0
    alpha: float = 0.0
    sharpe_ratio: float = 0.0
    sortino_ratio: float = 0.0
    maximum_drawdown: float = 0.0
    tracking_error: float = 0.0
    information_ratio: float = 0.0


@dataclass(frozen=True)
class RiskStatistics:
    """Risk statistics.

    Attributes:
        total_evaluations:    Total risk evaluations performed.
        limit_violations:     Number of limit violations.
        warnings:             Risk warnings.
        violations:           Limit violations details.
        recommended_actions:  Recommended actions.
        elapsed_seconds:      Evaluation time.
    """

    total_evaluations: int = 0
    limit_violations: int = 0
    warnings: tuple[str, ...] = field(default_factory=tuple)
    violations: tuple[str, ...] = field(default_factory=tuple)
    recommended_actions: tuple[str, ...] = field(default_factory=tuple)
    elapsed_seconds: float = 0.0


@dataclass(frozen=True)
class RiskPosition:
    """Position for risk analysis.

    Attributes:
        symbol:       Ticker symbol.
        weight:       Portfolio weight.
        return_series: Historical returns.
        sector:       Sector classification.
        beta:         Position beta.
        volatility:   Position volatility.
    """

    symbol: str
    weight: float = 0.0
    return_series: tuple[float, ...] = field(default_factory=tuple)
    sector: str = ""
    beta: float = 1.0
    volatility: float = 0.0


@runtime_checkable
class ScenarioStrategy(Protocol):
    """Protocol for scenario strategies."""

    def calculate(
        self,
        positions: tuple[RiskPosition, ...],
        config: RiskConfig,
    ) -> ScenarioResult:
        """Calculate scenario impact.

        Args:
            positions: Portfolio positions.
            config:    Risk configuration.

        Returns:
            ScenarioResult with scenario analysis.
        """
        ...
