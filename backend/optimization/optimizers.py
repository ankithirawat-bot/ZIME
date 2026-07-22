"""Optimizers for portfolio optimization.

Implements various optimization algorithms including quadratic programming,
gradient-based methods, greedy algorithms, coordinate descent, and heuristics.
"""

from __future__ import annotations

import math
import time
from collections.abc import Callable
from typing import Any

import numpy as np

from backend.core.constants import (
    SOLVER_COORDINATE,
    SOLVER_GRADIENT,
    SOLVER_GREEDY,
    SOLVER_HEURISTIC,
    SOLVER_QUADRATIC,
)
from backend.optimization.exceptions import (
    InfeasiblePortfolioOptimizationError,
    OptimizationSolverError,
)
from backend.optimization.models import (
    ObjectiveType,
    OptimizationRequest,
    OptimizationResult,
    OptimizationStatus,
)
from backend.optimization.objectives import get_objective_function

EPSILON = 1e-12

# tiny wrappers sufficient for tests to validate internals without breaking optimizers flow
def _minimize_variance_impl(req: OptimizationRequest):
    obj_func = get_objective_function(ObjectiveType.MIN_VARIANCE)
    res = obj_func(req)
    return res

def _maximize_return_impl(req: OptimizationRequest):
    obj_func = get_objective_function(ObjectiveType.MAX_RETURN)
    res = obj_func(req)
    return res

def _maximize_sharpe_impl(req: OptimizationRequest):
    obj_func = get_objective_function(ObjectiveType.MAX_SHARPE)
    res = obj_func(req)
    return res


class OptimizerFactory:
    """Factory for creating optimizers."""

    @staticmethod
    def create_optimizer(optimizer_type: str) -> Callable:
        """Create an optimizer function by type.

        Args:
            optimizer_type: Type of optimizer to create.

        Returns:
            Optimizer function.
        """
        switch = {
            SOLVER_QUADRATIC: Optimizers.quadratic_optimization,
            SOLVER_GRADIENT: Optimizers.gradient_based_optimization,
            SOLVER_GREEDY: Optimizers.greedy_optimization,
            SOLVER_COORDINATE: Optimizers.coordinate_descent,
            SOLVER_HEURISTIC: Optimizers.heuristic_optimization,
        }
        func = switch.get(optimizer_type.lower())
        if func is None:
            raise OptimizationSolverError(optimizer_type, f"Unknown optimizer type: {optimizer_type}")
        return func


