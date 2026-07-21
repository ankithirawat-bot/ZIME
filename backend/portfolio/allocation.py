"""Portfolio allocation strategies.

Implements various allocation strategies for portfolio construction.
"""

from __future__ import annotations

from typing import Any

from backend.portfolio.exceptions import InvalidAllocationError
from backend.portfolio.models import AllocationStrategy, PortfolioConfig


def equal_weight(
    symbols: tuple[str, ...],
    data: dict[str, Any],
    config: PortfolioConfig,
) -> dict[str, float]:
    """Equal weight allocation.

    Allocates equal weight to all symbols.

    Args:
        symbols: Symbols to allocate.
        data:    Market data (unused for equal weight).
        config:  Portfolio configuration.

    Returns:
        Dictionary of symbol -> weight.
    """
    if not symbols:
        return {}

    weight = 1.0 / len(symbols)
    return {s: weight for s in symbols}


def fixed_weight(
    symbols: tuple[str, ...],
    data: dict[str, Any],
    config: PortfolioConfig,
) -> dict[str, float]:
    """Fixed weight allocation.

    Uses pre-defined weights from data['weights'].

    Args:
        symbols: Symbols to allocate.
        data:    Market data with 'weights' key.
        config:  Portfolio configuration.

    Returns:
        Dictionary of symbol -> weight.

    Raises:
        InvalidAllocationError: If weights not provided or invalid.
    """
    if "weights" not in data:
        raise InvalidAllocationError("Fixed weight requires 'weights' in data")

    weights = data["weights"]
    if not isinstance(weights, dict):
        raise InvalidAllocationError("'weights' must be a dictionary")

    total = sum(weights.get(s, 0.0) for s in symbols)
    if total <= 0:
        raise InvalidAllocationError("Total weight must be positive")

    return {s: weights.get(s, 0.0) / total for s in symbols}


def risk_weight(
    symbols: tuple[str, ...],
    data: dict[str, Any],
    config: PortfolioConfig,
) -> dict[str, float]:
    """Risk weight allocation.

    Allocates inversely proportional to risk (standard deviation).

    Args:
        symbols: Symbols to allocate.
        data:    Market data with 'risk' key (symbol -> std dev).
        config:  Portfolio configuration.

    Returns:
        Dictionary of symbol -> weight.

    Raises:
        InvalidAllocationError: If risk data not provided.
    """
    if "risk" not in data:
        raise InvalidAllocationError("Risk weight requires 'risk' in data")

    risk = data["risk"]
    if not isinstance(risk, dict):
        raise InvalidAllocationError("'risk' must be a dictionary")

    inv_risks = {}
    for s in symbols:
        r = risk.get(s, 1.0)
        if r <= 0:
            r = 0.001
        inv_risks[s] = 1.0 / r

    total = sum(inv_risks.values())
    if total <= 0:
        raise InvalidAllocationError("Total inverse risk must be positive")

    return {s: v / total for s, v in inv_risks.items()}


def volatility_weight(
    symbols: tuple[str, ...],
    data: dict[str, Any],
    config: PortfolioConfig,
) -> dict[str, float]:
    """Volatility weight allocation.

    Allocates inversely proportional to volatility.

    Args:
        symbols: Symbols to allocate.
        data:    Market data with 'volatility' key (symbol -> volatility).
        config:  Portfolio configuration.

    Returns:
        Dictionary of symbol -> weight.

    Raises:
        InvalidAllocationError: If volatility data not provided.
    """
    if "volatility" not in data:
        raise InvalidAllocationError("Volatility weight requires 'volatility' in data")

    volatility = data["volatility"]
    if not isinstance(volatility, dict):
        raise InvalidAllocationError("'volatility' must be a dictionary")

    inv_vols = {}
    for s in symbols:
        v = volatility.get(s, 1.0)
        if v <= 0:
            v = 0.001
        inv_vols[s] = 1.0 / v

    total = sum(inv_vols.values())
    if total <= 0:
        raise InvalidAllocationError("Total inverse volatility must be positive")

    return {s: v / total for s, v in inv_vols.items()}


