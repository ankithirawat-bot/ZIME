"""Portfolio optimization engine.

Main orchestrator for portfolio optimization integrating objectives,
constraints, optimizers, efficient frontier generation, allocation
strategies, and analytics.
"""

from __future__ import annotations

import time
from typing import Any

import numpy as np

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
from backend.optimization.exceptions import (
    InfeasiblePortfolioOptimizationError,
    InsufficientAssetsError,
    InvalidObjectiveError,
    OptimizationError,
    OptimizationSolverError,
    OptimizationTimeoutError,
)
from backend.optimization.frontier import FrontierGenerator
from backend.optimization.models import (
    ConstraintViolation,
    EfficientFrontier,
    ObjectiveResult,
    ObjectiveType,
    OptimizationConfig,
    OptimizationRequest,
    OptimizationResult,
    OptimizationStatus,
    PortfolioSolution,
)
from backend.optimization.optimizers import (
    OptimizerFactory,
    _calculate_cvar,
    _calculate_diversification_ratio,
    _calculate_effective_n,
    _calculate_herfindahl_index,
    _calculate_max_drawdown,
    _calculate_portfolio_metrics,
    _calculate_turnover,
    _calculate_var,
)


class OptimizationEngine:
    """Main portfolio optimization engine.

    Integrates objective functions, constraints, optimizers,
    efficient frontier generation, allocation strategies, and analytics
    for institutional-grade portfolio construction.
    """

    def __init__(
        self,
        config: OptimizationConfig | None = None,
    ) -> None:
        """Initialize the optimization engine.

        Args:
            config: Optimization configuration (uses defaults if None).
        """
        self._config = config or OptimizationConfig()
        self._stats = {
            "total_solve_time": 0.0,
            "success_count": 0,
            "total_iterations": 0,
            "solver_usage": {},
            "failure_count": 0,
        }

    @property
    def config(self) -> OptimizationConfig:
        """Get the current optimization configuration."""
        return self._config

    @property
    def statistics(self) -> dict[str, Any]:
        """Get optimization statistics.

        Returns:
            Dictionary of optimization statistics.
        """
        stats = dict(self._stats)
        total_attempts = stats["success_count"] + stats.get("failure_count", 0)
        if stats["success_count"] > 0:
            stats["average_solve_time"] = stats["total_solve_time"] / stats["success_count"]
            stats["average_iterations"] = stats["total_iterations"] / stats["success_count"]
        else:
            stats["average_solve_time"] = 0.0
            stats["average_iterations"] = 0.0
        stats["success_rate"] = (
            stats["success_count"] / max(total_attempts, 1)
            if total_attempts > 0 else 0.0
        )
        return stats

    # ======================= Core Optimization Methods =======================

    def optimize(
        self,
        request: OptimizationRequest,
        objective_type: ObjectiveType | str = ObjectiveType.MAX_SHARPE,
    ) -> OptimizationResult:
        """Optimize portfolio for a given objective function.

        Args:
            request: Optimization request with asset data and constraints.
            objective_type: Objective function to optimize (uses config default if string not recognized).

        Returns:
            OptimizationResult with optimal portfolio weights and metrics.

        Raises:
            InvalidObjectiveError: If objective type is not supported.
            InfeasiblePortfolioOptimizationError: If no feasible solution exists.
            OptimizationSolverError: If the optimizer fails to converge.
            OptimizationTimeoutError: If optimization exceeds time limit.
        """
        start_time = time.time()

        # Convert objective type if string
        if isinstance(objective_type, str):
            try:
                objective_type = ObjectiveType(objective_type)
            except ValueError:
                raise InvalidObjectiveError(objective_type)

        # Validate request
        self._validate_request(request)

        # Try solvers in preference order
        last_error = None
        for solver_name in self._config.solver_preference:
            try:
                optimizer_func = OptimizerFactory.create_optimizer(solver_name)
                result = optimizer_func(request, objective_type, self._config)

                # Validate the result satisfies constraints
                is_valid, violations = Constraints.validate_weights(result.optimal_weights, request)
                if not is_valid:
                    raise OptimizationSolverError(solver_name, f"Solution violates constraints: {[str(v) for v in violations]}")

                # Update statistics
                solve_time = time.time() - start_time
                self._stats["total_solve_time"] += solve_time
                self._stats["success_count"] += 1
                self._stats["total_iterations"] += result.iterations
                self._stats["solver_usage"][solver_name] = self._stats["solver_usage"].get(solver_name, 0) + 1

                return result

            except (InfeasiblePortfolioOptimizationError, OptimizationSolverError, OptimizationTimeoutError) as e:
                last_error = e
                # Try next solver
                continue
            except Exception as e:
                last_error = OptimizationSolverError(solver_name, f"Unexpected error: {str(e)}")
                continue

        # If we get here, all solvers failed
        if last_error:
            raise last_error
        else:
            raise OptimizationError("All optimizers failed without specific error")

    def efficient_frontier(
        self,
        request: OptimizationRequest,
        num_points: int = 100,
        min_return: float | None = None,
        max_return: float | None = None,
    ) -> EfficientFrontier:
        """Generate efficient frontier for the given request.

        Args:
            request: Optimization request with asset data and constraints.
            num_points: Number of points to generate on the frontier.
            min_return: Minimum return to consider (optional).
            max_return: Maximum return to consider (optional).

        Returns:
            EfficientFrontier containing portfolios across the risk-return spectrum.

        Raises:
            InfeasiblePortfolioOptimizationError: If unable to generate frontier points.
        """
        start_time = time.time()

        try:
            frontier = FrontierGenerator.generate_frontier(
                request, num_points, min_return, max_return
            )

            # Update statistics
            solve_time = time.time() - start_time
            self._stats["total_solve_time"] += solve_time
            self._stats["success_count"] += 1

            return frontier
        except Exception as e:
            raise InfeasiblePortfolioOptimizationError(f"Failed to generate efficient frontier: {str(e)}") from e

    def rebalance(
        self,
        request: OptimizationRequest,
        objective_type: ObjectiveType | str = ObjectiveType.MAX_SHARPE,
        tolerance: float = 0.01,
    ) -> tuple[PortfolioSolution, dict[str, Any]]:
        """Generate rebalancing trades from current portfolio to target.

        Args:
            request: Optimization request (should include current_weights).
            objective_type: Objective function for target portfolio.
            tolerance: Maximum allowable deviation from current weights before rebalancing.

        Returns:
            Tuple of (target_portfolio, rebalancing_trades) where:
                target_portfolio: PortfolioSolution for target weights.
                rebalancing_trades: Dictionary with trade details.
        """
        if request.current_weights is None:
            raise OptimizationError("Current weights required for rebalancing")

        # Get target portfolio
        target_result = self.optimize(request, objective_type)
        target_solution = PortfolioSolution(
            weights=target_result.optimal_weights,
            expected_return=target_result.expected_return,
            expected_volatility=target_result.expected_volatility,
            sharpe_ratio=target_result.sharpe_ratio,
            sortino_ratio=target_result.sortino_ratio,
            max_drawdown=target_result.max_drawdown,
            var_95=target_result.var_95,
            cvar_95=target_result.cvar_95,
            diversification_ratio=target_result.diversification_ratio,
            effective_n=target_result.effective_n,
            herfindahl_index=target_result.herfindahl_index,
            turnover=target_result.turnover,
            objective_achieved=target_result.objective_value,
            constraint_violations=tuple(),  # Would need to calculate from constraints
            solution_details={
                "objective": objective_type.value if isinstance(objective_type, ObjectiveType) else str(objective_type),
                "solver_used": "unknown",  # Would need to track this
            }
        )

        # Calculate rebalancing trades
        current_weights = np.array(request.current_weights)
        target_weights = np.array(target_solution.weights)

        # Calculate trades needed
        weight_diffs = target_weights - current_weights
        abs_weight_diffs = np.abs(weight_diffs)
        total_turnover = np.sum(abs_weight_diffs)

        # Identify buy/sell actions
        buys = {}
        sells = {}
        for i, asset in enumerate(request.asset_names):
            diff = weight_diffs[i]
            if diff > tolerance:
                buys[asset] = diff
            elif diff < -tolerance:
                sells[asset] = -diff

        rebalancing_info = {
            "current_weights": dict(zip(request.asset_names, current_weights.tolist())),
            "target_weights": dict(zip(request.asset_names, target_weights.tolist())),
            "weight_changes": dict(zip(request.asset_names, weight_diffs.tolist())),
            "total_turnover": float(total_turnover),
            "buy_orders": buys,
            "sell_orders": sells,
            "num_assets_to_buy": len(buys),
            "num_assets_to_sell": len(sells),
        }

        return target_solution, rebalancing_info

    def evaluate(
        self,
        request: OptimizationRequest,
        weights: tuple[float, ...],
    ) -> tuple[OptimizationResult, list[ConstraintViolation]]:
        """Evaluate a given set of portfolio weights.

        Args:
            request: Optimization request with asset data.
            weights: Portfolio weights to evaluate.

        Returns:
            Tuple of (OptimizationResult, list_of_constraint_violations).
        """
        start_time = time.time()

        # Validate weights
        is_valid, violations = Constraints.validate_weights(weights, request)

        # Calculate portfolio metrics
        if len(weights) == len(request.asset_names):
            port_return, port_vol, sharpe, sortino = self._calculate_portfolio_metrics(request, weights)
            max_dd = _calculate_max_drawdown(request, weights)
            var_95 = _calculate_var(request, weights)
            cvar_95 = _calculate_cvar(request, weights)
            div_ratio = _calculate_diversification_ratio(request, weights)
            effective_n = _calculate_effective_n(request, weights)
            herfindahl = _calculate_herfindahl_index(request, weights)
            turnover = _calculate_turnover(request, weights)

            # Use default objective for evaluation (could make this configurable)
            objective_result = self._evaluate_objective(request, weights, self._config.objective)

            result = OptimizationResult(
                optimal_weights=weights,
                expected_return=port_return,
                expected_volatility=port_vol,
                sharpe_ratio=sharpe,
                sortino_ratio=sortino,
                max_drawdown=max_dd,
                var_95=var_95,
                cvar_95=cvar_95,
                diversification_ratio=div_ratio,
                effective_n=effective_n,
                herfindahl_index=herfindahl,
                turnover=turnover,
                status=OptimizationStatus.OPTIMAL if is_valid else OptimizationStatus.UNKNOWN,
                objective_value=objective_result.value,
                lagrange_multipliers=tuple(),
                solve_time=time.time() - start_time,
                iterations=0,
                message="Evaluation completed" if is_valid else "Constraint violations found",
            )
        else:
            # Wrong number of weights
            result = OptimizationResult(
                optimal_weights=weights,
                expected_return=0.0,
                expected_volatility=0.0,
                sharpe_ratio=0.0,
                sortino_ratio=0.0,
                max_drawdown=0.0,
                var_95=0.0,
                cvar_95=0.0,
                diversification_ratio=0.0,
                effective_n=0.0,
                herfindahl_index=0.0,
                turnover=0.0,
                status=OptimizationStatus.UNKNOWN,
                objective_value=0.0,
                lagrange_multipliers=tuple(),
                solve_time=time.time() - start_time,
                iterations=0,
                message=f"Weight count mismatch: expected {len(request.asset_names)}, got {len(weights)}",
            )

        return result, violations

    def recommend(
        self,
        request: OptimizationRequest,
        context: dict[str, Any] | None = None,
    ) -> dict[str, Any]:
        """Generate portfolio recommendation based on request and context.

        Args:
            request: Optimization request with asset data and constraints.
            context: Optional context including market regime, intelligence signals, etc.

        Returns:
            Dictionary containing recommendation details.
        """
        context = context or {}

        # Get recommended portfolio using default objective
        result = self.optimize(request, self._config.objective)

        # Create portfolio solution
        solution = PortfolioSolution(
            weights=result.optimal_weights,
            expected_return=result.expected_return,
            expected_volatility=result.expected_volatility,
            sharpe_ratio=result.sharpe_ratio,
            sortino_ratio=result.sortino_ratio,
            max_drawdown=result.max_drawdown,
            var_95=result.var_95,
            cvar_95=result.cvar_95,
            diversification_ratio=result.diversification_ratio,
            effective_n=result.effective_n,
            herfindahl_index=result.herfindahl_index,
            turnover=result.turnover,
            objective_achieved=result.objective_value,
            constraint_violations=tuple(),  # Would need to get from validate_weights
            solution_details={
                "objective": self._config.objective_type.value,
                "solver": result.method,
                "status": result.status.value,
                "iterations": result.iterations,
                "solve_time": result.solve_time,
            }
        )

        # Get analytics
        analytics = PortfolioAnalytics.calculate_analytics(request, solution)

        # Generate explanation
        explanation = self._generate_explanation(request, solution, context)

        return {
            "portfolio": solution,
            "analytics": analytics,
            "explanation": explanation,
            "request_summary": {
                "num_assets": len(request.asset_names),
                "objective": self._config.objective.value,
                "constraints_applied": len(self._get_applicable_constraints(request)),
            }
        }

    # ======================= Helper Methods =======================

    def _validate_request(self, request: OptimizationRequest) -> None:
        """Validate optimization request.

        Args:
            request: Optimization request to validate.

        Raises:
            InsufficientAssetsError: If insufficient assets for optimization.
            ValueError: If request data is malformed.
        """
        n = len(request.asset_names)
        if n < 2:
            raise InsufficientAssetsError(n, 2)

        # Check expected returns length
        if len(request.expected_returns) != n:
            raise ValueError(f"Expected returns length {len(request.expected_returns)} does not match number of assets {n}")

        # Check covariance matrix dimensions
        cov_matrix = np.array(request.covariance_matrix)
        if cov_matrix.shape != (n, n):
            raise ValueError(f"Covariance matrix shape {cov_matrix.shape} does not match ({n}, {n})")

        # Check if covariance matrix is valid (symmetric, positive semi-definite)
        if not np.allclose(cov_matrix, cov_matrix.T):
            raise ValueError("Covariance matrix is not symmetric")

        # Check eigenvalues for positive semi-definiteness
        try:
            eigenvals = np.linalg.eigvals(cov_matrix)
            if np.any(eigenvals < -1e-8):  # Allow small negative values due to numerical precision
                raise ValueError("Covariance matrix is not positive semi-definite")
        except np.linalg.LinAlgError:
            raise ValueError("Cannot compute eigenvalues of covariance matrix")

        # Check current weights if provided
        if request.current_weights is not None:
            if len(request.current_weights) != n:
                raise ValueError(f"Current weights length {len(request.current_weights)} does not match number of assets {n}")

        # Check views if provided (for Black-Litterman)
        if request.views is not None:
            if len(request.views) != n:
                raise ValueError(f"Views length {len(request.views)} does not match number of assets {n}")

        # Check confidences if provided
        if request.confidences is not None:
            if len(request.confidences) != n:
                raise ValueError(f"Confidences length {len(request.confidences)} does not match number of assets {n}")

    def _calculate_portfolio_metrics(
        self,
        request: OptimizationRequest,
        weights: tuple[float, ...],
    ) -> tuple[float, float, float, float]:
        """Calculate portfolio return, volatility, Sharpe, Sortino.

        Args:
            request: Optimization request.
            weights: Portfolio weights.

        Returns:
            Tuple of (expected_return, expected_volatility, sharpe_ratio, sortino_ratio).
        """
        return _calculate_portfolio_metrics(request, weights)

    def _calculate_max_drawdown(
        self,
        request: OptimizationRequest,
        weights: tuple[float, ...],
    ) -> float:
        """Calculate maximum drawdown.

        Args:
            request: Optimization request.
            weights: Portfolio weights.

        Returns:
            Maximum drawdown.
        """
        from backend.optimization.optimizers import _calculate_max_drawdown
        return _calculate_max_drawdown(request, weights)

    def _calculate_var(
        self,
        request: OptimizationRequest,
        weights: tuple[float, ...],
        confidence_level: float = 0.95,
    ) -> float:
        """Calculate Value at Risk.

        Args:
            request: Optimization request.
            weights: Portfolio weights.
            confidence_level: Confidence level for VaR.

        Returns:
            Value at Risk.
        """
        from backend.optimization.optimizers import _calculate_var
        return _calculate_var(request, weights, confidence_level)

    def _calculate_cvar(
        self,
        request: OptimizationRequest,
        weights: tuple[float, ...],
        confidence_level: float = 0.95,
    ) -> float:
        """Calculate Conditional Value at Risk.

        Args:
            request: Optimization request.
            weights: Portfolio weights.
            confidence_level: Confidence level for CVaR.

        Returns:
            Conditional Value at Risk.
        """
        from backend.optimization.optimizers import _calculate_cvar
        return _calculate_cvar(request, weights, confidence_level)

    def _evaluate_objective(
        self,
        request: OptimizationRequest,
        weights: tuple[float, ...],
        objective_type: ObjectiveType,
    ) -> ObjectiveResult:
        """Evaluate a specific objective function at given weights.

        Args:
        request: Optimization request.
        weights: Portfolio weights.
        objective_type: Objective function to evaluate.

        Returns:
        ObjectiveResult with objective value and diagnostics.
        """
        from backend.optimization.objectives import get_objective_function
        obj_func = get_objective_function(objective_type)
        # Recreate a tiny request to feed objective
        cov = np.zeros((len(weights), len(weights)))
        if len(request.expected_returns) == len(weights):
            for i in range(len(weights)):
                cov[i][i] = weights[i]
                for j in range(len(weights)):
                    cov[i][j] = 0.1
        subreq = OptimizationRequest(
            expected_returns=tuple(np.array(request.expected_returns) * np.array(weights)),
            covariance_matrix=tuple(tuple(r) for r in cov),
            asset_names=request.asset_names[:len(weights)],
        )
        try:
            res = obj_func(subreq)
        except Exception:
            res = ObjectiveResult(objective_type=objective_type, value=0.0)
        return res

    def _get_applicable_constraints(self, request: OptimizationRequest) -> list[str]:
        """Get list of applicable constraints for the request.

        Args:
            request: Optimization request.

        Returns:
            List of constraint descriptions that are active.
        """
        constraints = []

        # Check which constraints have non-default values
        if hasattr(self._config, 'max_weight_per_asset') and self._config.max_weight_per_asset < 1.0:
            constraints.append(f"Max weight per asset: {self._config.max_weight_per_asset}")

        if hasattr(self._config, 'min_weight_per_asset') and self._config.min_weight_per_asset > 0.0:
            constraints.append(f"Min weight per asset: {self._config.min_weight_per_asset}")

        if getattr(self._config, 'sector_limits', None):
            constraints.append(f"Sector limits: {len(self._config.sector_limits)} sectors")

        if getattr(self._config, 'industry_limits', None):
            constraints.append(f"Industry limits: {len(self._config.industry_limits)} industries")

        if hasattr(self._config, 'max_turnover') and self._config.max_turnover < 1.0:
            constraints.append(f"Max turnover: {self._config.max_turnover}")

        if hasattr(self._config, 'max_volatility') and self._config.max_volatility < 1.0:
            constraints.append(f"Max volatility: {self._config.max_volatility}")

        if hasattr(self._config, 'max_var') and self._config.max_var < 1.0:
            constraints.append(f"Max VaR: {self._config.max_var}")

        if hasattr(self._config, 'max_drawdown') and self._config.max_drawdown < 1.0:
            constraints.append(f"Max drawdown: {self._config.max_drawdown}")

        if hasattr(self._config, 'min_liquidity') and self._config.min_liquidity > 0.0:
            constraints.append(f"Min liquidity: {self._config.min_liquidity}")

        if hasattr(self._config, 'max_concentration') and self._config.max_concentration < 1.0:
            constraints.append(f"Max concentration: {self._config.max_concentration}")

        if hasattr(self._config, 'cardinality') and self._config.cardinality < len(request.asset_names):
            constraints.append(f"Cardinality limit: {self._config.cardinality}")

        return constraints

    def _generate_explanation(
        self,
        request: OptimizationRequest,
        solution: PortfolioSolution,
        context: dict[str, Any] | None = None,
    ) -> dict[str, Any]:
        """Generate explanation for the optimization result.

        Args:
            request: Optimization request.
            solution: Portfolio solution.
            context: Optional context including market regime, intelligence signals, etc.

        Returns:
            Dictionary containing explanation details.
        """
        context = context or {}

        explanation = {
            "objective_used": self._config.objective.value,
            "objective_description": self._get_objective_description(self._config.objective),
            "key_holdings": self._get_key_holdings(solution),
            "risk_profile": self._assess_risk_profile(solution),
            "diversification_assessment": self._assess_diversification(solution),
            "allocation_symbols": self._get_allocation_symbols(solution),
            "constraints_summary": self._get_applicable_constraints(request),
        }

        # Add context-specific explanations if available
        if context.get("regime"):
            explanation["regime_context"] = f"Optimized for {context['regime']} market conditions"

        if context.get("intelligence_signal"):
            explanation["intelligence_context"] = f"Adjusted based on intelligence signals: {context['intelligence_signal']}"

        return explanation

    def _get_objective_description(self, objective_type: ObjectiveType) -> str:
        """Get human-readable description of objective type."""
        descriptions = {
            ObjectiveType.MAX_SHARPE: "Maximize risk-adjusted returns (Sharpe ratio)",
            ObjectiveType.MIN_VARIANCE: "Minimize portfolio volatility (variance)",
            ObjectiveType.MAX_RETURN: "Maximize expected returns",
            ObjectiveType.MAX_SORTINO: "Maximize downside risk-adjusted returns (Sortino ratio)",
            ObjectiveType.MIN_CVAR: "Minimize tail risk (Conditional Value at Risk)",
            ObjectiveType.RISK_PARITY: "Equalize risk contributions across assets",
            ObjectiveType.MAX_DIVERSIFICATION: "Maximize diversification ratio",
            ObjectiveType.KELLY: "Maximize long-term growth rate (Kelly criterion)",
            ObjectiveType.BLACK_LITTERMAN: "Blend market equilibrium with investor views",
            ObjectiveType.HRP: "Hierarchical Risk Parity using tree clustering",
        }
        return descriptions.get(objective_type, "Custom objective")

    def _get_key_holdings(self, solution: PortfolioSolution) -> list[dict[str, Any]]:
        """Get top holdings in the portfolio.

        Args:
            solution: Portfolio solution.

        Returns:
            List of dictionaries with holding information.
        """
        # Create list of (weight, index) pairs
        weighted_indices = [(w, i) for i, w in enumerate(solution.weights)]
        # Sort by weight descending
        weighted_indices.sort(reverse=True)

        # Get top 5 holdings
        top_holdings = []
        for weight, idx in weighted_indices[:5]:
            top_holdings.append({
                "asset_index": idx,
                "weight": weight,
                "weight_percentage": weight * 100.0,
            })

        return top_holdings

    def _assess_risk_profile(self, solution: PortfolioSolution) -> dict[str, Any]:
        """Assess the risk profile of the portfolio.

        Args:
            solution: Portfolio solution.

        Returns:
            Dictionary with risk assessment.
        """
        vol = solution.expected_volatility
        max_dd = solution.max_drawdown

        risk_level = "Low"
        if vol > 0.25:  # 25% annual volatility
            risk_level = "High"
        elif vol > 0.15:  # 15% annual volatility
            risk_level = "Medium"

        return {
            "volatility": vol,
            "volatility_level": risk_level,
            "max_drawdown": max_dd,
            "drawdown_severity": "Low" if max_dd < 0.1 else "Medium" if max_dd < 0.2 else "High",
        }

    def _assess_diversification(self, solution: PortfolioSolution) -> dict[str, Any]:
        """Assess diversification of the portfolio.

        Args:
            solution: Portfolio solution.

        Returns:
            Dictionary with diversification assessment.
        """
        eff_n = solution.effective_n
        herfindahl = solution.herfindahl_index
        div_ratio = solution.diversification_ratio

        diversification_level = "Low"
        if eff_n > 10:
            diversification_level = "High"
        elif eff_n > 5:
            diversification_level = "Medium"

        return {
            "effective_number_of_positions": eff_n,
            "diversification_level": diversification_level,
            "herfindahl_index": herfindahl,
            "concentration_level": "High" if herfindahl > 0.3 else "Medium" if herfindahl > 0.1 else "Low",
            "diversification_ratio": div_ratio,
        }

    def _get_allocation_symbols(self, solution: PortfolioSolution) -> list[str]:
        """Get allocation symbols based on portfolio characteristics.

        Args:
            solution: Portfolio solution.

        Returns:
            List of symbolic descriptors.
        """
        symbols = []

        # Based on concentration
        if solution.herfindahl_index < 0.1:
            symbols.append("WELL_DIVERSIFIED")
        elif solution.herfindahl_index < 0.25:
            symbols.append("MODERATELY_CONCENTRATED")
        else:
            symbols.append("HIGHLY_CONCENTRATED")

        # Based on turnover
        if solution.turnover < 0.1:
            symbols.append("LOW_TURNOVER")
        elif solution.turnover < 0.3:
            symbols.append("MODERATE_TURNOVER")
        else:
            symbols.append("HIGH_TURNOVER")

        # Based on Sharpe ratio
        if solution.sharpe_ratio > 1.5:
            symbols.append("HIGH_SHARPE")
        elif solution.sharpe_ratio > 0.5:
            symbols.append("MODERATE_SHARPE")
        else:
            symbols.append("LOW_SHARPE")

        return symbols

    # ======================= Advanced Allocation & Analytics (42B) =======================

    def allocate(self, request_dict: dict[str, Any]) -> AllocationResult:
        """Build an allocation without using full optimizer stack (choose engine strategically).

        Args:
            request_dict: dict with keys expected_returns, volatilities, covariance, options.

        Returns:
            AllocationResult
        """
        n = len(request_dict.get("asset_names", ()))
        if n == 0:
            # Derive asset count from expected_returns when asset_names omitted.
            n = len(request_dict.get("expected_returns", ()) or ())
        expected_returns = tuple(request_dict.get("expected_returns", ()) or [0.0] * n)
        expected_volatilities = tuple(request_dict.get("volatilities", ()) or [1.0] * n)
        cov = request_dict.get("covariance", None)
        if cov is None:
            cov = tuple(tuple(0.1 if i != j else v ** 2 for j in range(n)) for i, v in enumerate(expected_volatilities))
        asset_names = tuple(request_dict.get("asset_names", ())) or tuple(f"A{i}" for i in range(n))
        req = AllocationRequest(
            expected_returns=expected_returns,
            expected_volatilities=expected_volatilities,
            covariance=cov,
            asset_names=asset_names,
            cash_reserve=float(request_dict.get("cash_reserve", 0.0)),
            max_weight_per_asset=float(request_dict.get("max_weight", 1.0)),
            min_weight_per_asset=float(request_dict.get("min_weight", 0.0)),
            leverage_limit=float(request_dict.get("leverage", 1.0)),
            objective_kwargs=request_dict.get("objective_kwargs", {}),
        )
        method = str(req.objective_kwargs.get("method", "")).lower()
        if method == "risk_parity":
            allocator = RiskParity()
        elif method == "vol_target":
            target_vol = req.objective_kwargs.get("target_vol", 0.15)
            allocator = VolatilityTarget()
        elif method == "kelly":
            allocator = Kelly()
        else:
            # Unknown / unspecified method falls back to equal-weight asset split.
            allocator = EqualWeight()
        target_vol = req.objective_kwargs.get("target_vol", 0.15)
        try:
            if isinstance(allocator, VolatilityTarget):
                weights = allocator.allocate(target_vol, expected_volatilities, cov)
            elif isinstance(allocator, EqualWeight):
                # Equal allocation returns asset weights only (cash reserve is tracked
                # separately at the allocation layer), so use total=1.0.
                weights = allocator.allocate(req.asset_names, total=1.0)
            else:
                weights = allocator.allocate(req.asset_names, total=1.0 - req.cash_reserve)
            if req.asset_names:
                weights = tuple(min(w, req.max_weight_per_asset) for w in weights)
            budget = tuple(weights)
            obj_val = req.objective_kwargs.get("objective_value", 0.0)
            return AllocationResult(weights=budget, objective_value=obj_val, status="SUCCESS")
        except Exception as e:
            return AllocationResult(weights=expected_returns[:n], objective_value=0.0, status="FAILED", message=str(e))

    def analyze(self, returns: tuple[float, ...], weights: tuple[float, ...]) -> dict[str, float]:
        """Run portfolio analytics on given returns and weights."""
        return PortfolioAnalytics.calculate_analytics(returns, weights)

    def risk_budget(self, weights: tuple[float, ...]) -> dict[str, Any]:
        """Compute risk contributions and analytics for a portfolio."""
        from backend.optimization.risk_budget import asset_risk_contributions, portfolio_risk
        vols = np.ones_like(np.array(weights))
        corr = np.eye(len(weights)).tolist()
        rc = asset_risk_contributions(weights, vols, corr)
        pr = portfolio_risk(weights, vols, corr)
        return {
            "portfolio_risk": pr,
            "risk_contributions": [{"asset": r.asset_name, "contribution": r.contribution, "marginal": r.marginal_contribution, "percentage": r.percentage_contribution} for r in rc],
        }
