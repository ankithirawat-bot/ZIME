"""Portfolio optimization exception hierarchy."""

from __future__ import annotations


class OptimizationError(Exception):
    """Base exception for all optimization errors."""


class InvalidObjectiveError(OptimizationError):
    """Raised when an invalid objective function is specified."""

    def __init__(self, objective: str) -> None:
        self.objective = objective
        super().__init__(f"Invalid objective: {objective}")


class InvalidConstraintError(OptimizationError):
    """Raised when an invalid constraint is specified."""

    def __init__(self, constraint: str) -> None:
        self.constraint = constraint
        super().__init__(f"Invalid constraint: {constraint}")


class InfeasiblePortfolioOptimizationError(OptimizationError):
    """Raised when portfolio optimization fails to find a feasible solution."""

    def __init__(self, message: str) -> None:
        super().__init__(f"Infeasible portfolio optimization: {message}")


class OptimizationSolverError(OptimizationError):
    """Raised when the optimization solver encounters an error."""

    def __init__(self, solver: str, message: str) -> None:
        self.solver = solver
        super().__init__(f"Optimizer {solver} failed: {message}")


class InvalidWeightError(OptimizationError):
    """Raised when portfolio weights are invalid."""

    def __init__(self, weights: list[float]) -> None:
        self.weights = weights
        super().__init__(f"Invalid portfolio weights: {weights}")


class ConstraintViolationError(OptimizationError):
    """Raised when a constraint is violated."""

    def __init__(self, constraint: str, value: float, limit: float) -> None:
        self.constraint = constraint
        self.value = value
        self.limit = limit
        super().__init__(
            f"Constraint violation: {constraint} = {value} > {limit}"
        )


class InsufficientAssetsError(OptimizationError):
    """Raised when there are insufficient assets for optimization."""

    def __init__(self, available: int, required: int) -> None:
        self.available = available
        self.required = required
        super().__init__(
            f"Insufficient assets: {available} available, {required} required"
        )


class InvalidCovarianceMatrixError(OptimizationError):
    """Raised when the covariance matrix is invalid for optimization."""

    def __init__(self, message: str) -> None:
        super().__init__(f"Invalid covariance matrix: {message}")


class OptimizationTimeoutError(OptimizationError):
    """Raised when optimization exceeds the time limit."""

    def __init__(self, timeout: float) -> None:
        self.timeout = timeout
        super().__init__(f"Optimization timed out after {timeout} seconds")

