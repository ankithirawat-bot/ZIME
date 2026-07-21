"""Stress testing.

Implements configurable stress scenarios for portfolio risk analysis.
"""

from __future__ import annotations

from typing import Any

from backend.risk.exceptions import StressTestError
from backend.risk.models import (
    RiskConfig,
    RiskPosition,
    StressScenario,
    StressTestResult,
)


def market_crash_stress(
    positions: tuple[RiskPosition, ...],
    config: RiskConfig,
    shock_size: float | None = None,
) -> StressTestResult:
    """Market crash stress test.

    Simulates a broad market decline.

    Args:
        positions: Portfolio positions.
        config:    Risk configuration.
        shock_size: Override shock size.

    Returns:
        StressTestResult with portfolio impact.
    """
    shock = shock_size if shock_size is not None else config.stress_shock_size

    position_impacts = {}
    total_impact = 0.0

    for pos in positions:
        impact = pos.weight * (-shock) * pos.beta
        position_impacts[pos.symbol] = impact
        total_impact += impact

    recovery_days = int(abs(total_impact) / 0.001) if total_impact < 0 else 0

    return StressTestResult(
        scenario=StressScenario.MARKET_CRASH,
        portfolio_impact=total_impact,
        position_impacts=position_impacts,
        recovery_days=recovery_days,
        description=f"Market crash with {shock:.0%} decline",
    )


def sector_crash_stress(
    positions: tuple[RiskPosition, ...],
    config: RiskConfig,
    target_sector: str = "Technology",
    shock_size: float | None = None,
) -> StressTestResult:
    """Sector crash stress test.

    Simulates a decline in a specific sector.

    Args:
        positions:    Portfolio positions.
        config:       Risk configuration.
        target_sector: Sector to stress.
        shock_size:   Override shock size.

    Returns:
        StressTestResult with portfolio impact.
    """
    shock = shock_size if shock_size is not None else config.stress_shock_size

    position_impacts = {}
    total_impact = 0.0

    for pos in positions:
        if pos.sector == target_sector:
            impact = pos.weight * (-shock)
            position_impacts[pos.symbol] = impact
            total_impact += impact
        else:
            correlation = 0.3
            impact = pos.weight * (-shock) * correlation
            position_impacts[pos.symbol] = impact
            total_impact += impact

    recovery_days = int(abs(total_impact) / 0.0005) if total_impact < 0 else 0

    return StressTestResult(
        scenario=StressScenario.SECTOR_CRASH,
        portfolio_impact=total_impact,
        position_impacts=position_impacts,
        recovery_days=recovery_days,
        description=f"{target_sector} sector crash with {shock:.0%} decline",
    )


def interest_rate_shock_stress(
    positions: tuple[RiskPosition, ...],
    config: RiskConfig,
    rate_change: float = 0.02,
) -> StressTestResult:
    """Interest rate shock stress test.

    Simulates a sudden interest rate change.

    Args:
        positions:   Portfolio positions.
        config:      Risk configuration.
        rate_change: Interest rate change (positive = increase).

    Returns:
        StressTestResult with portfolio impact.
    """
    position_impacts = {}
    total_impact = 0.0

    for pos in positions:
        duration = 5.0
        impact = pos.weight * (-duration * rate_change)
        position_impacts[pos.symbol] = impact
        total_impact += impact

    recovery_days = int(abs(total_impact) / 0.0002) if total_impact < 0 else 0

    return StressTestResult(
        scenario=StressScenario.INTEREST_RATE_SHOCK,
        portfolio_impact=total_impact,
        position_impacts=position_impacts,
        recovery_days=recovery_days,
        description=f"Interest rate shock of {rate_change:+.2%}",
    )


def volatility_expansion_stress(
    positions: tuple[RiskPosition, ...],
    config: RiskConfig,
    vol_multiplier: float = 2.0,
) -> StressTestResult:
    """Volatility expansion stress test.

    Simulates a sudden increase in volatility.

    Args:
        positions:     Portfolio positions.
        config:        Risk configuration.
        vol_multiplier: Volatility multiplier.

    Returns:
        StressTestResult with portfolio impact.
    """
    position_impacts = {}
    total_impact = 0.0

    for pos in positions:
        vol_impact = pos.volatility * (vol_multiplier - 1)
        impact = pos.weight * (-vol_impact * 0.5)
        position_impacts[pos.symbol] = impact
        total_impact += impact

    recovery_days = int(abs(total_impact) / 0.0003) if total_impact < 0 else 0

    return StressTestResult(
        scenario=StressScenario.VOLATILITY_EXPANSION,
        portfolio_impact=total_impact,
        position_impacts=position_impacts,
        recovery_days=recovery_days,
        description=f"Volatility expansion {vol_multiplier}x",
    )


