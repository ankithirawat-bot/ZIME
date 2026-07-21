"""Sizing engine.

Core position sizing engine for calculating optimal position sizes based on
account size, portfolio constraints, volatility, and risk management rules.
"""

from __future__ import annotations

from typing import Any

from backend.sizing.constraints import SizingConstraints
from backend.sizing.exceptions import (
    MethodNotFoundError,
)
from backend.sizing.methods import (
    ATRPositionSizingMethod,
    EqualRiskContributionMethod,
    FixedFractionalMethod,
    FixedRiskPerTradeMethod,
    FixedSharesMethod,
    FixedValueMethod,
    FractionalKellyMethod,
    KellyCriterionMethod,
    PercentageOfEquityMethod,
    VolatilityTargetingMethod,
)
from backend.sizing.models import (
    AllocationResult,
    PositionRequest,
    PositionSizing,
    SizingConfig,
    SizingMetrics,
    SizingStatistics,
)
from backend.sizing.optimizer import SizingOptimizer


class SizingEngine:
    """Core position sizing engine.

    Calculates optimal position sizes, validates constraints, and produces
    allocation results for single positions and multi-position portfolios.
    Optionally integrates with portfolio, risk, and strategy engines.
    """

    def __init__(
        self,
        config: SizingConfig | None = None,
        optimizer: SizingOptimizer | None = None,
        portfolio_engine: Any | None = None,
        risk_engine: Any | None = None,
        strategy_engine: Any | None = None,
    ) -> None:
        """Initialize the engine.

        Args:
            config:           Sizing configuration (defaults created).
            optimizer:        Sizing optimizer (defaults created).
            portfolio_engine: Optional portfolio engine for integration.
            risk_engine:      Optional risk engine for integration.
            strategy_engine:  Optional strategy engine for integration.
        """
        self._config = config or SizingConfig()
        self._optimizer = optimizer or SizingOptimizer()
        self._portfolio_engine = portfolio_engine
        self._risk_engine = risk_engine
        self._strategy_engine = strategy_engine
        self._methods: dict[str, Any] = {}
        self._total_calculations = 0
        self._register_default_methods()

    @property
    def config(self) -> SizingConfig:
        """Current configuration."""
        return self._config

    @property
    def methods(self) -> dict[str, Any]:
        """Registered sizing methods."""
        return dict(self._methods)

    def _register_default_methods(self) -> None:
        """Register default sizing methods."""
        default_methods = [
            FixedSharesMethod(),
            FixedValueMethod(),
            FixedFractionalMethod(),
            FixedRiskPerTradeMethod(),
            PercentageOfEquityMethod(),
            KellyCriterionMethod(),
            FractionalKellyMethod(),
            ATRPositionSizingMethod(),
            VolatilityTargetingMethod(),
            EqualRiskContributionMethod(),
        ]
        for method in default_methods:
            self._methods[method.name] = method

    def register_method(self, name: str, method: Any) -> None:
        """Register a custom sizing method.

        Args:
            name:   Method name.
            method: Method instance.
        """
        self._methods[name] = method

    def _get_method(self, name: str | None = None) -> Any:
        """Get a sizing method by name."""
        method_name = name or self._config.method
        if method_name not in self._methods:
            raise MethodNotFoundError(method_name)
        return self._methods[method_name]

    def calculate_position_size(
        self,
        request: PositionRequest,
        method_name: str | None = None,
    ) -> PositionSizing:
        """Calculate optimal position size for a single position.

        Args:
            request:     Position request with market data.
            method_name: Sizing method to use (default from config).

        Returns:
            PositionSizing with calculated size.
        """
        method = self._get_method(method_name)
        self._total_calculations += 1
        return method.calculate(request, self._config)

    def calculate_portfolio_sizes(
        self,
        requests: tuple[PositionRequest, ...],
        method_name: str | None = None,
    ) -> AllocationResult:
        """Calculate optimal position sizes for a portfolio.

        Args:
            requests:    Position requests.
            method_name: Sizing method to use (default from config).

        Returns:
            AllocationResult with sized positions.
        """
        if not requests:
            return AllocationResult()

        self._total_calculations += len(requests)
        method = self._get_method(method_name)

        sizings_list: list[PositionSizing] = []
        for request in requests:
            sizing = method.calculate(request, self._config)
            sizings_list.append(sizing)

        available_cash = self._compute_available_cash(requests)

        return self._optimizer.optimize(
            tuple(sizings_list),
            self._config,
            available_cash,
        )

    def rebalance_sizes(
        self,
        current_allocations: tuple[PositionSizing, ...],
        target_allocations: tuple[PositionSizing, ...],
        config: SizingConfig | None = None,
    ) -> AllocationResult:
        """Calculate rebalancing sizes from current to target.

        Args:
            current_allocations: Current position sizes.
            target_allocations:  Target position sizes.
            config:              Sizing configuration (default from engine).

        Returns:
            AllocationResult with rebalanced positions.
        """
        cfg = config or self._config
        if not target_allocations:
            return AllocationResult(
                cash_remaining=cfg.default_account_size,
                cash_reserve=cfg.default_account_size * cfg.cash_reserve,
            )

        current_map = {s.symbol: s for s in current_allocations}
        rebalanced: list[PositionSizing] = []
        warnings_list: list[str] = []

        for target in target_allocations:
            current = current_map.get(target.symbol)
            if current is None:
                rebalanced.append(target)
                continue

            diff_value = target.value - current.value
            diff_shares = target.shares - current.shares

            if abs(diff_shares) < 0.001:
                continue

            rebalanced.append(
                PositionSizing(
                    symbol=target.symbol,
                    method=target.method,
                    shares=diff_shares,
                    value=diff_value,
                    weight=target.weight,
                    price=target.price,
                    risk_amount=target.risk_amount - current.risk_amount,
                    risk_percentage=target.risk_percentage,
                    confidence=target.confidence,
                    reason=f"Rebalance: {current.shares:.0f} -> {target.shares:.0f}",
                )
            )

        total_value = sum(s.value for s in rebalanced)
        total_exposure = total_value / cfg.default_account_size if cfg.default_account_size > 0 else 0.0
        cash_remaining = cfg.default_account_size - total_value

        if total_exposure > cfg.max_portfolio_exposure:
            warnings_list.append("Rebalanced portfolio exceeds exposure limit")

        return AllocationResult(
            positions=tuple(rebalanced),
            total_value=total_value,
            total_risk=sum(s.risk_amount for s in rebalanced),
            cash_remaining=max(0.0, cash_remaining),
            cash_reserve=cfg.default_account_size * cfg.cash_reserve,
            exposure=total_exposure,
            warnings=tuple(warnings_list),
        )

    def validate_sizes(
        self,
        allocation: AllocationResult,
        config: SizingConfig | None = None,
    ) -> tuple[str, ...]:
        """Validate position sizes against constraints.

        Args:
            allocation: Allocation result to validate.
            config:     Sizing configuration (default from engine).

        Returns:
            Tuple of constraint violation messages.
        """
        cfg = config or self._config
        violations: list[str] = []

        portfolio_results = SizingConstraints.validate_allocation(allocation, cfg)
        for result in portfolio_results:
            if not result.valid:
                violations.append(result.message)

        for sizing in allocation.positions:
            pos_results = SizingConstraints.validate_position(
                sizing, {}, "", cfg
            )
            for result in pos_results:
                if not result.valid:
                    violations.append(result.message)

        return tuple(violations)

    def optimize_allocations(
        self,
        sizings: tuple[PositionSizing, ...],
        config: SizingConfig | None = None,
        available_cash: float | None = None,
    ) -> AllocationResult:
        """Optimize position allocations against constraints.

        Args:
            sizings:        Position sizings to optimize.
            config:         Sizing configuration (default from engine).
            available_cash: Available cash (default from config).

        Returns:
            AllocationResult with optimized positions.
        """
        cfg = config or self._config
        cash = available_cash if available_cash is not None else cfg.default_account_size

        return self._optimizer.optimize(sizings, cfg, cash)

    def compute_metrics(
        self,
        allocation: AllocationResult,
        config: SizingConfig | None = None,
    ) -> SizingMetrics:
        """Compute sizing metrics from an allocation.

        Args:
            allocation: Allocation result.
            config:     Sizing configuration (default from engine).

        Returns:
            SizingMetrics with summary statistics.
        """
        cfg = config or self._config
        positions = allocation.positions
        n = len(positions)

        if n == 0:
            return SizingMetrics(
                cash_ratio=allocation.cash_remaining / cfg.default_account_size if cfg.default_account_size > 0 else 1.0,
            )

        weights = [p.weight for p in positions]
        largest = max(weights) if weights else 0.0
        smallest = min(weights) if weights else 0.0
        average = sum(weights) / n if n > 0 else 0.0

        hhi = sum(w**2 for w in weights)

        sector_exp: dict[str, float] = {}
        for p in positions:
            pass

        return SizingMetrics(
            total_positions=n,
            total_exposure=allocation.exposure,
            largest_position=largest,
            smallest_position=smallest,
            average_position=average,
            concentration=hhi,
            cash_ratio=allocation.cash_remaining / cfg.default_account_size if cfg.default_account_size > 0 else 0.0,
            leverage=1.0,
            sector_exposure=sector_exp,
        )

    def generate_statistics(
        self,
        elapsed: float,
        violations: tuple[str, ...] = (),
        warnings: tuple[str, ...] = (),
    ) -> SizingStatistics:
        """Generate sizing statistics.

        Args:
            elapsed:    Elapsed time in seconds.
            violations: Constraint violations.
            warnings:   Sizing warnings.

        Returns:
            SizingStatistics with calculation stats.
        """
        return SizingStatistics(
            total_calculations=self._total_calculations,
            constraint_violations=len(violations),
            violations=violations,
            warnings=warnings,
            elapsed_seconds=elapsed,
        )

    def _compute_available_cash(
        self,
        requests: tuple[PositionRequest, ...],
    ) -> float:
        """Compute available cash from requests."""
        if not requests:
            return self._config.default_account_size
        cash_values = [r.available_cash for r in requests if r.available_cash > 0]
        return cash_values[0] if cash_values else self._config.default_account_size
