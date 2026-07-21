"""Backtesting performance metrics.

Calculates various performance metrics for backtest results.
"""

from __future__ import annotations

import math
from datetime import datetime
from typing import Any

from backend.backtesting.models import (
    BacktestConfig,
    EquityPoint,
    PerformanceMetrics,
    Trade,
)


def calculate_cagr(start_value: float, end_value: float, years: float) -> float:
    """Calculate Compound Annual Growth Rate.

    Args:
        start_value: Starting value.
        end_value:   Ending value.
        years:       Number of years.

    Returns:
        CAGR as a decimal.
    """
    if years <= 0 or start_value <= 0 or end_value <= 0:
        return 0.0
    return (end_value / start_value) ** (1 / years) - 1


def calculate_total_return(start_value: float, end_value: float) -> float:
    """Calculate total return.

    Args:
        start_value: Starting value.
        end_value:   Ending value.

    Returns:
        Total return as a decimal.
    """
    if start_value <= 0:
        return 0.0
    return (end_value - start_value) / start_value


def calculate_annualized_return(total_return: float, years: float) -> float:
    """Calculate annualized return.

    Args:
        total_return: Total return as a decimal.
        years:        Number of years.

    Returns:
        Annualized return as a decimal.
    """
    if years <= 0:
        return 0.0
    return (1 + total_return) ** (1 / years) - 1


def calculate_sharpe_ratio(
    returns: list[float],
    risk_free_rate: float = 0.06,
    periods_per_year: int = 252,
) -> float:
    """Calculate Sharpe ratio.

    Args:
        returns:         List of period returns.
        risk_free_rate:  Annual risk-free rate.
        periods_per_year: Periods per year.

    Returns:
        Sharpe ratio.
    """
    if not returns or len(returns) < 2:
        return 0.0

    mean_return = sum(returns) / len(returns)
    variance = sum((r - mean_return) ** 2 for r in returns) / (len(returns) - 1)
    std_dev = math.sqrt(variance) if variance > 0 else 0.0001

    excess_return = mean_return - (risk_free_rate / periods_per_year)
    return (excess_return / std_dev) * math.sqrt(periods_per_year)


def calculate_sortino_ratio(
    returns: list[float],
    risk_free_rate: float = 0.06,
    periods_per_year: int = 252,
) -> float:
    """Calculate Sortino ratio.

    Args:
        returns:         List of period returns.
        risk_free_rate:  Annual risk-free rate.
        periods_per_year: Periods per year.

    Returns:
        Sortino ratio.
    """
    if not returns or len(returns) < 2:
        return 0.0

    mean_return = sum(returns) / len(returns)
    downside_returns = [r for r in returns if r < 0]

    if not downside_returns:
        return 0.0

    downside_variance = sum(r**2 for r in downside_returns) / len(downside_returns)
    downside_std = math.sqrt(downside_variance) if downside_variance > 0 else 0.0001

    excess_return = mean_return - (risk_free_rate / periods_per_year)
    return (excess_return / downside_std) * math.sqrt(periods_per_year)


def calculate_calmar_ratio(cagr: float, max_drawdown: float) -> float:
    """Calculate Calmar ratio.

    Args:
        cagr:           Compound Annual Growth Rate.
        max_drawdown:   Maximum drawdown (positive value).

    Returns:
        Calmar ratio.
    """
    if max_drawdown <= 0:
        return 0.0
    return cagr / max_drawdown


def calculate_maximum_drawdown(equity_curve: list[EquityPoint]) -> float:
    """Calculate maximum drawdown.

    Args:
        equity_curve: Equity curve data.

    Returns:
        Maximum drawdown as a positive percentage.
    """
    if not equity_curve:
        return 0.0

    peak = equity_curve[0].equity
    max_dd = 0.0

    for point in equity_curve:
        if point.equity > peak:
            peak = point.equity
        dd = (peak - point.equity) / peak if peak > 0 else 0.0
        if dd > max_dd:
            max_dd = dd

    return max_dd


def calculate_drawdown_curve(equity_curve: list[EquityPoint]) -> list[tuple[datetime, float]]:
    """Calculate drawdown curve.

    Args:
        equity_curve: Equity curve data.

    Returns:
        List of (timestamp, drawdown) pairs.
    """
    if not equity_curve:
        return []

    peak = equity_curve[0].equity
    drawdowns = []

    for point in equity_curve:
        if point.equity > peak:
            peak = point.equity
        dd = (peak - point.equity) / peak if peak > 0 else 0.0
        drawdowns.append((point.date, -dd))

    return drawdowns


