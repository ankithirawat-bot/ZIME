from __future__ import annotations

from datetime import UTC, datetime

from frontend.adapters.market_overview_model import (
    MarketBreadth,
    MarketIndexSnapshot,
    MarketOverview,
)
from frontend.adapters.system_adapter import SystemAdapter
from frontend.controller import ApplicationController
from frontend.worker import Worker, WorkerThread  # noqa: F401  (availability check)

_INDEX_SYMBOLS: tuple[str, ...] = ("NIFTY", "SENSEX", "BANK NIFTY", "VIX")


class MarketOverviewAdapter:
    """Placeholder adapter for the Market Overview page.

    Reads only controller/system state — no live market data sources are
    contacted. All market figures are returned as ``None``/empty until the
    data layer is introduced in a later sprint.
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

    def collect(self) -> MarketOverview:
        system_status = self._system_adapter.collect()
        now = datetime.now(UTC).strftime("%Y-%m-%d %H:%M:%S UTC")

        indices = tuple(
            MarketIndexSnapshot(symbol=symbol, last=None, change=None, change_pct=None)
            for symbol in _INDEX_SYMBOLS
        )

        breadth = MarketBreadth(
            advances=None,
            declines=None,
            unchanged=None,
            advance_decline_ratio=None,
        )

        controller_started = bool(self._controller is not None and self._controller.is_started)
        controller_status = "running" if controller_started else "stopped"
        event_bus_status = (
            "available"
            if self._controller is not None and self._controller.event_bus is not None
            else "unknown"
        )
        worker_status = "available" if self.worker_available else "unavailable"
        connection_connected = controller_started
        connection_detail = (
            "Controller running"
            if controller_started
            else "Awaiting controller"
        )

        return MarketOverview(
            indices=indices,
            top_gainers=(),
            top_losers=(),
            most_active=(),
            breadth=breadth,
            last_update=now,
            connection_connected=connection_connected,
            connection_detail=connection_detail,
            controller_status=controller_status,
            event_bus_status=event_bus_status,
            worker_status=worker_status,
            extensions={"python_version": system_status.python_version},
        )
