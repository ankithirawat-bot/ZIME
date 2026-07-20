"""
Reusable simulation metrics.

Pure functions for financial calculations used across execution modes.
"""

from __future__ import annotations

import math


def sharpe_ratio(
    returns: list[float],
    risk_free_rate: float = 0.0,
) -> float:
    """Calculate annualized Sharpe ratio.

    Args:
        returns:        List of periodic returns (e.g. daily).
        risk_free_rate: Annualized risk-free rate (e.g. 0.06 for 6%).

    Returns:
        Annualized Sharpe ratio.
    """
    if len(returns) < 2:
        return 0.0

    avg = sum(returns) / len(returns)
    variance = sum((r - avg) ** 2 for r in returns) / (len(returns) - 1)
    std = math.sqrt(variance) if variance > 0 else 0.0

    if std == 0:
        return 0.0

    daily_rf = risk_free_rate / 252
    excess = avg - daily_rf
    return (excess / std) * math.sqrt(252)


def sortino_ratio(
    returns: list[float],
    risk_free_rate: float = 0.0,
) -> float:
    """Calculate annualized Sortino ratio.

    Uses only downside deviation for risk.

    Args:
        returns:        List of periodic returns.
        risk_free_rate: Annualized risk-free rate.

    Returns:
        Annualized Sortino ratio.
    """
    if len(returns) < 2:
        return 0.0

    avg = sum(returns) / len(returns)
    daily_rf = risk_free_rate / 252
    excess = avg - daily_rf

    downside = [r for r in returns if r < daily_rf]
    if not downside:
        return 10.0 if excess > 0 else 0.0

    downside_var = sum((r - daily_rf) ** 2 for r in downside) / len(returns)
    downside_std = math.sqrt(downside_var) if downside_var > 0 else 0.0

    if downside_std == 0:
        return 10.0 if excess > 0 else 0.0

    return (excess / downside_std) * math.sqrt(252)


def calmar_ratio(
    annualized_return: float,
    maximum_drawdown: float,
) -> float:
    """Calculate Calmar ratio.

    Args:
        annualized_return: Annualized return percentage.
        maximum_drawdown:  Maximum drawdown percentage (positive).

    Returns:
        Calmar ratio.
    """
    if maximum_drawdown <= 0:
        return 0.0
    return annualized_return / maximum_drawdown


def maximum_drawdown(equity_curve: list[float]) -> float:
    """Calculate maximum drawdown from equity curve.

    Args:
        equity_curve: List of equity values over time.

    Returns:
        Maximum drawdown as a positive percentage.
    """
    if len(equity_curve) < 2:
        return 0.0

    peak = equity_curve[0]
    max_dd = 0.0

    for value in equity_curve:
        if value > peak:
            peak = value
        dd = (peak - value) / peak if peak > 0 else 0.0
        if dd > max_dd:
            max_dd = dd

    return max_dd * 100.0


def profit_factor(returns: list[float]) -> float:
    """Calculate profit factor.

    Args:
        returns: List of trade returns (positive for wins, negative for losses).

    Returns:
        Profit factor ratio.
    """
    gross_profit = sum(r for r in returns if r > 0)
    gross_loss = abs(sum(r for r in returns if r < 0))

    if gross_loss == 0:
        return 10.0 if gross_profit > 0 else 0.0
    return gross_profit / gross_loss


def expectancy(returns: list[float]) -> float:
    """Calculate expected value per trade.

    Args:
        returns: List of trade returns.

    Returns:
        Expected value per trade.
    """
    if not returns:
        return 0.0
    return sum(returns) / len(returns)


def cagr(
    start_value: float,
    end_value: float,
    years: float,
) -> float:
    """Calculate Compound Annual Growth Rate.

    Args:
        start_value: Starting portfolio value.
        end_value:   Ending portfolio value.
        years:       Number of years.

    Returns:
        CAGR as a percentage.
    """
    if start_value <= 0 or end_value <= 0 or years <= 0:
        return 0.0
    return ((end_value / start_value) ** (1.0 / years) - 1.0) * 100.0


def win_rate(winning: int, total: int) -> float:
    """Calculate win rate percentage.

    Args:
        winning: Number of winning trades.
        total:   Total number of trades.

    Returns:
        Win rate as a percentage.
    """
    if total == 0:
        return 0.0
    return (winning / total) * 100.0


def loss_rate(losing: int, total: int) -> float:
    """Calculate loss rate percentage.

    Args:
        losing: Number of losing trades.
        total:  Total number of trades.

    Returns:
        Loss rate as a percentage.
    """
    if total == 0:
        return 0.0
    return (losing / total) * 100.0
