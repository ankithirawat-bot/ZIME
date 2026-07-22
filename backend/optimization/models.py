"""Portfolio optimization models.

Immutable dataclasses for optimization configuration, requests, results,
and portfolio analytics.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from datetime import datetime
from enum import StrEnum
from typing import Any

import numpy as np

from backend.core.constants import (
    DEFAULT_CONFIDENCE_LEVEL,
    DEFAULT_MAX_ITERATIONS,
    DEFAULT_MAX_VOLATILITY,
    DEFAULT_TOLERANCE,
    SOLVER_GRADIENT,
    SOLVER_HEURISTIC,
    SOLVER_QUADRATIC,
)


class ObjectiveType(StrEnum):
    """Types of optimization objectives."""

    MAX_SHARPE = "MAX_SHARPE"
    MIN_VARIANCE = "MIN_VARIANCE"
    MAX_RETURN = "MAX_RETURN"
    MAX_SORTINO = "MAX_SORTINO"
    MIN_CVAR = "MIN_CVAR"
    RISK_PARITY = "RISK_PARITY"
    MAX_DIVERSIFICATION = "MAX_DIVERSIFICATION"
    KELLY = "KELLY"
    BLACK_LITTERMAN = "BLACK_LITTERMAN"
    HRP = "HRP"


class ConstraintType(StrEnum):
    """Types of portfolio constraints."""

    MAX_WEIGHT = "MAX_WEIGHT"
    MIN_WEIGHT = "MIN_WEIGHT"
    SECTOR_EXPOSURE = "SECTOR_EXPOSURE"
    INDUSTRY_EXPOSURE = "INDUSTRY_EXPOSURE"
    CASH_RESERVE = "CASH_RESERVE"
    MAX_TURNOVER = "MAX_TURNOVER"
    MAX_VOLATILITY = "MAX_VOLATILITY"
    MAX_VAR = "MAX_VAR"
    MAX_DRAWDOWN = "MAX_DRAWDOWN"
    LIQUIDITY_THRESHOLD = "LIQUIDITY_THRESHOLD"
    CARDINALITY = "CARDINALITY"
    WEIGHT_NORMALIZATION = "WEIGHT_NORMALIZATION"

    # Alias for backward compatibility in tests
    NORMALIZATION = WEIGHT_NORMALIZATION


class OptimizationStatus(StrEnum):
    """Optimization solver status."""

    OPTIMAL = "OPTIMAL"
    INFEASIBLE = "INFEASIBLE"
    UNBOUNDED = "UNBOUNDED"
    ITERATION_LIMIT = "ITERATION_LIMIT"
    TIME_LIMIT = "TIME_LIMIT"
    NUMERICAL_ERROR = "NUMERICAL_ERROR"
    UNKNOWN = "UNKNOWN"


@dataclass(frozen=True)
class OptimizationMetadata:
    """Metadata for the optimization platform.

    Attributes:
        name: Identifier for the optimization instance.
        version: Schema version.
        created_at: Timestamp of creation.
        author: Creator identifier.
        tags: Searchable metadata tags.
    """

    name: str = ""
    version: str = "1.0"
    created_at: datetime = field(
        default_factory=lambda: datetime.now().astimezone()
    )
    author: str = ""
    tags: tuple[str, ...] = field(default_factory=tuple)


@dataclass(frozen=True)
class OptimizationConfig:
    """Configuration for portfolio optimization.

    Attributes:
        objective: Primary objective to optimize.
        risk_free_rate: Risk-free rate for Sharpe ratio calculations.
        confidence_level: Confidence level for VaR/CVaR calculations.
        max_iterations: Maximum iterations for iterative solvers.
        tolerance: Convergence tolerance for optimizers.
        timeout_seconds: Maximum time allowed for optimization.
        solver_preference: Preferred solver hierarchy.
        rebalance_frequency: How often to rebalance (in days).
        transaction_cost_model: Model for transaction costs.
        max_weight_per_asset: Maximum weight for any single asset.
        min_weight_per_asset: Minimum weight for any single asset.
        sector_limits: Maximum exposure per sector.
        industry_limits: Maximum exposure per industry.
        max_turnover: Maximum portfolio turnover allowed.
        max_volatility: Maximum portfolio volatility allowed.
        max_var: Maximum Value-at-Risk allowed.
        max_drawdown: Maximum drawdown allowed.
        min_liquidity: Minimum liquidity score required.
        max_concentration: Maximum concentration (Herfindahl index).
        cardinality: Maximum number of non-zero positions.
        allow_short_selling: Whether short selling is permitted.
        leverage_limit: Maximum leverage allowed.
        currency: Base currency for calculations.
        benchmark: Benchmark for relative performance.
    """

    objective: ObjectiveType = ObjectiveType.MAX_SHARPE
    risk_free_rate: float = 0.02
    confidence_level: float = DEFAULT_CONFIDENCE_LEVEL
    max_iterations: int = DEFAULT_MAX_ITERATIONS
    tolerance: float = DEFAULT_TOLERANCE
    timeout_seconds: float = 30.0
    solver_preference: tuple[str, ...] = field(
        default_factory=lambda: (SOLVER_QUADRATIC, SOLVER_GRADIENT, SOLVER_HEURISTIC)
    )
    rebalance_frequency: int = 252  # Daily trading days in a year
    transaction_cost_model: str = "linear"
    max_weight_per_asset: float = 0.10
    min_weight_per_asset: float = 0.0
    sector_limits: dict[str, float] = field(default_factory=dict)
    industry_limits: dict[str, float] = field(default_factory=dict)
    max_turnover: float = 0.5
    max_volatility: float = DEFAULT_MAX_VOLATILITY
    max_var: float = 0.05
    max_drawdown: float = 0.15
    min_liquidity: float = 0.3
    max_concentration: float = 0.25
    cardinality: int = 20
    allow_short_selling: bool = False
    leverage_limit: float = 1.0
    currency: str = "USD"
    benchmark: str = "SPX"


@dataclass(frozen=True)
class OptimizationRequest:
    """Request for portfolio optimization.

    Attributes:
        expected_returns: Expected returns for each asset.
        covariance_matrix: Covariance matrix of asset returns.
        asset_names: Names/tickers of assets.
        current_weights: Current portfolio weights (for rebalancing).
        views: Black-Litterman views (if applicable).
        confidences: Confidence in views (if applicable).
        market_caps: Market capitalizations for weighting.
        volumes: Trading volumes for liquidity constraints.
        sector_map: Mapping of assets to sectors.
        industry_map: Mapping of assets to industries.
        risk_budgets: Target risk contributions per asset.
        factor_exposures: Factor exposure matrix.
        timestamp: When the request was generated.
        metadata: Additional request-specific metadata.
    """

    expected_returns: tuple[float, ...]
    covariance_matrix: tuple[tuple[float, ...], ...]
    asset_names: tuple[str, ...]
    current_weights: tuple[float, ...] | None = None
    views: tuple[float, ...] | None = None
    confidences: tuple[float, ...] | None = None
    market_caps: tuple[float, ...] | None = None
    volumes: tuple[float, ...] | None = None
    sector_map: dict[str, str] | None = None
    industry_map: dict[str, str] | None = None
    risk_budgets: tuple[float, ...] | None = None
    factor_exposures: tuple[tuple[float, ...], ...] | None = None
    timestamp: datetime = field(
        default_factory=lambda: datetime.now().astimezone()
    )
    metadata: dict[str, Any] = field(default_factory=dict)


@dataclass(frozen=True)
class OptimizationResult:
    """Result of portfolio
    """
    optimal_weights: tuple[float, ...] = field(default_factory=tuple)
    expected_return: float = 0.0
    expected_volatility: float = 0.0
    sharpe_ratio: float = 0.0
    sortino_ratio: float = 0.0
    max_drawdown: float = 0.0
    var_95: float = 0.0
    cvar_95: float = 0.0
    diversification_ratio: float = 0.0
    effective_n: float = 0.0
    herfindahl_index: float = 0.0
    turnover: float = 0.0
    status: OptimizationStatus = OptimizationStatus.UNKNOWN
    objective_value: float = 0.0
    lagrange_multipliers: tuple[float, ...] = field(default_factory=tuple)
    solve_time: float = 0.0
    iterations: int = 0
    message: str = ""
    metadata: dict[str, Any] = field(default_factory=dict)


@dataclass(frozen=True)
class PortfolioSolution:
    """Complete portfolio solution with analytics.

    Attributes:
        weights: Optimal portfolio weights.
        expected_return: Expected portfolio return.
        expected_volatility: Expected portfolio volatility.
        sharpe_ratio: Sharpe ratio of the portfolio.
        sortino_ratio: Sortino ratio of the portfolio.
        max_drawdown: Maximum drawdown estimate.
        var_95: Value at Risk at 95% confidence.
        cvar_95: Conditional VaR at 95% confidence.
        diversification_ratio: Ratio of weighted avg volatility to portfolio volatility.
        effective_n: Effective number of positions.
        herfindahl_index: Concentration measure.
        turnover: Estimated turnover from current portfolio.
        objective_achieved: Value of the objective function achieved.
        constraint_violations: Any constraint violations.
        solution_details: Additional solution information.
    """

    weights: tuple[float, ...]
    expected_return: float
    expected_volatility: float
    sharpe_ratio: float
    sortino_ratio: float
    max_drawdown: float
    var_95: float
    cvar_95: float
    diversification_ratio: float
    effective_n: float
    herfindahl_index: float
    turnover: float
    objective_achieved: float
    constraint_violations: tuple[str, ...] = field(default_factory=tuple)
    solution_details: dict[str, Any] = field(default_factory=dict)


@dataclass(frozen=True)
class EfficientFrontier:
    """Efficient frontier representing risk-return trade-offs.

    Attributes:
    returns: Expected returns for each portfolio on the frontier.
    volatilities: Expected volatilities for each portfolio.
    sharpe_ratios: Sharpe ratios for each portfolio (alias to sharpes).
    sortinos: Sortino ratios for each portfolio.
    weights: Portfolio weights for each point on the frontier.
    portfolio_solutions: Complete solutions for each frontier point.
    """

    returns: tuple[float, ...]
    volatilities: tuple[float, ...]
    sharpes: tuple[float, ...]
    sortinos: tuple[float, ...]
    weights: tuple[tuple[float, ...], ...]
    portfolio_solutions: tuple[PortfolioSolution, ...]

    @property
    def sharpe_ratios(self) -> tuple[float, ...]:
        return self.sharpes


@dataclass(frozen=True)
class ObjectiveResult:
    """Result of evaluating an objective function.

    Attributes:
        objective_type: Type of objective evaluated.
        value: Numerical value of the objective.
        gradient: Gradient of the objective (if applicable).
        hessian: Hessian of the objective (if applicable).
        contribution_by_asset: Asset-level contributions to objective.
    """

    objective_type: ObjectiveType
    value: float
    gradient: tuple[float, ...] | None = None
    hessian: tuple[tuple[float, ...], ...] | None = None
    contribution_by_asset: tuple[float, ...] = field(default_factory=tuple)


@dataclass(frozen=True)
class OptimizationStatistics:
    """Statistics from optimization process.

    Attributes:
        total_solve_time: Total time spent optimizing.
        average_solve_time: Average time per optimization.
        success_rate: Percentage of successful optimizations.
        average_iterations: Average iterations to convergence.
        objective_improvement: Average improvement in objective value.
        constraint_violations: Number of constraint violations encountered.
        solver_usage: Count of times each solver was used.
    """

    total_solve_time: float = 0.0
    average_solve_time: float = 0.0
    success_rate: float = 0.0
    average_iterations: float = 0.0
    objective_improvement: float = 0.0
    constraint_violations: int = 0
    solver_usage: dict[str, int] = field(default_factory=dict)


@dataclass(frozen=True)
class ConstraintViolation:
    """Details of a constraint violation.

    Attributes:
        constraint_type: Type of constraint violated.
        current_value: Current value of the constraint metric.
        limit_value: Maximum allowed value.
        severity: How severely the constraint is violated (0-1).
        assets_involved: Which assets contribute to the violation.
    """

    constraint_type: ConstraintType
    current_value: float
    limit_value: float
    severity: float = field(default=0.0)
    assets_involved: tuple[str, ...] = field(default_factory=tuple)


# Helper functions for creating tuples from arrays (for immutability)
def _to_tuple(arr: list[float] | np.ndarray) -> tuple[float, ...]:
    """Convert array/list to tuple for immutability."""
    if isinstance(arr, np.ndarray):
        return tuple(arr.tolist())
    return tuple(arr)


def _to_matrix_tuple(
    mat: list[list[float]] | np.ndarray
) -> tuple[tuple[float, ...], ...]:
    """Convert matrix to tuple of tuples for immutability."""
    if isinstance(mat, np.ndarray):
        return tuple(tuple(row) for row in mat.tolist())
    return tuple(tuple(row) for row in mat)

