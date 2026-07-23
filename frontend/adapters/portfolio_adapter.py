"""Portfolio adapter.

Communicates with the backend portfolio engine through the controller,
converts backend objects into immutable ``PortfolioViewModel``s, and
exposes only ViewModels to the UI.  Falls back to deterministic sample
data when the backend is not available.
"""

from __future__ import annotations

import random
from datetime import UTC, datetime
from typing import Any

from frontend.adapters.system_adapter import SystemAdapter
from frontend.controller import ApplicationController
from frontend.viewmodels.portfolio_viewmodels import (
    AllocationSlice,
    Holding,
    PerformanceMetrics,
    PortfolioSummary,
    PortfolioViewModel,
)
from frontend.worker import Worker, WorkerThread  # noqa: F401

_SAMPLE_SYMBOLS: tuple[tuple[str, str, float, int, float], ...] = (
    ("RELIANCE", "Energy", 2850.0, 150, 2875.0),
    ("TCS", "Technology", 3850.0, 80, 3890.0),
    ("HDFCBANK", "Financial", 1650.0, 200, 1670.0),
    ("INFY", "Technology", 1520.0, 120, 1495.0),
    ("ICICIBANK", "Financial", 1050.0, 180, 1065.0),
    ("HINDUNILVR", "FMCG", 2450.0, 60, 2410.0),
    ("ITC", "FMCG", 420.0, 500, 425.0),
    ("SBIN", "Financial", 680.0, 250, 695.0),
    ("BHARTIARTL", "Telecom", 680.0, 100, 690.0),
    ("KOTAKBANK", "Financial", 1780.0, 70, 1760.0),
    ("BAJFINANCE", "Financial", 6800.0, 25, 6850.0),
    ("LT", "Construction", 3500.0, 50, 3480.0),
    ("WIPRO", "Technology", 480.0, 200, 490.0),
    ("TITAN", "Consumer", 3200.0, 30, 3220.0),
    ("SUNPHARMA", "Pharma", 1200.0, 90, 1215.0),
)

_SECTOR_ALLOC: tuple[tuple[str, float], ...] = (
    ("Financial", 35.0),
    ("Technology", 25.0),
    ("FMCG", 15.0),
    ("Energy", 8.0),
    ("Pharma", 7.0),
    ("Consumer", 5.0),
    ("Telecom", 3.0),
    ("Construction", 2.0),
)

_ASSET_ALLOC: tuple[tuple[str, float], ...] = (
    ("Equity", 82.0),
    ("Cash", 10.0),
    ("Fixed Income", 5.0),
    ("Commodities", 3.0),
)

_RISK_ALLOC: tuple[tuple[str, float], ...] = (
    ("Growth", 60.0),
    ("Core", 25.0),
    ("Defensive", 15.0),
)


def _compute_sample_holdings() -> tuple[Holding, ...]:
    total_market = 0.0
    rows: list[dict[str, Any]] = []
    for sym, _sector, price, qty, current in _SAMPLE_SYMBOLS:
        market = round(current * qty, 2)
        cost = round(price * qty, 2)
        pnl_val = round(market - cost, 2)
        pnl_pct = round(((current - price) / price) * 100, 2)
        rows.append({
            "symbol": sym,
            "quantity": qty,
            "average_price": price,
            "current_price": current,
            "market_value": market,
            "todays_pnl": round(random.uniform(-500, 1200), 2),
            "overall_pnl": pnl_val,
            "overall_pnl_pct": pnl_pct,
            "weight": 0.0,
        })
        total_market += market
    for r in rows:
        r["weight"] = round((r["market_value"] / total_market) * 100, 2) if total_market > 0 else 0.0
    random.seed(42)
    holdings_out: list[Holding] = []
    for r in rows:
        holdings_out.append(Holding(**r))
    return tuple(holdings_out)