def score_weight(
    symbols: tuple[str, ...],
    data: dict[str, Any],
    config: PortfolioConfig,
) -> dict[str, float]:
    """Score weight allocation.

    Allocates based on ranking scores.

    Args:
        symbols: Symbols to allocate.
        data:    Market data with 'scores' key (symbol -> score).
        config:  Portfolio configuration.

    Returns:
        Dictionary of symbol -> weight.

    Raises:
        InvalidAllocationError: If scores not provided.
    """
    if "scores" not in data:
        raise InvalidAllocationError("Score weight requires 'scores' in data")

    scores = data["scores"]
    if not isinstance(scores, dict):
        raise InvalidAllocationError("'scores' must be a dictionary")

    score_sum = sum(max(scores.get(s, 0.0), 0.0) for s in symbols)
    if score_sum <= 0:
        raise InvalidAllocationError("Total score must be positive")

    return {s: max(scores.get(s, 0.0), 0.0) / score_sum for s in symbols}


def market_cap_weight(
    symbols: tuple[str, ...],
    data: dict[str, Any],
    config: PortfolioConfig,
) -> dict[str, float]:
    """Market cap weight allocation.

    Allocates based on market capitalization.

    Args:
        symbols: Symbols to allocate.
        data:    Market data with 'market_cap' key (symbol -> market cap).
        config:  Portfolio configuration.

    Returns:
        Dictionary of symbol -> weight.

    Raises:
        InvalidAllocationError: If market cap data not provided.
    """
    if "market_cap" not in data:
        raise InvalidAllocationError("Market cap weight requires 'market_cap' in data")

    market_cap = data["market_cap"]
    if not isinstance(market_cap, dict):
        raise InvalidAllocationError("'market_cap' must be a dictionary")

    total_cap = sum(market_cap.get(s, 0.0) for s in symbols)
    if total_cap <= 0:
        raise InvalidAllocationError("Total market cap must be positive")

    return {s: market_cap.get(s, 0.0) / total_cap for s in symbols}


def get_allocation_strategy(
    strategy: AllocationStrategy,
) -> callable:
    """Get allocation strategy function.

    Args:
        strategy: Allocation strategy enum.

    Returns:
        Allocation strategy function.

    Raises:
        InvalidAllocationError: If strategy not found.
    """
    strategies = {
        AllocationStrategy.EQUAL_WEIGHT: equal_weight,
        AllocationStrategy.FIXED_WEIGHT: fixed_weight,
        AllocationStrategy.RISK_WEIGHT: risk_weight,
        AllocationStrategy.VOLATILITY_WEIGHT: volatility_weight,
        AllocationStrategy.SCORE_WEIGHT: score_weight,
        AllocationStrategy.MARKET_CAP_WEIGHT: market_cap_weight,
    }

    if strategy not in strategies:
        raise InvalidAllocationError(f"Unknown strategy: {strategy}")

    return strategies[strategy]


def calculate_weights(
    strategy: AllocationStrategy,
    symbols: tuple[str, ...],
    data: dict[str, Any],
    config: PortfolioConfig,
) -> dict[str, float]:
    """Calculate allocation weights using specified strategy.

    Args:
        strategy: Allocation strategy to use.
        symbols:  Symbols to allocate.
        data:     Market data for calculations.
        config:   Portfolio configuration.

    Returns:
        Dictionary of symbol -> weight.
    """
    strategy_fn = get_allocation_strategy(strategy)
    return strategy_fn(symbols, data, config)


def validate_weights(weights: dict[str, float]) -> bool:
    """Validate allocation weights.

    Args:
        weights: Allocation weights.

    Returns:
        True if weights are valid.

    Raises:
        InvalidAllocationError: If weights are invalid.
    """
    if not weights:
        raise InvalidAllocationError("Weights cannot be empty")

    total = sum(weights.values())
    if abs(total - 1.0) > 0.001:
        raise InvalidAllocationError(
            f"Weights must sum to 1.0, got {total:.4f}"
        )

    for symbol, weight in weights.items():
        if weight < 0:
            raise InvalidAllocationError(
                f"Weight for {symbol} cannot be negative: {weight}"
            )

    return True
