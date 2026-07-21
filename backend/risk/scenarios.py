"""Scenario analysis.

Implements single-factor, multi-factor, and custom scenario analysis.
"""

from __future__ import annotations

from typing import Any

from backend.risk.exceptions import ScenarioNotFoundError
from backend.risk.models import (
    RiskConfig,
    RiskPosition,
    ScenarioResult,
)


class ScenarioRegistry:
    """Registry for scenario strategies."""

    def __init__(self) -> None:
        self._scenarios: dict[str, callable] = {}

    def register(self, name: str, fn: callable) -> None:
        """Register a scenario.

        Args:
            name: Scenario name.
            fn:   Scenario function.
        """
        self._scenarios[name] = fn

    def get(self, name: str) -> callable:
        """Get a scenario.

        Args:
            name: Scenario name.

        Returns:
            Scenario function.

        Raises:
            ScenarioNotFoundError: If scenario not found.
        """
        if name not in self._scenarios:
            raise ScenarioNotFoundError(name)
        return self._scenarios[name]

    def list_scenarios(self) -> tuple[str, ...]:
        """List registered scenarios.

        Returns:
            Tuple of scenario names.
        """
        return tuple(self._scenarios.keys())


def single_factor_scenario(
    positions: tuple[RiskPosition, ...],
    config: RiskConfig,
    factor: str,
    shock: float,
) -> ScenarioResult:
    """Single-factor scenario analysis.

    Applies a shock to a single factor.

    Args:
        positions: Portfolio positions.
        config:    Risk configuration.
        factor:    Factor to shock.
        shock:     Factor shock size.

    Returns:
        ScenarioResult with scenario analysis.
    """
    position_returns = {}
    total_return = 0.0

    for pos in positions:
        factor_loading = pos.beta if factor == "market" else 1.0
        ret = shock * factor_loading
        position_returns[pos.symbol] = ret
        total_return += pos.weight * ret

    return ScenarioResult(
        scenario_name=f"Single Factor: {factor}",
        factors={factor: shock},
        portfolio_return=total_return,
        position_returns=position_returns,
    )


def multi_factor_scenario(
    positions: tuple[RiskPosition, ...],
    config: RiskConfig,
    factors: dict[str, float],
) -> ScenarioResult:
    """Multi-factor scenario analysis.

    Applies shocks to multiple factors.

    Args:
        positions: Portfolio positions.
        config:    Risk configuration.
        factors:   Dictionary of factor -> shock.

    Returns:
        ScenarioResult with scenario analysis.
    """
    position_returns = {}
    total_return = 0.0

    for pos in positions:
        ret = 0.0
        for factor, shock in factors.items():
            factor_loading = pos.beta if factor == "market" else 1.0
            ret += shock * factor_loading * 0.3
        position_returns[pos.symbol] = ret
        total_return += pos.weight * ret

    return ScenarioResult(
        scenario_name=f"Multi Factor: {', '.join(factors.keys())}",
        factors=factors,
        portfolio_return=total_return,
        position_returns=position_returns,
    )


def market_crash_scenario(
    positions: tuple[RiskPosition, ...],
    config: RiskConfig,
) -> ScenarioResult:
    """Market crash scenario.

    Simulates a 2008-style market crash.

    Args:
        positions: Portfolio positions.
        config:    Risk configuration.

    Returns:
        ScenarioResult with scenario analysis.
    """
    return single_factor_scenario(
        positions, config, "market", -0.40
    )


def interest_rate_rise_scenario(
    positions: tuple[RiskPosition, ...],
    config: RiskConfig,
) -> ScenarioResult:
    """Interest rate rise scenario.

    Simulates a sharp interest rate increase.

    Args:
        positions: Portfolio positions.
        config:    Risk configuration.

    Returns:
        ScenarioResult with scenario analysis.
    """
    factors = {
        "interest_rate": 0.03,
        "market": -0.10,
    }
    return multi_factor_scenario(positions, config, factors)


def inflation_surge_scenario(
    positions: tuple[RiskPosition, ...],
    config: RiskConfig,
) -> ScenarioResult:
    """Inflation surge scenario.

    Simulates a sudden inflation increase.

    Args:
        positions: Portfolio positions.
        config:    Risk configuration.

    Returns:
        ScenarioResult with scenario analysis.
    """
    factors = {
        "inflation": 0.05,
        "interest_rate": 0.02,
        "market": -0.15,
    }
    return multi_factor_scenario(positions, config, factors)


def custom_scenario(
    positions: tuple[RiskPosition, ...],
    config: RiskConfig,
    factors: dict[str, float],
    name: str = "Custom",
) -> ScenarioResult:
    """Custom scenario analysis.

    Args:
        positions: Portfolio positions.
        config:    Risk configuration.
        factors:   Factor shocks.
        name:      Scenario name.

    Returns:
        ScenarioResult with scenario analysis.
    """
    return multi_factor_scenario(positions, config, factors)


def build_default_registry() -> ScenarioRegistry:
    """Build default scenario registry.

    Returns:
        ScenarioRegistry with built-in scenarios.
    """
    registry = ScenarioRegistry()
    registry.register("market_crash", market_crash_scenario)
    registry.register("interest_rate_rise", interest_rate_rise_scenario)
    registry.register("inflation_surge", inflation_surge_scenario)
    return registry


def run_scenario(
    positions: tuple[RiskPosition, ...],
    config: RiskConfig,
    scenario_name: str,
    params: dict[str, Any] | None = None,
    registry: ScenarioRegistry | None = None,
) -> ScenarioResult:
    """Run a scenario analysis.

    Args:
        positions:     Portfolio positions.
        config:        Risk configuration.
        scenario_name: Scenario name.
        params:        Additional parameters.
        registry:      Scenario registry.

    Returns:
        ScenarioResult with scenario analysis.
    """
    if registry is None:
        registry = build_default_registry()

    try:
        scenario_fn = registry.get(scenario_name)
        return scenario_fn(positions, config)
    except ScenarioNotFoundError:
        if params and "factors" in params:
            return custom_scenario(
                positions, config, params["factors"], scenario_name
            )
        raise


def run_all_scenarios(
    positions: tuple[RiskPosition, ...],
    config: RiskConfig,
    registry: ScenarioRegistry | None = None,
) -> tuple[ScenarioResult, ...]:
    """Run all registered scenarios.

    Args:
        positions: Portfolio positions.
        config:    Risk configuration.
        registry:  Scenario registry.

    Returns:
        Tuple of ScenarioResult for each scenario.
    """
    if registry is None:
        registry = build_default_registry()

    results = []
    for name in registry.list_scenarios():
        try:
            result = run_scenario(positions, config, name, registry=registry)
            results.append(result)
        except Exception:
            continue

    return tuple(results)