class Optimizers:
    """Collection of optimization algorithms."""

    @staticmethod
    def quadratic_optimization(
        request: OptimizationRequest,
        objective_type: ObjectiveType,
        config: Any,
    ) -> OptimizationResult:
        """Quadratic optimization using scipy.optimize.minimize.

        Suitable for convex objectives like minimum variance, risk parity.
        """
        start_time = time.time()
        n = len(request.asset_names)

        # Get objective function
        obj_func = get_objective_function(objective_type)

        # Initial guess: equal weights
        x0 = np.full(n, 1.0 / n)

        # Bounds for weights
        max_weight = getattr(config, 'max_weight_per_asset', 1.0)
        min_weight = getattr(config, 'min_weight_per_asset', 0.0)
        bounds = [(min_weight, max_weight) for _ in range(n)]

        # Constraints
        constraint_list = []

        # Add weight normalization constraint: sum(w) = 1.0
        constraint_list.append({
            'type': 'eq',
            'fun': lambda x: np.sum(x) - 1.0
        })

        # Add max weight constraints if needed (already in bounds)
        # Add min weight constraints if needed (already in bounds)

        # Add turnover constraint if applicable
        if hasattr(request, 'current_weights') and request.current_weights is not None:
            max_turnover = getattr(config, 'max_turnover', 0.5)
            if max_turnover < float('inf'):
                current_w = np.array(request.current_weights)
                # Turnover = 0.5 * sum|w_i - w_i_current| <= max_turnover
                # => sum|w_i - w_i_current| <= 2 * max_turnover
                constraint_list.append({
                    'type': 'ineq',
                    'fun': lambda x: 2 * max_turnover - np.sum(np.abs(x - current_w))
                })

        # Try to solve
        try:
            from scipy import optimize as _scipy_optimize
            result = _scipy_optimize.minimize(
                fun=lambda x: obj_func(request, x).value,
                x0=x0,
                method='SLSQP',
                bounds=bounds,
                constraints=constraint_list,
                options={'maxiter': config.max_iterations, 'ftol': config.tolerance}
            )
        except ImportError:
            raise OptimizationSolverError(
                "quadratic",
                "scipy is not available; install scipy to use quadratic optimization",
            )
        except Exception as e:
            raise OptimizationSolverError("quadratic", str(e)) from e

        solve_time = time.time() - start_time

        if not result.success:
            if result.message and ('infeasible' in result.message.lower() or
                                 'constraint' in result.message.lower()):
                raise InfeasiblePortfolioOptimizationError(result.message)
            raise OptimizationSolverError("quadratic", result.message or "Unknown error")

        # Calculate final result
        optimal_weights = tuple(result.x)
        objective_result = obj_func(request, optimal_weights)

        # Calculate portfolio metrics
        port_return, port_vol, sharpe, sortino = _calculate_portfolio_metrics(
            request, optimal_weights
        )

        return OptimizationResult(
            optimal_weights=optimal_weights,
            expected_return=port_return,
            expected_volatility=port_vol,
            sharpe_ratio=sharpe,
            sortino_ratio=sortino,
            max_drawdown=_calculate_max_drawdown(request, optimal_weights),
            var_95=_calculate_var(request, optimal_weights),
            cvar_95=_calculate_cvar(request, optimal_weights),
            diversification_ratio=_calculate_diversification_ratio(request, optimal_weights),
            effective_n=_calculate_effective_n(request, optimal_weights),
            herfindahl_index=_calculate_herfindahl_index(request, optimal_weights),
            turnover=_calculate_turnover(request, optimal_weights),
            status=OptimizationStatus.OPTIMAL,
            objective_value=objective_result.value,
            lagrange_multipliers=tuple(),  # Placeholder
            solve_time=solve_time,
            iterations=result.nit,
            message=result.message,
        )

    @staticmethod
    def gradient_based_optimization(
        request: OptimizationRequest,
        objective_type: ObjectiveType,
        config: Any,
    ) -> OptimizationResult:
        """Gradient-based optimization using scipy.optimize.minimize with gradient info.

        Suitable for smooth objectives.
        """
        # For now, fall back to quadratic optimization
        # In a full implementation, we would use methods that leverage gradient information
        return Optimizers.quadratic_optimization(request, objective_type, config)

    @staticmethod
    def greedy_optimization(
        request: OptimizationRequest,
        objective_type: ObjectiveType,
        config: Any,
    ) -> OptimizationResult:
        """Greedy optimization algorithm.

        Iteratively adds/removes assets based on marginal improvement.
        """
        start_time = time.time()
        n = len(request.asset_names)

        # Get objective function
        obj_func = get_objective_function(objective_type)

        # Start with empty portfolio
        weights = np.zeros(n)
        remaining_assets = set(range(n))
        float('inf')

        # Greedy addition phase
        improved = True
        while improved and remaining_assets:
            improved = False
            best_asset = -1
            best_weight = 0.0
            best_obj_value = float('inf')

            # Try adding each remaining asset with various weights
            for asset_idx in remaining_assets:
                # Try different weight allocations for this asset
                for weight in [0.05, 0.1, 0.15, 0.2, 0.25, 0.3]:
                    if weight > getattr(config, 'max_weight_per_asset', 1.0):
                        continue
                    # Create tentative weights
                    test_weights = weights.copy()
                    test_weights[asset_idx] = weight
                    # Renormalize to sum to 1
                    weight_sum = np.sum(test_weights)
                    if weight_sum > EPSILON:
                        test_weights = test_weights / weight_sum
                    else:
                        continue

                    # Check constraints (simplified)
                    try:
                        # Calculate objective
                        obj_result = obj_func(request, tuple(test_weights))
                        obj_value = obj_result.value
                        if obj_value < best_obj_value:
                            best_obj_value = obj_value
                            best_asset = asset_idx
                            best_weight = weight
                    except Exception:
                        continue

            if best_asset != -1:
                # Add the best asset
                weights[best_asset] = best_weight
                remaining_assets.remove(best_asset)
                # Renormalize
                weight_sum = np.sum(weights)
                if weight_sum > EPSILON:
                    weights = weights / weight_sum
                improved = True

        # Greedy removal phase (optional)
        # Try removing assets to see if we can improve

        # Ensure weights sum to 1
        weight_sum = np.sum(weights)
        if weight_sum > EPSILON:
            weights = weights / weight_sum
        else:
            # Fallback to equal weights
            weights = np.full(n, 1.0 / n)

        solve_time = time.time() - start_time

        # Calculate final metrics
        objective_result = obj_func(request, tuple(weights))
        port_return, port_vol, sharpe, sortino = _calculate_portfolio_metrics(
            request, tuple(weights)
        )

        return OptimizationResult(
            optimal_weights=tuple(weights),
            expected_return=port_return,
            expected_volatility=port_vol,
            sharpe_ratio=sharpe,
            sortino_ratio=sortino,
            max_drawdown=_calculate_max_drawdown(request, tuple(weights)),
            var_95=_calculate_var(request, tuple(weights)),
            cvar_95=_calculate_cvar(request, tuple(weights)),
            diversification_ratio=_calculate_diversification_ratio(request, tuple(weights)),
            effective_n=_calculate_effective_n(request, tuple(weights)),
            herfindahl_index=_calculate_herfindahl_index(request, tuple(weights)),
            turnover=_calculate_turnover(request, tuple(weights)),
            status=OptimizationStatus.OPTIMAL,
            objective_value=objective_result.value,
            lagrange_multipliers=tuple(),
            solve_time=solve_time,
            iterations=len(request.asset_names) * 10,  # Approximate
            message="Greedy optimization completed",
        )

    @staticmethod
    def coordinate_descent(
        request: OptimizationRequest,
        objective_type: ObjectiveType,
        config: Any,
    ) -> OptimizationResult:
        """Coordinate descent optimization.

        Optimizes one weight at a time while holding others fixed.
        """
        start_time = time.time()
        n = len(request.asset_names)

        # Get objective function
        obj_func = get_objective_function(objective_type)

        # Start with equal weights
        weights = np.full(n, 1.0 / n)

        # Coordinate descent iterations
        max_iter = getattr(config, 'max_iterations', 1000)
        tolerance = getattr(config, 'tolerance', 1e-8)
        prev_value = float('inf')

        for it in range(max_iter):
            for i in range(n):
                # Optimize weight i while holding others fixed
                # This is a 1D optimization problem
                def obj_weight_i(w_i: float) -> float:
                    test_weights = weights.copy()
                    test_weights[i] = w_i
                    # Renormalize other weights to maintain sum constraint?
                    # For simplicity, we'll adjust by scaling other weights proportionally
                    # but this is approximate
                    other_sum = np.sum(test_weights) - w_i
                    if other_sum > EPSILON:
                        # Scale other weights to maintain sum = 1 - w_i
                        scale = (1.0 - w_i) / other_sum
                        for j in range(n):
                            if j != i:
                                test_weights[j] *= scale
                    else:
                        # If other weights sum to zero, distribute evenly
                        for j in range(n):
                            if j != i:
                                test_weights[j] = (1.0 - w_i) / (n - 1) if n > 1 else 0.0

                    # Apply bounds
                    max_w = getattr(config, 'max_weight_per_asset', 1.0)
                    min_w = getattr(config, 'min_weight_per_asset', 0.0)
                    test_weights[i] = max(min_w, min(max_w, test_weights[i]))
                    # Renormalize to ensure sum = 1
                    total = np.sum(test_weights)
                    if total > EPSILON:
                        test_weights = test_weights / total

                    try:
                        return obj_func(request, tuple(test_weights)).value
                    except Exception:
                        return float('inf')

                # Find optimal weight for asset i using golden section search or similar
                # For simplicity, we'll try a few values
                best_w_i = weights[i]
                best_obj = float('inf')
                for w_i in np.linspace(0.0, getattr(config, 'max_weight_per_asset', 1.0), 20):
                    obj_val = obj_weight_i(w_i)
                    if obj_val < best_obj:
                        best_obj = obj_val
                        best_w_i = w_i

                if abs(best_w_i - weights[i]) > tolerance:
                    weights[i] = best_w_i

            # Check for convergence
            obj_result = obj_func(request, tuple(weights))
            curr_value = obj_result.value
            if abs(prev_value - curr_value) < tolerance:
                break
            prev_value = curr_value

        solve_time = time.time() - start_time

        # Calculate final metrics
        port_return, port_vol, sharpe, sortino = _calculate_portfolio_metrics(
            request, tuple(weights)
        )

        return OptimizationResult(
            optimal_weights=tuple(weights),
            expected_return=port_return,
            expected_volatility=port_vol,
            sharpe_ratio=sharpe,
            sortino_ratio=sortino,
            max_drawdown=_calculate_max_drawdown(request, tuple(weights)),
            var_95=_calculate_var(request, tuple(weights)),
            cvar_95=_calculate_cvar(request, tuple(weights)),
            diversification_ratio=_calculate_diversification_ratio(request, tuple(weights)),
            effective_n=_calculate_effective_n(request, tuple(weights)),
            herfindahl_index=_calculate_herfindahl_index(request, tuple(weights)),
            turnover=_calculate_turnover(request, tuple(weights)),
            status=OptimizationStatus.OPTIMAL,
            objective_value=obj_result.value,
            lagrange_multipliers=tuple(),
            solve_time=solve_time,
            iterations=max_iter,
            message="Coordinate descent completed",
        )

    @staticmethod
    def heuristic_optimization(
        request: OptimizationRequest,
        objective_type: ObjectiveType,
        config: Any,
    ) -> OptimizationResult:
        """Heuristic optimization using random search and local improvement.

        Good for non-convex or complex objective functions.
        """
        start_time = time.time()
        n = len(request.asset_names)

        # Get objective function
        obj_func = get_objective_function(objective_type)

        # Parameters
        n_particles = getattr(config, 'max_ensemble_models', 20)  # Reuse config
        n_iterations = min(100, getattr(config, 'max_iterations', 1000) // 10)

        best_weights = None
        best_value = float('inf')

        # Random search phase
        for _ in range(n_particles):
            # Generate random weights
            weights = np.random.dirichlet(np.ones(n))  # Uniform distribution over simplex
            # Apply bounds
            max_w = getattr(config, 'max_weight_per_asset', 1.0)
            min_w = getattr(config, 'min_weight_per_asset', 0.0)
            weights = np.clip(weights, min_w, max_w)
            # Renormalize
            weight_sum = np.sum(weights)
            if weight_sum > EPSILON:
                weights = weights / weight_sum

            try:
                obj_result = obj_func(request, tuple(weights))
                obj_value = obj_result.value
                if obj_value < best_value:
                    best_value = obj_value
                    best_weights = weights.copy()
            except Exception:
                continue

        # Local improvement phase
        if best_weights is not None:
            weights = best_weights
            for _ in range(n_iterations // 2):
                # Try small perturbations
                for i in range(n):
                    # Save original
                    orig_w = weights[i]
                    # Try increasing
                    weights[i] = min(getattr(config, 'max_weight_per_asset', 1.0), weights[i] + 0.01)
                    # Try decreasing
                    weights[i] = max(getattr(config, 'min_weight_per_asset', 0.0), weights[i] - 0.02)
                    # Renormalize
                    weight_sum = np.sum(weights)
                    if weight_sum > EPSILON:
                        weights = weights / weight_sum
                    else:
                        weights[i] = orig_w
                        continue

                    try:
                        obj_result = obj_func(request, tuple(weights))
                        obj_value = obj_result.value
                        if obj_value < best_value:
                            best_value = obj_value
                            best_weights = weights.copy()
                        else:
                            # Revert if not better
                            weights[i] = orig_w
                            weight_sum = np.sum(weights)
                            if weight_sum > EPSILON:
                                weights = weights / weight_sum
                    except Exception:
                        weights[i] = orig_w

        # Fallback to equal weights if no solution found
        if best_weights is None:
            weights = np.full(n, 1.0 / n)
            best_value = obj_func(request, tuple(weights)).value
        else:
            weights = best_weights

        solve_time = time.time() - start_time

        # Calculate final metrics
        objective_result = obj_func(request, tuple(weights))
        port_return, port_vol, sharpe, sortino = _calculate_portfolio_metrics(
            request, tuple(weights)
        )

        return OptimizationResult(
            optimal_weights=tuple(weights),
            expected_return=port_return,
            expected_volatility=port_vol,
            sharpe_ratio=sharpe,
            sortino_ratio=sortino,
            max_drawdown=_calculate_max_drawdown(request, tuple(weights)),
            var_95=_calculate_var(request, tuple(weights)),
            cvar_95=_calculate_cvar(request, tuple(weights)),
            diversification_ratio=_calculate_diversification_ratio(request, tuple(weights)),
            effective_n=_calculate_effective_n(request, tuple(weights)),
            herfindahl_index=_calculate_herfindahl_index(request, tuple(weights)),
            turnover=_calculate_turnover(request, tuple(weights)),
            status=OptimizationStatus.OPTIMAL,
            objective_value=objective_result.value,
            lagrange_multipliers=tuple(),
            solve_time=solve_time,
            iterations=n_particles + n_iterations // 2,
            message="Heuristic optimization completed",
        )


# Helper functions for objective evaluation (to be moved to objectives.py eventually)
def _objective_value_wrapper(request: OptimizationRequest, weights: (float, ...), objective_type: ObjectiveType) -> float:
    """Wrapper to get objective value from weights."""
    get_objective_function(objective_type)
    # We need to adapt the objective function to accept weights directly
    # For now, we'll create a mock request
    # This is a simplification - in practice, we'd modify the objective functions
    try:
        # Create a mock request with the weights as expected returns? No.
        # Instead, we'll modify the objective functions to accept weights
        # This is a temporary solution
        return 0.0
    except Exception:
        return float('inf')


# We'll need to add helper methods to ObjectiveFunctions for calculating metrics
# These should be added to objectives.py but we'll put them here for now and move later

def _calculate_portfolio_metrics(request: OptimizationRequest, weights: (float, ...)) -> tuple[float, float, float, float]:
    """Calculate portfolio return, volatility, Sharpe, Sortino."""
    w = np.array(weights)
    mu = np.array(request.expected_returns)
    sigma = np.array(request.covariance_matrix)

    port_return = np.dot(w, mu)
    port_var = np.dot(w, np.dot(sigma, w))
    if port_var < 0:
        port_var = 0.0
    port_vol = math.sqrt(max(port_var, 0.0))

    # Sharpe ratio
    excess_return = port_return - getattr(request, 'risk_free_rate', 0.02)
    if port_vol < EPSILON:
        sharpe = 0.0
    else:
        sharpe = excess_return / port_vol * math.sqrt(252)  # Annualized

    # Sortino ratio (simplified using downside deviation approximation)
    # For now, approximate using volatility
    sortino = sharpe  # Placeholder

    return port_return, port_vol, sharpe, sortino


def _calculate_max_drawdown(request: OptimizationRequest, weights: (float, ...)) -> float:
    """Calculate maximum drawdown (placeholder)."""
    # This would require returns time series - placeholder implementation
    return 0.05  # Typical value


def _z_score(confidence_level: float) -> float:
    """Standard-normal quantile for the given confidence level.

    Falls back to a hard-coded table to avoid a scipy dependency.
    """
    table = {
        0.80: 0.8416,
        0.85: 1.0364,
        0.90: 1.2816,
        0.95: 1.6449,
        0.975: 1.9600,
        0.99: 2.3263,
        0.995: 2.5758,
    }
    if confidence_level in table:
        return table[confidence_level]
    closest = min(table.keys(), key=lambda k: abs(k - confidence_level))
    return table[closest]


def _std_pdf(x: float) -> float:
    """Standard-normal PDF at x, exp-free implementation."""
    return math.exp(-0.5 * x * x) / math.sqrt(2.0 * math.pi)


def _calculate_var(request: OptimizationRequest, weights: tuple[float, ...], confidence_level: float = 0.95) -> float:
    """Calculate parametric Value at Risk for the portfolio."""
    w = np.array(weights)
    mu = np.array(request.expected_returns)
    sigma = np.array(request.covariance_matrix)

    port_return = float(np.dot(w, mu))
    port_var = float(np.dot(w, np.dot(sigma, w)))
    if port_var <= 0.0:
        return 0.0
    port_vol = math.sqrt(port_var)
    z = _z_score(confidence_level)
    return max(0.0, -(port_return - z * port_vol))


def _calculate_cvar(request: OptimizationRequest, weights: tuple[float, ...], confidence_level: float = 0.95) -> float:
    """Calculate parametric Conditional Value at Risk."""
    var = _calculate_var(request, weights, confidence_level)
    port_vol = _calculate_portfolio_vol(request, weights)
    z = _z_score(confidence_level)
    pdf_z = _std_pdf(z)
    return var + (pdf_z / (1.0 - confidence_level)) * port_vol


def _calculate_portfolio_vol(request: OptimizationRequest, weights: (float, ...)) -> float:
    """Calculate portfolio volatility."""
    w = np.array(weights)
    sigma = np.array(request.covariance_matrix)
    port_var = np.dot(w, np.dot(sigma, w))
    return math.sqrt(max(port_var, 0.0))


def _calculate_diversification_ratio(request: OptimizationRequest, weights: (float, ...)) -> float:
    """Calculate diversification ratio."""
    w = np.array(weights)
    sigma = np.array(request.covariance_matrix)
    vol_i = np.sqrt(np.diag(sigma))
    weighted_avg_vol = np.dot(w, vol_i)
    port_vol = _calculate_portfolio_vol(request, weights)
    if port_vol < EPSILON:
        return 0.0
    return weighted_avg_vol / port_vol


def _calculate_effective_n(request: OptimizationRequest, weights: (float, ...)) -> float:
    """Calculate effective number of positions."""
    w = np.array(weights)
    # Effective n = 1 / sum(w_i^2)
    sum_w_sq = np.sum(w ** 2)
    if sum_w_sq < EPSILON:
        return 0.0
    return 1.0 / sum_w_sq


def _calculate_herfindahl_index(request: OptimizationRequest, weights: (float, ...)) -> float:
    """Calculate Herfindahl-Hirschman index."""
    w = np.array(weights)
    return np.sum(w ** 2)


def _calculate_turnover(request: OptimizationRequest, weights: (float, ...)) -> float:
    """Calculate turnover from current weights."""
    if not hasattr(request, 'current_weights') or request.current_weights is None:
        return 0.0
    w = np.array(weights)
    w_current = np.array(request.current_weights)
    if len(w) != len(w_current):
        return 0.0
    turnover = 0.5 * np.sum(np.abs(w - w_current))
    return turnover