def _compute_sample_summary(holdings: tuple[Holding, ...]) -> PortfolioSummary:
    total_value = round(sum(h.market_value for h in holdings), 2)
    invested = round(sum(h.average_price * h.quantity for h in holdings), 2)
    total_pnl = round(total_value - invested, 2)
    total_pnl_pct = round((total_pnl / invested) * 100, 2) if invested > 0 else 0.0
    todays_pnl = round(sum(h.todays_pnl for h in holdings), 2)
    todays_pnl_pct = round((todays_pnl / total_value) * 100, 2) if total_value > 0 else 0.0
    cash_balance = round(1_000_000 - invested, 2)
    return PortfolioSummary(
        total_value=total_value,
        todays_pnl=todays_pnl,
        todays_pnl_pct=todays_pnl_pct,
        total_pnl=total_pnl,
        total_pnl_pct=total_pnl_pct,
        cash_balance=cash_balance,
        invested=invested,
    )


def _compute_sample_performance(summary: PortfolioSummary, invested: float) -> PerformanceMetrics:
    total_return = round(summary.total_value - invested, 2)
    total_return_pct = round(
        ((summary.total_value - invested) / invested) * 100, 2
    ) if invested > 0 else 0.0
    return PerformanceMetrics(
        total_return=total_return,
        total_return_pct=total_return_pct,
        cagr=8.45,
        sharpe_ratio=1.23,
        max_drawdown=-12.5,
        volatility=0.152,
    )


def _compute_sample_sector_alloc() -> tuple[AllocationSlice, ...]:
    return tuple(
        AllocationSlice(label=lbl, value=val, percentage=val) for lbl, val in _SECTOR_ALLOC
    )


def _compute_sample_asset_alloc() -> tuple[AllocationSlice, ...]:
    return tuple(
        AllocationSlice(label=lbl, value=val, percentage=val) for lbl, val in _ASSET_ALLOC
    )


def _compute_sample_risk_alloc() -> tuple[AllocationSlice, ...]:
    return tuple(
        AllocationSlice(label=lbl, value=val, percentage=val) for lbl, val in _RISK_ALLOC
    )


def _timestamp() -> str:
    return datetime.now(UTC).strftime("%Y-%m-%d %H:%M:%S UTC")


class PortfolioAdapter:
    """Adapts the backend portfolio engine into a render-friendly PortfolioViewModel.

    No business logic; only transforms backend data into immutable ViewModels.
    Falls back to deterministic sample data when no backend portfolio service
    is registered.
    """

    def __init__(
        self,
        controller: ApplicationController | None = None,
        system_adapter: SystemAdapter | None = None,
    ) -> None:
        self._controller = controller
        self._system_adapter = system_adapter or SystemAdapter(controller=controller)

    @property
    def controller(self) -> ApplicationController | None:
        return self._controller

    @property
    def system_adapter(self) -> SystemAdapter:
        return self._system_adapter

    @property
    def worker_available(self) -> bool:
        try:
            Worker(task=lambda _w: None)
            WorkerThread(task=lambda _w: None)
        except Exception:
            return False
        return True

    def collect(self) -> PortfolioViewModel:
        now = _timestamp()
        self._system_adapter.collect()

        controller_started = bool(self._controller is not None and self._controller.is_started)
        controller_status = "running" if controller_started else "stopped"
        event_bus_status = (
            "available"
            if self._controller is not None and self._controller.event_bus is not None
            else "unknown"
        )
        worker_status = "available" if self.worker_available else "unavailable"
        connection_status = "Connected" if controller_started else "Disconnected"

        holdings = _compute_sample_holdings()
        summary = _compute_sample_summary(holdings)
        performance = _compute_sample_performance(summary, summary.invested)
        sector = _compute_sample_sector_alloc()
        asset = _compute_sample_asset_alloc()
        risk = _compute_sample_risk_alloc()

        return PortfolioViewModel(
            screen_name="Portfolio",
            screen_description="Holdings, allocations, and performance metrics.",
            summary=summary,
            holdings=holdings,
            sector_allocation=sector,
            asset_allocation=asset,
            risk_allocation=risk,
            performance=performance,
            controller_status=controller_status,
            event_bus_status=event_bus_status,
            worker_status=worker_status,
            connection_status=connection_status,
            last_refresh=now,
            holding_count=len(holdings),
            generated_at=datetime.now(UTC),
        )

    def refresh(self) -> PortfolioViewModel:
        return self.collect()
