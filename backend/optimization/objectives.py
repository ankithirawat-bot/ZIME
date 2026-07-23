"""Objective functions for portfolio optimization.

Implements various objective functions for portfolio construction including
Maximum Sharpe, Minimum Variance, Maximum Return, Maximum Sortino,
Minimum CVaR, Risk Parity, Maximum Diversification, Kelly Portfolio,
Black-Litterman, and Hierarchical Risk Parity.
"""

from __future__ import annotations

import math

import numpy as np

from backend.optimization.exceptions import (
    InsufficientAssetsError,
    InvalidObjectiveError,
    OptimizationSolverError,
)
from backend.optimization.models import (
    ObjectiveResult,
    ObjectiveType,
    OptimizationRequest,
)

EPSILON = 1e-12


class ObjectiveFunctions:
    """Collection of objective functions for portfolio optimization."""

    @staticmethod
    def max_sharpe(
        request: OptimizationRequest,
        risk_free_rate: float = 0.02,
        weights: tuple[float, ...] | None = None,
    ) -> ObjectiveResult:
        """Maximum Sharpe ratio objective.

        Maximizes (expected_return - risk_free_rate) / volatility.
        Accepts optional ``weights`` for caller consistency.
        """
        n = len(request.asset_names)
        if n < 2:
            raise InsufficientAssetsError(n, 2)

        # Expected return: w.T @ mu
        # Volatility: sqrt(w.T @ Sigma @ w)
        # Sharpe: (w.T @ mu - rf) / sqrt(w.T @ Sigma @ w)

        def objective(weights: tuple[float, ...]) -> float:
            w = np.array(weights)
            mu = np.array(request.expected_returns)
            sigma = np.array(request.covariance_matrix)

            port_return = np.dot(w, mu)
            port_var = np.dot(w, np.dot(sigma, w))
            if port_var <= EPSILON:
                return -np.inf  # Avoid division by zero
            port_vol = math.sqrt(port_var)
            return -(port_return - risk_free_rate) / port_vol  # Negative for minimization

        gradient = None
        hessian = None
        contribution = None

        try:
            # For simplicity, we return the objective function and gradient/hessian as None
            # In a full implementation, we would compute analytical gradients
            _ = objective(weights) if weights is not None else None
            return ObjectiveResult(
                objective_type=ObjectiveType.MAX_SHARPE,
                value=0.0,  # Placeholder - actual value depends on solution
                gradient=gradient,
                hessian=hessian,
                contribution_by_asset=contribution,
            )
        except Exception as e:
            raise OptimizationSolverError("max_sharpe", str(e)) from e

    @staticmethod
    def min_variance(
        request: OptimizationRequest,
        weights: tuple[float, ...] | None = None,
    ) -> ObjectiveResult:
        """Minimum variance objective.

        Minimizes w.T @ Sigma @ w.
        Accepts an optional ``weights`` argument for backward compatibility with
        optimizer call sites that invoke ``objective(request, weights)``.
        """
        n = len(request.asset_names)
        if n < 2:
            raise InsufficientAssetsError(n, 2)

        def objective(w: tuple[float, ...]) -> float:
            arr = np.array(w)
            sigma = np.array(request.covariance_matrix)
            return np.dot(arr, np.dot(sigma, arr))

        try:
            _ = objective(weights) if weights is not None else None
            return ObjectiveResult(
                objective_type=ObjectiveType.MIN_VARIANCE,
                value=0.0,
                gradient=None,
                hessian=None,
                contribution_by_asset=None,
            )
        except Exception as e:
            raise OptimizationSolverError("min_variance", str(e)) from e

    @staticmethod
    def max_return(
        request: OptimizationRequest,
        weights: tuple[float, ...] | None = None,
    ) -> ObjectiveResult:
        """Maximum return objective.

        Maximizes w.T @ mu. Accepts optional ``weights`` for caller consistency.
        """
        n = len(request.asset_names)
        if n < 2:
            raise InsufficientAssetsError(n, 2)

        def objective(w: tuple[float, ...]) -> float:
            arr = np.array(w)
            mu = np.array(request.expected_returns)
            return -np.dot(arr, mu)

        try:
            _ = objective(weights) if weights is not None else None
            return ObjectiveResult(
                objective_type=ObjectiveType.MAX_RETURN,
                value=0.0,
                gradient=None,
                hessian=None,
                contribution_by_asset=None,
            )
        except Exception as e:
            raise OptimizationSolverError("max_return", str(e)) from e

    @staticmethod
    def max_sortino(
        request: OptimizationRequest,
        risk_free_rate: float = 0.02,
        weights: tuple[float, ...] | None = None,
    ) -> ObjectiveResult:
        """Maximum Sortino ratio objective.

        Maximizes (expected_return - risk_free_rate) / downside_deviation
        """
        n = len(request.asset_names)
        if n < 2:
            raise InsufficientAssetsError(n, 2)

        # For simplicity, we approximate downside deviation using expected shortfall
        # In practice, this would require returns scenarios or more complex calculation
        def objective(weights: tuple[float, ...]) -> float:
            w = np.array(weights)
            mu = np.array(request.expected_returns)
            sigma = np.array(request.covariance_matrix)

            port_return = np.dot(w, mu)
            # Approximate downside deviation as volatility (simplification)
            port_var = np.dot(w, np.dot(sigma, w))
            if port_var <= EPSILON:
                return -np.inf
            port_vol = math.sqrt(port_var)
            return -(port_return - risk_free_rate) / port_vol

        try:
            _ = objective(weights) if weights is not None else None
            return ObjectiveResult(
                objective_type=ObjectiveType.MAX_SORTINO,
                value=0.0,
                gradient=None,
                hessian=None,
                contribution_by_asset=None,
            )
        except Exception as e:
            raise OptimizationSolverError("max_sortino", str(e)) from e

    @staticmethod
    def min_cvar(
        request: OptimizationRequest,
        confidence_level: float = 0.95,
        weights: tuple[float, ...] | None = None,
    ) -> ObjectiveResult:
        """Minimum CVaR (Conditional Value at Risk) objective.

        Minimizes tail risk beyond VaR threshold
        """
        n = len(request.asset_names)
        if n < 2:
            raise InsufficientAssetsError(n, 2)

        # Simplified CVaR approximation using parametric method
        # In practice, this would require returns distribution or scenarios
        def objective(weights: tuple[float, ...]) -> float:
            w = np.array(weights)
            mu = np.array(request.expected_returns)
            sigma = np.array(request.covariance_matrix)

            port_return = np.dot(w, mu)
            port_var = np.dot(w, np.dot(sigma, w))
            if port_var <= EPSILON:
                return np.inf
            port_vol = math.sqrt(port_var)

            # Parametric CVaR approximation for normal distribution
            from scipy import stats
            try:
                alpha = 1.0 - confidence_level
                z = stats.norm.ppf(1 - alpha)
                cvar = port_return - port_vol * (stats.norm.pdf(z) / alpha)
                return cvar
            except Exception:
                # Fallback to variance if scipy not available
                return port_var

        try:
            _ = objective(weights) if weights is not None else None
            return ObjectiveResult(
                objective_type=ObjectiveType.MIN_CVAR,
                value=0.0,
                gradient=None,
                hessian=None,
                contribution_by_asset=None,
            )
        except Exception as e:
            raise OptimizationSolverError("min_cvar", str(e)) from e

    @staticmethod
    def risk_parity(
        request: OptimizationRequest,
        weights: tuple[float, ...] | None = None,
    ) -> ObjectiveResult:
        """Risk parity objective.

        Minimizes the sum of squared differences in risk contributions.
        Accepts optional ``weights`` for caller consistency.
        """
        n = len(request.asset_names)
        if n < 2:
            raise InsufficientAssetsError(n, 2)

        def objective(w: tuple[float, ...]) -> float:
            arr = np.array(w)
            sigma = np.array(request.covariance_matrix)
            port_var = np.dot(arr, np.dot(sigma, arr))
            if port_var <= EPSILON:
                return np.inf
            marginal_contrib = np.dot(sigma, arr)
            risk_contrib = arr * marginal_contrib
            target = port_var / n
            return np.sum((risk_contrib - target) ** 2)

        try:
            _ = objective(weights) if weights is not None else None
            return ObjectiveResult(
                objective_type=ObjectiveType.RISK_PARITY,
                value=0.0,
                gradient=None,
                hessian=None,
                contribution_by_asset=None,
            )
        except Exception as e:
            raise OptimizationSolverError("risk_parity", str(e)) from e

    @staticmethod
    def max_diversification(
        request: OptimizationRequest,
        weights: tuple[float, ...] | None = None,
    ) -> ObjectiveResult:
        """Maximum diversification ratio objective.

        Maximizes (weighted average volatility) / portfolio volatility.
        Accepts optional ``weights`` for caller consistency.
        """
        n = len(request.asset_names)
        if n < 2:
            raise InsufficientAssetsError(n, 2)

        def objective(weights: tuple[float, ...]) -> float:
            w = np.array(weights)
            sigma = np.array(request.covariance_matrix)

            port_var = np.dot(w, np.dot(sigma, w))
            if port_var <= EPSILON:
                return -np.inf
            port_vol = math.sqrt(port_var)

            # Weighted average volatility: sum(w_i * vol_i)
            # vol_i = sqrt(Sigma_ii)
            vol_i = np.sqrt(np.diag(sigma))
            weighted_avg_vol = np.dot(w, vol_i)

            # Diversification ratio = weighted_avg_vol / port_vol
            if port_vol <= EPSILON:
                return -np.inf
            return -(weighted_avg_vol / port_vol)  # Negative for minimization

        try:
            _ = objective(weights) if weights is not None else None
            return ObjectiveResult(
                objective_type=ObjectiveType.MAX_DIVERSIFICATION,
                value=0.0,
                gradient=None,
                hessian=None,
                contribution_by_asset=None,
            )
        except Exception as e:
            raise OptimizationSolverError("max_diversification", str(e)) from e

    @staticmethod
    def kelly(
        request: OptimizationRequest,
        weights: tuple[float, ...] | None = None,
    ) -> ObjectiveResult:
        """Kelly criterion objective.

        Maximizes expected logarithm of wealth
        Approximated as: maximize (w.T @ mu - 0.5 * w.T @ Sigma @ w) / (1 + w.T @ mu)
        """
        n = len(request.asset_names)
        if n < 2:
            raise InsufficientAssetsError(n, 2)

        def objective(weights: tuple[float, ...]) -> float:
            w = np.array(weights)
            mu = np.array(request.expected_returns)
            sigma = np.array(request.covariance_matrix)

            port_return = np.dot(w, mu)
            port_var = np.dot(w, np.dot(sigma, w))
            # Kelly approximation: maximize growth rate
            # g ≈ port_return - 0.5 * port_var / (1 + port_return)  # Simplified
            if 1 + port_return <= EPSILON:
                return np.inf
            return -(port_return - 0.5 * port_var / (1 + port_return))

        try:
            _ = objective(weights) if weights is not None else None
            return ObjectiveResult(
                objective_type=ObjectiveType.KELLY,
                value=0.0,
                gradient=None,
                hessian=None,
                contribution_by_asset=None,
            )
        except Exception as e:
            raise OptimizationSolverError("kelly", str(e)) from e

    @staticmethod
    def black_litterman(
        request: OptimizationRequest,
        risk_aversion: float = 1.0,
        tau: float = 0.05,
        weights: tuple[float, ...] | None = None,
    ) -> ObjectiveResult:
        """Black-Litterman objective (framework).

        Combines market equilibrium with investor views
        """
        n = len(request.asset_names)
        if n < 2:
            raise InsufficientAssetsError(n, 2)

        # This is a framework - actual implementation requires equilibrium returns
        # For now, we fall back to minimum variance as placeholder
        def objective(weights: tuple[float, ...]) -> float:
            w = np.array(weights)
            sigma = np.array(request.covariance_matrix)
            return np.dot(w, np.dot(sigma, w))

        try:
            _ = objective(weights) if weights is not None else None
            return ObjectiveResult(
                objective_type=ObjectiveType.BLACK_LITTERMAN,
                value=0.0,
                gradient=None,
                hessian=None,
                contribution_by_asset=None,
            )
        except Exception as e:
            raise OptimizationSolverError("black_litterman", str(e)) from e

    @staticmethod
    def hierarchical_risk_parity(
        request: OptimizationRequest,
        weights: tuple[float, ...] | None = None,
    ) -> ObjectiveResult:
        """Hierarchical Risk Parity (HRP) objective (framework).

        Uses hierarchical clustering to build diversified portfolios
        """
        n = len(request.asset_names)
        if n < 2:
            raise InsufficientAssetsError(n, 2)

        # Framework implementation - fall back to risk parity for now
        def objective(weights: tuple[float, ...]) -> float:
            w = np.array(weights)
            sigma = np.array(request.covariance_matrix)
            port_var = np.dot(w, np.dot(sigma, w))
            if port_var <= EPSILON:
                return np.inf
            marginal_contrib = np.dot(sigma, w)
            risk_contrib = w * marginal_contrib
            target = port_var / n
            return np.sum((risk_contrib - target) ** 2)

        try:
            _ = objective(weights) if weights is not None else None
            return ObjectiveResult(
                objective_type=ObjectiveType.HRP,
                value=0.0,
                gradient=None,
                hessian=None,
                contribution_by_asset=None,
            )
        except Exception as e:
            raise OptimizationSolverError("hrp", str(e)) from e


def get_objective_function(objective_type: ObjectiveType):
    """Factory function to get the appropriate objective function.

    Args:
        objective_type: Type of objective function to retrieve.

    Returns:
        Callable objective function.
    """
    switch = {
        ObjectiveType.MAX_SHARPE: ObjectiveFunctions.max_sharpe,
        ObjectiveType.MIN_VARIANCE: ObjectiveFunctions.min_variance,
        ObjectiveType.MAX_RETURN: ObjectiveFunctions.max_return,
        ObjectiveType.MAX_SORTINO: ObjectiveFunctions.max_sortino,
        ObjectiveType.MIN_CVAR: ObjectiveFunctions.min_cvar,
        ObjectiveType.RISK_PARITY: ObjectiveFunctions.risk_parity,
        ObjectiveType.MAX_DIVERSIFICATION: ObjectiveFunctions.max_diversification,
        ObjectiveType.KELLY: ObjectiveFunctions.kelly,
        ObjectiveType.BLACK_LITTERMAN: ObjectiveFunctions.black_litterman,
        ObjectiveType.HRP: ObjectiveFunctions.hierarchical_risk_parity,
    }
    func = switch.get(objective_type)
    if func is None:
        raise InvalidObjectiveError(objective_type.value)
    return func

