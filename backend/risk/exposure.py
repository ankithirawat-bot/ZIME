"""Risk exposure analysis.

Calculates various exposure metrics for portfolio risk analysis.
"""

from __future__ import annotations

from backend.risk.models import Exposure, RiskConfig, RiskPosition


def calculate_gross_exposure(positions: tuple[RiskPosition, ...]) -> float:
    """Calculate gross exposure.

    Gross exposure is the sum of absolute weights.

    Args:
        positions: Portfolio positions.

    Returns:
        Gross exposure.
    """
    return sum(abs(p.weight) for p in positions)


def calculate_net_exposure(positions: tuple[RiskPosition, ...]) -> float:
    """Calculate net exposure.

    Net exposure is long weights minus short weights.

    Args:
        positions: Portfolio positions.

    Returns:
        Net exposure.
    """
    return sum(p.weight for p in positions)


def calculate_long_exposure(positions: tuple[RiskPosition, ...]) -> float:
    """Calculate long exposure.

    Args:
        positions: Portfolio positions.

    Returns:
        Long exposure.
    """
    return sum(p.weight for p in positions if p.weight > 0)


def calculate_short_exposure(positions: tuple[RiskPosition, ...]) -> float:
    """Calculate short exposure.

    Args:
        positions: Portfolio positions.

    Returns:
        Short exposure (negative).
    """
    return sum(p.weight for p in positions if p.weight < 0)


def calculate_cash_exposure(
    positions: tuple[RiskPosition, ...],
    total_equity: float = 1.0,
) -> float:
    """Calculate cash exposure.

    Args:
        positions:    Portfolio positions.
        total_equity: Total portfolio equity.

    Returns:
        Cash exposure.
    """
    invested = sum(abs(p.weight) for p in positions)
    cash = 1.0 - invested
    return max(cash, 0.0)


def calculate_sector_exposure(positions: tuple[RiskPosition, ...]) -> dict[str, float]:
    """Calculate sector exposure.

    Args:
        positions: Portfolio positions.

    Returns:
        Dictionary of sector -> exposure.
    """
    sector_weights: dict[str, float] = {}
    for pos in positions:
        sector = pos.sector or "Unknown"
        sector_weights[sector] = sector_weights.get(sector, 0.0) + pos.weight

    return sector_weights


def calculate_industry_exposure(positions: tuple[RiskPosition, ...]) -> dict[str, float]:
    """Calculate industry exposure.

    Uses sector as industry proxy.

    Args:
        positions: Portfolio positions.

    Returns:
        Dictionary of industry -> exposure.
    """
    return calculate_sector_exposure(positions)


def calculate_position_exposure(positions: tuple[RiskPosition, ...]) -> dict[str, float]:
    """Calculate position exposure.

    Args:
        positions: Portfolio positions.

    Returns:
        Dictionary of symbol -> exposure.
    """
    return {p.symbol: p.weight for p in positions}


def calculate_concentration_index(positions: tuple[RiskPosition, ...]) -> float:
    """Calculate concentration index (Herfindahl-Hirschman Index).

    HHI = sum(weight_i^2)

    Args:
        positions: Portfolio positions.

    Returns:
        Concentration index (0 to 1).
    """
    return sum(p.weight**2 for p in positions)


def calculate_exposure(
    positions: tuple[RiskPosition, ...],
    config: RiskConfig,
) -> Exposure:
    """Calculate all exposure metrics.

    Args:
        positions: Portfolio positions.
        config:    Risk configuration.

    Returns:
        Exposure with all metrics.
    """
    gross = calculate_gross_exposure(positions)
    net = calculate_net_exposure(positions)
    long = calculate_long_exposure(positions)
    short = calculate_short_exposure(positions)
    cash = calculate_cash_exposure(positions)
    sector = calculate_sector_exposure(positions)
    industry = calculate_industry_exposure(positions)
    position = calculate_position_exposure(positions)
    concentration = calculate_concentration_index(positions)

    return Exposure(
        gross_exposure=gross,
        net_exposure=net,
        long_exposure=long,
        short_exposure=short,
        cash_exposure=cash,
        sector_exposure=sector,
        industry_exposure=industry,
        position_exposure=position,
        concentration_index=concentration,
    )
