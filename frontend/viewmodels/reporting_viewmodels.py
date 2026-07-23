"""Immutable dataclasses for Reporting & Analytics workspace view models."""

from __future__ import annotations

from dataclasses import dataclass


@dataclass(frozen=True)
class AnalyticsSummary:
    portfolio_return: float
    benchmark_return: float
    alpha: float
    beta: float
    sharpe_ratio: float
    max_drawdown: float



@dataclass(frozen=True)
class PerformanceMetric:
    cagr: float
    annual_return: float
    volatility: float
    sortino_ratio: float
    calmar_ratio: float
    information_ratio: float
    profit_factor: float
    win_rate: float



@dataclass(frozen=True)
class StrategyComparison:
    strategy_return: float
    sharpe: float
    drawdown: float
    win_rate: float
    trades: int



@dataclass(frozen=True)
class ChartSeries:
    name: str
    data: list[tuple[float, float]]  # x, y



@dataclass(frozen=True)
class ReportStatus:
    backend_status: str
    data_status: str
    last_refresh_utc: str | None
    available_reports: list[str]
    error: str | None



@dataclass(frozen=True)
class ReportingViewModel:
    analytics: AnalyticsSummary | None
    metrics: PerformanceMetric | None
    strategies: list[StrategyComparison] | None
    charts: list[ChartSeries] | None
    status: ReportStatus
    is_refreshing: bool
    last_refresh_at_utc: str | None
    controller_status: str
