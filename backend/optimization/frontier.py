"""Efficient frontier generation for portfolio optimization.

Generates efficient frontier portfolios by solving mean-variance optimization
at multiple target return / risk-aversion levels.
"""

from __future__ import annotations

import numpy as np

from backend.optimization.exceptions import InsufficientAssetsError
from backend.optimization.models import (
    EfficientFrontier,
    ObjectiveType,
    OptimizationRequest,
    PortfolioSolution,
)
from backend.optimization.optimizers import (
    _calculate_cvar,
    _calculate_diversification_ratio,
    _calculate_effective_n,
    _calculate_herfindahl_index,
    _calculate_max_drawdown,
    _calculate_portfolio_metrics,
    _calculate_turnover,
    _calculate_var,
)

EPSILON = 1e-12


class FrontierGenerator:
    """Efficient-frontier generator using risk-aversion parameter sweep."""

    @staticmethod
    def generate_frontier(
        request: OptimizationRequest,
        num_points: int = 50,
        min_return: float | None = None,
        max_return: float | None = None,
    ) -> EfficientFrontier:
        """Generate efficient frontier portfolios.

        Args:
            request: Base optimization request.
            num_points: Number of portfolios on the frontier.
            min_return: Optional override for minimum acceptable return.
            max_return: Optional override for maximum acceptable return.

        Returns:
            Populated EfficientFrontier.

        Raises:
            InsufficientAssetsError: If fewer than 2 assets.
        """
        n = len(request.asset_names)
        if n < 2:
            raise InsufficientAssetsError(n, 2)

        boundary_min, boundary_max = FrontierGenerator._get_return_bounds(request)
        if min_return is None:
            min_return = boundary_min
        if max_return is None:
            max_return = boundary_max
        if max_return <= min_return:
            r_mid = (min_return + max_return) / 2.0
            min_return = r_mid
            max_return = r_mid

        target_returns = np.linspace(min_return, max_return, num_points)

        returns_out: list[float] = []
        vols_out: list[float] = []
        sharpes_out: list[float] = []
        sortinos_out: list[float] = []
        weights_out: list[tuple[float, ...]] = []
        solutions_out: list[PortfolioSolution] = []

        for target in target_returns:
            weights = FrontierGenerator._solve_target_return(
                request, float(target)
            )
            port_return, port_vol, sharpe, sortino = _calculate_portfolio_metrics(
                request, weights
            )
            solution = PortfolioSolution(
                weights=weights,
                expected_return=port_return,
                expected_volatility=port_vol,
                sharpe_ratio=sharpe,
                sortino_ratio=sortino,
                max_drawdown=_calculate_max_drawdown(request, weights),
                var_95=_calculate_var(request, weights),
                cvar_95=_calculate_cvar(request, weights),
                diversification_ratio=_calculate_diversification_ratio(
                    request, weights
                ),
                effective_n=_calculate_effective_n(request, weights),
                herfindahl_index=_calculate_herfindahl_index(request, weights),
                turnover=_calculate_turnover(request, weights),
                objective_achieved=float(target),
                constraint_violations=tuple(),
                solution_details={
                    "objective_type": ObjectiveType.MAX_SHARPE.value,
                    "target_return": float(target),
                },
            )
            returns_out.append(port_return)
            vols_out.append(port_vol)
            sharpes_out.append(sharpe)
            sortinos_out.append(sortino)
            weights_out.append(weights)
            solutions_out.append(solution)

        return EfficientFrontier(
            returns=tuple(returns_out),
            volatilities=tuple(vols_out),
            sharpes=tuple(sharpes_out),
            sortinos=tuple(sortinos_out),
            weights=tuple(weights_out),
            portfolio_solutions=tuple(solutions_out),
        )

    @staticmethod
    def _get_return_bounds(request: OptimizationRequest) -> tuple[float, float]:
        """Return inclusive (min_return, max_return) bounds under fully invested weights."""
        returns = np.array(request.expected_returns, dtype=float)
        return float(np.min(returns)), float(np.max(returns))

    @staticmethod
    def _solve_target_return(
        request: OptimizationRequest,
        target_return: float,
    ) -> tuple[float, ...]:
        """Solve constrained min-variance portfolio for a given target return.

        Analytical closed-form solution via symmetric matrix projection.
        Falls back to equal weights if the system is degenerate.
        """
        n = len(request.asset_names)
        mu = np.array(request.expected_returns, dtype=float)
        sigma = np.array(request.covariance_matrix, dtype=float)

        if n == 0:
            return tuple()

        sigma = (sigma + sigma.T) / 2.0
        try:
            sigma_inv = np.linalg.pinv(sigma)
        except np.linalg.LinAlgError:
            w = np.ones(n) / n
            return tuple(float(x) for x in w)

        ones = np.ones(n)
        a = float(ones @ sigma_inv @ ones)
        b = float(mu @ sigma_inv @ ones)
        c = float(mu @ sigma_inv @ mu)

        denom = a * c - b * b
        if abs(denom) < EPSILON:
            w = np.ones(n) / n
            return tuple(float(x) for x in w)

        lambdas = (c * ones - b * mu) / denom
        gammas = (a * mu - b * ones) / denom
        w = sigma_inv @ (lambdas + gammas * target_return)

        w = np.where(np.isfinite(w), w, 0.0)
        if np.any(w < 0):
            w = np.clip(w, 0.0, None)
        weight_sum = float(np.sum(w))
        if weight_sum > EPSILON:
            w = w / weight_sum
        else:
            w = np.ones(n) / n

        return tuple(float(x) for x in w)