def liquidity_shock_stress(
    positions: tuple[RiskPosition, ...],
    config: RiskConfig,
    liquidity_discount: float = 0.10,
) -> StressTestResult:
    """Liquidity shock stress test.

    Simulates a liquidity crisis with bid-ask spread widening.

    Args:
        positions:         Portfolio positions.
        config:            Risk configuration.
        liquidity_discount: Liquidity discount.

    Returns:
        StressTestResult with portfolio impact.
    """
    position_impacts = {}
    total_impact = 0.0

    for pos in positions:
        impact = pos.weight * (-liquidity_discount)
        position_impacts[pos.symbol] = impact
        total_impact += impact

    recovery_days = int(abs(total_impact) / 0.001) if total_impact < 0 else 0

    return StressTestResult(
        scenario=StressScenario.LIQUIDITY_SHOCK,
        portfolio_impact=total_impact,
        position_impacts=position_impacts,
        recovery_days=recovery_days,
        description=f"Liquidity shock with {liquidity_discount:.0%} discount",
    )


def custom_stress(
    positions: tuple[RiskPosition, ...],
    config: RiskConfig,
    shocks: dict[str, float],
) -> StressTestResult:
    """Custom stress test.

    Applies user-defined shocks to positions.

    Args:
        positions: Portfolio positions.
        config:    Risk configuration.
        shocks:    Dictionary of symbol -> shock size.

    Returns:
        StressTestResult with portfolio impact.
    """
    position_impacts = {}
    total_impact = 0.0

    for pos in positions:
        shock = shocks.get(pos.symbol, 0.0)
        impact = pos.weight * (-shock)
        position_impacts[pos.symbol] = impact
        total_impact += impact

    recovery_days = int(abs(total_impact) / 0.001) if total_impact < 0 else 0

    return StressTestResult(
        scenario=StressScenario.CUSTOM,
        portfolio_impact=total_impact,
        position_impacts=position_impacts,
        recovery_days=recovery_days,
        description=f"Custom stress with {len(shocks)} positions shocked",
    )


def run_stress_test(
    positions: tuple[RiskPosition, ...],
    config: RiskConfig,
    scenario: StressScenario,
    params: dict[str, Any] | None = None,
) -> StressTestResult:
    """Run a stress test.

    Args:
        positions: Portfolio positions.
        config:    Risk configuration.
        scenario:  Stress scenario.
        params:    Additional parameters.

    Returns:
        StressTestResult with portfolio impact.
    """
    params = params or {}

    if scenario == StressScenario.MARKET_CRASH:
        return market_crash_stress(positions, config, params.get("shock_size"))
    elif scenario == StressScenario.SECTOR_CRASH:
        return sector_crash_stress(
            positions,
            config,
            params.get("target_sector", "Technology"),
            params.get("shock_size"),
        )
    elif scenario == StressScenario.INTEREST_RATE_SHOCK:
        return interest_rate_shock_stress(
            positions, config, params.get("rate_change", 0.02)
        )
    elif scenario == StressScenario.VOLATILITY_EXPANSION:
        return volatility_expansion_stress(
            positions, config, params.get("vol_multiplier", 2.0)
        )
    elif scenario == StressScenario.LIQUIDITY_SHOCK:
        return liquidity_shock_stress(
            positions, config, params.get("liquidity_discount", 0.10)
        )
    elif scenario == StressScenario.CUSTOM:
        return custom_stress(positions, config, params.get("shocks", {}))
    else:
        raise StressTestError(f"Unknown scenario: {scenario}")


def run_all_stress_tests(
    positions: tuple[RiskPosition, ...],
    config: RiskConfig,
) -> tuple[StressTestResult, ...]:
    """Run all standard stress tests.

    Args:
        positions: Portfolio positions.
        config:    Risk configuration.

    Returns:
        Tuple of StressTestResult for each scenario.
    """
    results = []

    for scenario in [
        StressScenario.MARKET_CRASH,
        StressScenario.SECTOR_CRASH,
        StressScenario.INTEREST_RATE_SHOCK,
        StressScenario.VOLATILITY_EXPANSION,
        StressScenario.LIQUIDITY_SHOCK,
    ]:
        try:
            result = run_stress_test(positions, config, scenario)
            results.append(result)
        except Exception:
            continue

    return tuple(results)
