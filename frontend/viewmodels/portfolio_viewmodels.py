from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime
from typing import Any


@dataclass(frozen=True)
class PortfolioSummary:
    total_value: float
    todays_pnl: float
    todays_pnl_pct: float
    total_pnl: float
    total_pnl_pct: float
    cash_balance: float
    invested: float

    def to_dict(self) -> dict[str, Any]:
        return {
            "total_value": self.total_value,
            "todays_pnl": self.todays_pnl,
            "todays_pnl_pct": self.todays_pnl_pct,
            "total_pnl": self.total_pnl,
            "total_pnl_pct": self.total_pnl_pct,
            "cash_balance": self.cash_balance,
            "invested": self.invested,
        }


@dataclass(frozen=True)
class Holding:
    symbol: str
    quantity: int
    average_price: float
    current_price: float
    market_value: float
    todays_pnl: float
    overall_pnl: float
    overall_pnl_pct: float
    weight: float

    def to_dict(self) -> dict[str, Any]:
        return {
            "symbol": self.symbol,
            "quantity": self.quantity,
            "average_price": self.average_price,
            "current_price": self.current_price,
            "market_value": self.market_value,
            "todays_pnl": self.todays_pnl,
            "overall_pnl": self.overall_pnl,
            "overall_pnl_pct": self.overall_pnl_pct,
            "weight": self.weight,
        }


@dataclass(frozen=True)
class AllocationSlice:
    label: str
    value: float
    percentage: float

    def to_dict(self) -> dict[str, Any]:
        return {
            "label": self.label,
            "value": self.value,
            "percentage": self.percentage,
        }


@dataclass(frozen=True)
class PerformanceMetrics:
    total_return: float
    total_return_pct: float
    cagr: float | None
    sharpe_ratio: float | None
    max_drawdown: float | None
    volatility: float | None

    def to_dict(self) -> dict[str, Any]:
        return {
            "total_return": self.total_return,
            "total_return_pct": self.total_return_pct,
            "cagr": self.cagr,
            "sharpe_ratio": self.sharpe_ratio,
            "max_drawdown": self.max_drawdown,
            "volatility": self.volatility,
        }


@dataclass(frozen=True)
class PortfolioViewModel:
    screen_name: str
    screen_description: str
    summary: PortfolioSummary
    holdings: tuple[Holding, ...]
    sector_allocation: tuple[AllocationSlice, ...]
    asset_allocation: tuple[AllocationSlice, ...]
    risk_allocation: tuple[AllocationSlice, ...]
    performance: PerformanceMetrics
    controller_status: str
    event_bus_status: str
    worker_status: str
    connection_status: str
    last_refresh: str
    holding_count: int
    generated_at: datetime

    def to_dict(self) -> dict[str, Any]:
        return {
            "screen_name": self.screen_name,
            "screen_description": self.screen_description,
            "summary": self.summary.to_dict(),
            "holdings": [h.to_dict() for h in self.holdings],
            "sector_allocation": [a.to_dict() for a in self.sector_allocation],
            "asset_allocation": [a.to_dict() for a in self.asset_allocation],
            "risk_allocation": [a.to_dict() for a in self.risk_allocation],
            "performance": self.performance.to_dict(),
            "controller_status": self.controller_status,
            "event_bus_status": self.event_bus_status,
            "worker_status": self.worker_status,
            "connection_status": self.connection_status,
            "last_refresh": self.last_refresh,
            "holding_count": self.holding_count,
            "generated_at": self.generated_at.isoformat(timespec="seconds"),
        }

    def flatten_holdings(self) -> tuple[dict[str, Any], ...]:
        return tuple(h.to_dict() for h in self.holdings)
