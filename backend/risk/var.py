"""Value at Risk calculations.

Implements Historical, Parametric, and Monte Carlo VaR methods.
"""

from __future__ import annotations

import math
import random

from backend.risk.exceptions import VaRCalculationError
from backend.risk.models import (
    ConfidenceLevel,
    RiskConfig,
    RiskPosition,
    VaRMethod,
    VaRResult,
)


def historical_var(
    returns: list[float],
    confidence_level: ConfidenceLevel,
    lookback_period: int,
) -> VaRResult:
    """Calculate VaR using historical simulation.

    Args:
        returns:          Historical return series.
        confidence_level: Confidence level.
        lookback_period:  Lookback period.

    Returns:
        VaRResult with VaR metrics.
    """
    if not returns:
        return VaRResult(
            method=VaRMethod.HISTORICAL,
            confidence_level=confidence_level,
            lookback_period=lookback_period,
        )

    sorted_returns = sorted(returns)
    alpha = 1 - (int(confidence_level.value) / 100)
    index = int(alpha * len(sorted_returns))
    var = -sorted_returns[index]

    tail = sorted_returns[: index + 1]
    cvar = -sum(tail) / len(tail) if tail else 0.0

    worst_loss = -min(sorted_returns) if sorted_returns else 0.0

    tail_mean = sum(tail) / len(tail) if tail else 0.0
    tail_var = sum((r - tail_mean) ** 2 for r in tail) / len(tail) if tail else 0.0
    tail_std = math.sqrt(tail_var) if tail_var > 0 else 0.0

    return VaRResult(
        method=VaRMethod.HISTORICAL,
        confidence_level=confidence_level,
        var=var,
        cvar=cvar,
        worst_loss=worst_loss,
        tail_mean=-tail_mean,
        tail_std=tail_std,
        lookback_period=lookback_period,
    )


def parametric_var(
    returns: list[float],
    confidence_level: ConfidenceLevel,
    lookback_period: int,
) -> VaRResult:
    """Calculate VaR using parametric (variance-covariance) method.

    Args:
        returns:          Historical return series.
        confidence_level: Confidence level.
        lookback_period:  Lookback period.

    Returns:
        VaRResult with VaR metrics.
    """
    if not returns or len(returns) < 2:
        return VaRResult(
            method=VaRMethod.PARAMETRIC,
            confidence_level=confidence_level,
            lookback_period=lookback_period,
        )

    n = len(returns)
    mean_return = sum(returns) / n
    variance = sum((r - mean_return) ** 2 for r in returns) / (n - 1)
    std_dev = math.sqrt(variance) if variance > 0 else 0.0001

    z_scores = {ConfidenceLevel.P95: 1.645, ConfidenceLevel.P99: 2.326}
    z = z_scores.get(confidence_level, 1.645)

    var = -(mean_return - z * std_dev)

    tail_threshold = mean_return - z * std_dev
    tail = [r for r in returns if r <= tail_threshold]
    cvar = -sum(tail) / len(tail) if tail else var

    worst_loss = -min(returns) if returns else 0.0

    tail_mean = sum(tail) / len(tail) if tail else 0.0
    tail_var = sum((r - tail_mean) ** 2 for r in tail) / len(tail) if tail else 0.0
    tail_std = math.sqrt(tail_var) if tail_var > 0 else 0.0

    return VaRResult(
        method=VaRMethod.PARAMETRIC,
        confidence_level=confidence_level,
        var=var,
        cvar=cvar,
        worst_loss=worst_loss,
        tail_mean=-tail_mean,
        tail_std=tail_std,
        lookback_period=lookback_period,
    )


def monte_carlo_var(
    returns: list[float],
    confidence_level: ConfidenceLevel,
    lookback_period: int,
    num_simulations: int = 10000,
) -> VaRResult:
    """Calculate VaR using Monte Carlo simulation.

    Args:
        returns:          Historical return series.
        confidence_level: Confidence level.
        lookback_period:  Lookback period.
        num_simulations:  Number of simulations.

    Returns:
        VaRResult with VaR metrics.
    """
    if not returns or len(returns) < 2:
        return VaRResult(
            method=VaRMethod.MONTE_CARLO,
            confidence_level=confidence_level,
            lookback_period=lookback_period,
        )

    n = len(returns)
    mean_return = sum(returns) / n
    variance = sum((r - mean_return) ** 2 for r in returns) / (n - 1)
    std_dev = math.sqrt(variance) if variance > 0 else 0.0001

    simulated = []
    for _ in range(num_simulations):
        r = random.gauss(mean_return, std_dev)
        simulated.append(r)

    sorted_sim = sorted(simulated)
    alpha = 1 - (int(confidence_level.value) / 100)
    index = int(alpha * len(sorted_sim))
    var = -sorted_sim[index]

    tail = sorted_sim[: index + 1]
    cvar = -sum(tail) / len(tail) if tail else 0.0

    worst_loss = -min(sorted_sim) if sorted_sim else 0.0

    tail_mean = sum(tail) / len(tail) if tail else 0.0
    tail_var = sum((r - tail_mean) ** 2 for r in tail) / len(tail) if tail else 0.0
    tail_std = math.sqrt(tail_var) if tail_var > 0 else 0.0

    return VaRResult(
        method=VaRMethod.MONTE_CARLO,
        confidence_level=confidence_level,
        var=var,
        cvar=cvar,
        worst_loss=worst_loss,
        tail_mean=-tail_mean,
        tail_std=tail_std,
        lookback_period=lookback_period,
    )


def calculate_var(
    positions: tuple[RiskPosition, ...],
    config: RiskConfig,
) -> VaRResult:
    """Calculate VaR for the portfolio.

    Args:
        positions: Portfolio positions.
        config:    Risk configuration.

    Returns:
        VaRResult with VaR metrics.
    """
    if not positions:
        return VaRResult(
            method=config.var_method,
            confidence_level=config.confidence_level,
            lookback_period=config.lookback_period,
        )

    portfolio_returns = _aggregate_portfolio_returns(positions)

    if not portfolio_returns:
        return VaRResult(
            method=config.var_method,
            confidence_level=config.confidence_level,
            lookback_period=config.lookback_period,
        )

    actual_lookback = min(len(portfolio_returns), config.lookback_period)

    if config.var_method == VaRMethod.HISTORICAL:
        return historical_var(
            portfolio_returns, config.confidence_level, actual_lookback
        )
    elif config.var_method == VaRMethod.PARAMETRIC:
        return parametric_var(
            portfolio_returns, config.confidence_level, actual_lookback
        )
    elif config.var_method == VaRMethod.MONTE_CARLO:
        return monte_carlo_var(
            portfolio_returns,
            config.confidence_level,
            actual_lookback,
            config.monte_carlo_simulations,
        )
    else:
        raise VaRCalculationError(f"Unknown VaR method: {config.var_method}")


def _aggregate_portfolio_returns(positions: tuple[RiskPosition, ...]) -> list[float]:
    """Aggregate position returns into portfolio returns.

    Args:
        positions: Portfolio positions.

    Returns:
        Aggregated portfolio returns.
    """
    if not positions:
        return []

    min_length = min(len(p.return_series) for p in positions if p.return_series)
    if min_length == 0:
        return []

    portfolio_returns = []
    for i in range(min_length):
        daily_return = sum(
            p.weight * p.return_series[i]
            for p in positions
            if p.return_series and i < len(p.return_series)
        )
        portfolio_returns.append(daily_return)

    return portfolio_returns
