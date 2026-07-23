"""Portfolio optimization platform.

Institutional-grade portfolio optimization platform.
"""

from __future__ import annotations

from backend.optimization.allocation import (
    AllocationRequest,
    AllocationResult,
    EqualWeight,
    Kelly,
    RiskParity,
    VolatilityTarget,
)
from backend.optimization.analytics import PortfolioAnalytics
from backend.optimization.constraints import Constraints
from backend.optimization.engine import OptimizationEngine
from backend.optimization.exceptions import (
    ConstraintViolationError,
    InfeasiblePortfolioOptimizationError,
    InvalidConstraintError,
    InvalidObjectiveError,
    OptimizationError,
    OptimizationSolverError,
    OptimizationTimeoutError,
)
from backend.optimization.factory import OptimizationFactory
from backend.optimization.models import (
    ConstraintType,
    EfficientFrontier,
    ObjectiveType,
    OptimizationConfig,
    OptimizationMetadata,
    OptimizationRequest,
    OptimizationResult,
    OptimizationStatistics,
    PortfolioSolution,
)
from backend.optimization.models import (  # noqa: N817
    ConstraintViolation as CV,
)
from backend.optimization.objectives import ObjectiveFunctions, get_objective_function
from backend.optimization.optimizers import OptimizerFactory, Optimizers
from backend.optimization.risk_budget import (
    RiskBudget,
    RiskContribution,
    asset_risk_contributions,
    marginal_risk_contributions,
    portfolio_risk,
    risk_contribution_percentages,
    validate_risk_budget,
)

ConstraintViolation = CV

__all__ = [
    # Main classes
    "OptimizationConfig",
    "OptimizationEngine",
    "OptimizationFactory",
    "OptimizationMetadata",
    "OptimizationRequest",
    "OptimizationResult",
    "OptimizationStatistics",
    "PortfolioSolution",
    # Analytics
    "PortfolioAnalytics",
    # Enums / types
    "ConstraintType",
    "ConstraintViolation",
    "EfficientFrontier",
    "ObjectiveType",
    # Exceptions
    "ConstraintViolationError",
    "InfeasiblePortfolioOptimizationError",
    "InvalidConstraintError",
    "InvalidObjectiveError",
    "OptimizationError",
    "OptimizationSolverError",
    "OptimizationTimeoutError",
    # Constraints bridge
    "Constraints",
    # Allocators
    "AllocationRequest",
    "AllocationResult",
    "EqualWeight",
    "RiskParity",
    "VolatilityTarget",
    "Kelly",
    # Risk budgeting
    "RiskContribution",
    "RiskBudget",
    "portfolio_risk",
    "asset_risk_contributions",
    "marginal_risk_contributions",
    "risk_contribution_percentages",
    "validate_risk_budget",
    # Functions
    "ObjectiveFunctions",
    "get_objective_function",
    "OptimizerFactory",
    "Optimizers",
]
