"""Risk engine.

Core risk management engine for portfolio risk analysis and limit monitoring.
"""

from __future__ import annotations

import math

from backend.risk.exposure import calculate_exposure
from backend.risk.models import (
    RiskConfig,
    RiskMetrics,
    RiskPosition,
)
from backend.risk.scenarios import ScenarioRegistry, build_default_registry, run_all_scenarios
from backend.risk.stress import run_all_stress_tests
from backend.risk.var import calculate_var


class RiskEngine:
    """Core risk management engine.

    Performs portfolio risk analysis, exposure measurement, and limit monitoring.
    """

    def __init__(
        self,
        scenario_registry: ScenarioRegistry | None = None,
    ) -> None:
        """Initialize the engine.

        Args:
            scenario_registry: Registry of scenarios.
        """
        self._scenario_registry = scenario_registry or build_default_registry()
        self._config: RiskConfig | None = None

    @property
    def config(self) -> RiskConfig | None:
        """Current configuration."""
        return self._config

    @property
    def scenario_registry(self) -> ScenarioRegistry:
        """Access the scenario registry."""
        return self._scenario_registry

    def evaluate(
        self,
        positions: tuple[RiskPosition, ...],
        config: RiskConfig,
    ) -> RiskMetrics:
        """Evaluate portfolio risk.

        Args:
            positions: Portfolio positions.
            config:    Risk configuration.

        Returns:
            RiskMetrics with all risk metrics.
        """
        self._config = config

        if not positions:
            return RiskMetrics()

        exposure = calculate_exposure(positions, config)
        var_result = calculate_var(positions, config)
        stress_tests = run_all_stress_tests(positions, config)
        scenarios = run_all_scenarios(
            positions, config, self._scenario_registry
        )

        returns = []
        for pos in positions:
            if pos.return_series:
                returns.extend(pos.return_series)

        volatility = 0.0
        if returns and len(returns) > 1:
            mean_ret = sum(returns) / len(returns)
            variance = sum((r - mean_ret) ** 2 for r in returns) / (len(returns) - 1)
            volatility = math.sqrt(variance) if variance > 0 else 0.0

        max_dd = 0.0
        if returns:
            peak = 1.0
            equity = 1.0
            for r in returns:
                equity *= 1 + r
                if equity > peak:
                    peak = equity
                dd = (peak - equity) / peak if peak > 0 else 0.0
                max_dd = max(max_dd, dd)

        sharpe = 0.0
        if volatility > 0:
            mean_ret = sum(returns) / len(returns) if returns else 0.0
            excess = mean_ret - (config.risk_free_rate / 252)
            sharpe = (excess / volatility) * math.sqrt(252)

        sortino = 0.0
        if returns:
            downside = [r for r in returns if r < 0]
            if downside:
                downside_var = sum(r**2 for r in downside) / len(downside)
                downside_std = math.sqrt(downside_var)
                if downside_std > 0:
                    mean_ret = sum(returns) / len(returns)
                    excess = mean_ret - (config.risk_free_rate / 252)
                    sortino = (excess / downside_std) * math.sqrt(252)

        return RiskMetrics(
            exposure=exposure,
            var=var_result,
            stress_tests=stress_tests,
            scenarios=scenarios,
            volatility=volatility,
            sharpe_ratio=sharpe,
            sortino_ratio=sortino,
            maximum_drawdown=max_dd,
        )

    def evaluate_portfolio(
        self,
        weights: dict[str, float],
        returns_data: dict[str, list[float]],
        config: RiskConfig,
        sectors: dict[str, str] | None = None,
    ) -> RiskMetrics:
        """Evaluate portfolio risk from weights and returns.

        Args:
            weights:      Position weights.
            returns_data: Historical returns by symbol.
            config:       Risk configuration.
            sectors:      Sector mapping.

        Returns:
            RiskMetrics with all risk metrics.
        """
        positions = []
        for symbol, weight in weights.items():
            returns = returns_data.get(symbol, [])
            sector = sectors.get(symbol, "") if sectors else ""
            vol = 0.0
            if returns and len(returns) > 1:
                mean = sum(returns) / len(returns)
                var = sum((r - mean) ** 2 for r in returns) / (len(returns) - 1)
                vol = math.sqrt(var) if var > 0 else 0.0

            positions.append(
                RiskPosition(
                    symbol=symbol,
                    weight=weight,
                    return_series=tuple(returns),
                    sector=sector,
                    volatility=vol,
                )
            )

        return self.evaluate(tuple(positions), config)

    def evaluate_backtest(
        self,
        equity_curve: list[float],
        config: RiskConfig,
    ) -> RiskMetrics:
        """Evaluate risk from backtest equity curve.

        Args:
            equity_curve: Equity curve values.
            config:       Risk configuration.

        Returns:
            RiskMetrics with risk metrics.
        """
        if not equity_curve or len(equity_curve) < 2:
            return RiskMetrics()

        returns = []
        for i in range(1, len(equity_curve)):
            if equity_curve[i - 1] > 0:
                returns.append(
                    (equity_curve[i] - equity_curve[i - 1]) / equity_curve[i - 1]
                )

        position = RiskPosition(
            symbol="Portfolio",
            weight=1.0,
            return_series=tuple(returns),
        )

        return self.evaluate((position,), config)

    def evaluate_strategy(
        self,
        signals: dict[str, float],
        returns_data: dict[str, list[float]],
        config: RiskConfig,
    ) -> RiskMetrics:
        """Evaluate risk from strategy signals.

        Args:
            signals:      Strategy signals (symbol -> signal strength).
            returns_data: Historical returns by symbol.
            config:       Risk configuration.

        Returns:
            RiskMetrics with risk metrics.
        """
        total_signal = sum(abs(v) for v in signals.values())
        if total_signal <= 0:
            return RiskMetrics()

        weights = {s: v / total_signal for s, v in signals.items()}
        return self.evaluate_portfolio(weights, returns_data, config)

    def check_limits(
        self,
        metrics: RiskMetrics,
        config: RiskConfig,
    ) -> tuple[str, ...]:
        """Check risk limits.

        Args:
            metrics: Risk metrics.
            config:  Risk configuration.

        Returns:
            Tuple of limit violation messages.
        """
        violations = []

        if metrics.var.var > config.maximum_var:
            violations.append(
                f"VaR {metrics.var.var:.2%} exceeds limit {config.maximum_var:.2%}"
            )

        if metrics.maximum_drawdown > config.maximum_drawdown:
            violations.append(
                f"Max drawdown {metrics.maximum_drawdown:.2%} exceeds limit {config.maximum_drawdown:.2%}"
            )

        if metrics.volatility > config.maximum_volatility:
            violations.append(
                f"Volatility {metrics.volatility:.2%} exceeds limit {config.maximum_volatility:.2%}"
            )

        if metrics.exposure.concentration_index > config.maximum_concentration:
            violations.append(
                f"Concentration {metrics.exposure.concentration_index:.4f} exceeds limit {config.maximum_concentration:.4f}"
            )

        for sector, exposure in metrics.exposure.sector_exposure.items():
            if abs(exposure) > config.maximum_sector_exposure:
                violations.append(
                    f"Sector {sector} exposure {exposure:.2%} exceeds limit {config.maximum_sector_exposure:.2%}"
                )

        for symbol, exposure in metrics.exposure.position_exposure.items():
            if abs(exposure) > config.maximum_position_size:
                violations.append(
                    f"Position {symbol} exposure {exposure:.2%} exceeds limit {config.maximum_position_size:.2%}"
                )

        return tuple(violations)

    def generate_warnings(
        self,
        metrics: RiskMetrics,
        config: RiskConfig,
    ) -> tuple[str, ...]:
        """Generate risk warnings.

        Args:
            metrics: Risk metrics.
            config:  Risk configuration.

        Returns:
            Tuple of warning messages.
        """
        warnings = []

        if metrics.var.var > config.maximum_var * 0.8:
            warnings.append(f"VaR approaching limit: {metrics.var.var:.2%}")

        if metrics.maximum_drawdown > config.maximum_drawdown * 0.8:
            warnings.append(
                f"Max drawdown approaching limit: {metrics.maximum_drawdown:.2%}"
            )

        if metrics.volatility > config.maximum_volatility * 0.8:
            warnings.append(f"Volatility approaching limit: {metrics.volatility:.2%}")

        if metrics.exposure.concentration_index > 0.15:
            warnings.append("Portfolio concentration is high")

        for stress in metrics.stress_tests:
            if stress.portfolio_impact < -0.10:
                warnings.append(
                    f"Stress test {stress.scenario}: {stress.portfolio_impact:.2%} impact"
                )

        return tuple(warnings)

    def generate_actions(
        self,
        metrics: RiskMetrics,
        config: RiskConfig,
        violations: tuple[str, ...],
    ) -> tuple[str, ...]:
        """Generate recommended actions.

        Args:
            metrics:    Risk metrics.
            config:     Risk configuration.
            violations: Limit violations.

        Returns:
            Tuple of recommended actions.
        """
        actions = []

        if violations:
            actions.append("Review and reduce positions to comply with limits")

        if metrics.var.var > config.maximum_var:
            actions.append("Reduce portfolio VaR by hedging or reducing positions")

        if metrics.maximum_drawdown > config.maximum_drawdown:
            actions.append("Implement stop-loss or reduce exposure")

        if metrics.exposure.concentration_index > config.maximum_concentration:
            actions.append("Diversify portfolio to reduce concentration")

        for sector, exposure in metrics.exposure.sector_exposure.items():
            if abs(exposure) > config.maximum_sector_exposure:
                actions.append(f"Reduce {sector} sector exposure")

        return tuple(actions)