def calculate_trade_metrics(trades: list[Trade]) -> dict[str, Any]:
    """Calculate trade-related metrics.

    Args:
        trades: List of completed trades.

    Returns:
        Dictionary of trade metrics.
    """
    if not trades:
        return {
            "win_rate": 0.0,
            "loss_rate": 0.0,
            "profit_factor": 0.0,
            "expectancy": 0.0,
            "average_win": 0.0,
            "average_loss": 0.0,
            "largest_win": 0.0,
            "largest_loss": 0.0,
            "average_holding": 0.0,
            "number_of_trades": 0,
        }

    winning = [t for t in trades if t.pnl > 0]
    losing = [t for t in trades if t.pnl < 0]

    total = len(trades)
    win_rate = len(winning) / total if total > 0 else 0.0
    loss_rate = len(losing) / total if total > 0 else 0.0

    gross_profit = sum(t.pnl for t in winning) if winning else 0.0
    gross_loss = abs(sum(t.pnl for t in losing)) if losing else 0.0001
    profit_factor = gross_profit / gross_loss if gross_loss > 0 else 0.0

    expectancy = sum(t.pnl for t in trades) / total if total > 0 else 0.0

    average_win = gross_profit / len(winning) if winning else 0.0
    average_loss = gross_loss / len(losing) if losing else 0.0

    largest_win = max((t.pnl for t in winning), default=0.0)
    largest_loss = min((t.pnl for t in losing), default=0.0)

    total_holding = sum(t.holding_period for t in trades)
    average_holding = total_holding / total if total > 0 else 0.0

    return {
        "win_rate": win_rate,
        "loss_rate": loss_rate,
        "profit_factor": profit_factor,
        "expectancy": expectancy,
        "average_win": average_win,
        "average_loss": average_loss,
        "largest_win": largest_win,
        "largest_loss": largest_loss,
        "average_holding": average_holding,
        "number_of_trades": total,
    }


def calculate_monthly_returns(
    equity_curve: list[EquityPoint],
) -> list[tuple[str, float]]:
    """Calculate monthly returns.

    Args:
        equity_curve: Equity curve data.

    Returns:
        List of (month_key, return) pairs.
    """
    if not equity_curve:
        return []

    monthly: dict[str, list[EquityPoint]] = {}
    for point in equity_curve:
        key = point.date.strftime("%Y-%m")
        if key not in monthly:
            monthly[key] = []
        monthly[key].append(point)

    results = []
    sorted_months = sorted(monthly.keys())

    for i, month_key in enumerate(sorted_months):
        points = monthly[month_key]
        if len(points) < 2:
            continue

        start_value = points[0].equity
        end_value = points[-1].equity
        ret = (end_value - start_value) / start_value if start_value > 0 else 0.0
        results.append((month_key, ret))

    return results


def calculate_yearly_returns(
    equity_curve: list[EquityPoint],
) -> list[tuple[str, float]]:
    """Calculate yearly returns.

    Args:
        equity_curve: Equity curve data.

    Returns:
        List of (year_key, return) pairs.
    """
    if not equity_curve:
        return []

    yearly: dict[str, list[EquityPoint]] = {}
    for point in equity_curve:
        key = point.date.strftime("%Y")
        if key not in yearly:
            yearly[key] = []
        yearly[key].append(point)

    results = []
    sorted_years = sorted(yearly.keys())

    for year_key in sorted_years:
        points = yearly[year_key]
        if len(points) < 2:
            continue

        start_value = points[0].equity
        end_value = points[-1].equity
        ret = (end_value - start_value) / start_value if start_value > 0 else 0.0
        results.append((year_key, ret))

    return results


def calculate_performance_metrics(
    equity_curve: list[EquityPoint],
    trades: list[Trade],
    config: BacktestConfig,
    total_exposure: float = 0.0,
) -> PerformanceMetrics:
    """Calculate all performance metrics.

    Args:
        equity_curve:    Equity curve data.
        trades:          Completed trades.
        config:          Backtest configuration.
        total_exposure:  Total portfolio exposure.

    Returns:
        PerformanceMetrics with all calculated metrics.
    """
    if not equity_curve:
        return PerformanceMetrics()

    start_value = equity_curve[0].equity
    end_value = equity_curve[-1].equity

    start_date = equity_curve[0].date
    end_date = equity_curve[-1].date
    years = (end_date - start_date).days / 365.25

    cagr = calculate_cagr(start_value, end_value, years)
    total_return = calculate_total_return(start_value, end_value)
    annualized_return = calculate_annualized_return(total_return, years)

    max_drawdown = calculate_maximum_drawdown(equity_curve)
    calmar_ratio = calculate_calmar_ratio(cagr, max_drawdown)

    daily_returns = []
    for i in range(1, len(equity_curve)):
        prev = equity_curve[i - 1].equity
        curr = equity_curve[i].equity
        if prev > 0:
            daily_returns.append((curr - prev) / prev)

    sharpe_ratio = calculate_sharpe_ratio(daily_returns, config.risk_free_rate)
    sortino_ratio = calculate_sortino_ratio(daily_returns, config.risk_free_rate)

    recovery_factor = total_return / max_drawdown if max_drawdown > 0 else 0.0

    trade_metrics = calculate_trade_metrics(trades)

    return PerformanceMetrics(
        cagr=cagr,
        total_return=total_return,
        annualized_return=annualized_return,
        sharpe_ratio=sharpe_ratio,
        sortino_ratio=sortino_ratio,
        calmar_ratio=calmar_ratio,
        maximum_drawdown=max_drawdown,
        recovery_factor=recovery_factor,
        win_rate=trade_metrics["win_rate"],
        loss_rate=trade_metrics["loss_rate"],
        profit_factor=trade_metrics["profit_factor"],
        expectancy=trade_metrics["expectancy"],
        average_win=trade_metrics["average_win"],
        average_loss=trade_metrics["average_loss"],
        largest_win=trade_metrics["largest_win"],
        largest_loss=trade_metrics["largest_loss"],
        average_holding=trade_metrics["average_holding"],
        number_of_trades=trade_metrics["number_of_trades"],
        exposure=total_exposure,
    )
