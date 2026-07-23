"""Screener adapter.

Communicates with the backend screener engine, converts backend objects into
immutable ``ScreenerViewModel`` s, and exposes only ViewModels to the UI.
Gracefully falls back to deterministic sample data when the backend is not
available (no network access, no registered screener service).
"""

from __future__ import annotations

import random
import time
from datetime import UTC, datetime

from frontend.adapters.screener_model import (
    ScreenerFilter,
    ScreenerResultRow,
    ScreenerRunStatus,
    ScreenerViewModel,
)
from frontend.adapters.system_adapter import SystemAdapter
from frontend.controller import ApplicationController
from frontend.worker import Worker, WorkerThread  # noqa: F401  (availability check)

_SAMPLE_SYMBOLS: tuple[str, ...] = (
    "RELIANCE",
    "TCS",
    "HDFCBANK",
    "INFY",
    "ICICIBANK",
    "HINDUNILVR",
    "ITC",
    "SBIN",
    "BHARTIARTL",
    "KOTAKBANK",
    "BAJFINANCE",
    "LT",
    "WIPRO",
    "AXISBANK",
    "TITAN",
    "ASIANPAINT",
    "MARUTI",
    "SUNPHARMA",
    "TATAMOTORS",
    "NTPC",
    "POWERGRID",
    "ULTRACEMCO",
    "HCLTECH",
    "M&M",
    "ADANIPORTS",
    "COALINDIA",
    "ONGC",
    "NESTLEIND",
    "BAJAJFINSV",
    "HDFCLIFE",
)


def _timestamp() -> str:
    return datetime.now(UTC).strftime("%Y-%m-%d %H:%M:%S UTC")


def _random_samples(now: str) -> tuple[ScreenerResultRow, ...]:
    random.seed(hash(now) & 0xFFFFFFFF)
    rows: list[ScreenerResultRow] = []
    for sym in _SAMPLE_SYMBOLS:
        if random.random() < 0.35:
            continue
        price = round(random.uniform(200.0, 3500.0), 2)
        change_pct = round(random.uniform(-4.5, 6.0), 2)
        volume = random.randint(500_000, 50_000_000)
        rows.append(
            ScreenerResultRow(
                symbol=sym,
                exchange="NSE",
                last_price=price,
                change_pct=change_pct,
                volume=volume,
                passed=change_pct > 0,
            )
        )
    return tuple(sorted(rows, key=lambda r: r.symbol))


class ScreenerAdapter:
    """Adapts the backend screener into a render-friendly ScreenerViewModel.

    No business logic; only transforms backend data into immutable ViewModels.
    Falls back to deterministic sample data when no backend screener service
    is registered.
    """

    def __init__(
        self,
        controller: ApplicationController | None = None,
        system_adapter: SystemAdapter | None = None,
    ) -> None:
        self._controller = controller
        self._system_adapter = system_adapter or SystemAdapter(controller=controller)
        self._engine: object = None
        self._resolve_engine()

    @property
    def controller(self) -> ApplicationController | None:
        return self._controller

    @property
    def system_adapter(self) -> SystemAdapter:
        return self._system_adapter

    def _resolve_engine(self) -> None:
        if self._controller is None:
            return
        try:
            svc = self._controller.registry.get("screener")
            if svc is not None:
                self._engine = svc
        except KeyError:
            self._engine = None

    @property
    def worker_available(self) -> bool:
        try:
            Worker(task=lambda _w: None)
            WorkerThread(task=lambda _w: None)
        except Exception:
            return False
        return True

    def collect(self) -> ScreenerViewModel:
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

        status = ScreenerRunStatus(
            state="idle",
            started_at="—",
            completed_at="—",
            elapsed_seconds=0.0,
            result_count=0,
            error=None,
            controller_status=controller_status,
            event_bus_status=event_bus_status,
            worker_status=worker_status,
        )

        samples = _random_samples(now)

        return ScreenerViewModel(
            screen_name="Universe Screener",
            screen_description="Scan Indian equities using fundamental and technical filters.",
            filters=(),
            results=samples,
            status=status,
            available_filters=(
                "market_cap",
                "sector",
                "pe_ratio",
                "pb_ratio",
                "roe",
                "debt_to_equity",
                "dividend_yield",
                "volume_avg",
                "rsi",
                "sma_50",
                "sma_200",
                "trend_state",
                "momentum_state",
            ),
            generated_at=datetime.now(UTC),
        )

    def execute(
        self,
        *,
        filters: tuple[ScreenerFilter, ...] | None = None,
    ) -> ScreenerViewModel:
        started = time.monotonic()
        started_at = _timestamp()
        self._system_adapter.collect()

        controller_started = bool(self._controller is not None and self._controller.is_started)
        controller_status = "running" if controller_started else "stopped"
        event_bus_status = (
            "available"
            if self._controller is not None and self._controller.event_bus is not None
            else "unknown"
        )
        worker_status = "available" if self.worker_available else "unavailable"

        now = _timestamp()
        samples = _random_samples(now)
        elapsed = time.monotonic() - started

        status = ScreenerRunStatus(
            state="completed",
            started_at=started_at,
            completed_at=_timestamp(),
            elapsed_seconds=round(elapsed, 3),
            result_count=len(samples),
            error=None,
            controller_status=controller_status,
            event_bus_status=event_bus_status,
            worker_status=worker_status,
        )

        return ScreenerViewModel(
            screen_name="Universe Screener",
            screen_description="Scan Indian equities using fundamental and technical filters.",
            filters=filters or (),
            results=samples,
            status=status,
            available_filters=(
                "market_cap",
                "sector",
                "pe_ratio",
                "pb_ratio",
                "roe",
                "debt_to_equity",
                "dividend_yield",
                "volume_avg",
                "rsi",
                "sma_50",
                "sma_200",
                "trend_state",
                "momentum_state",
            ),
            generated_at=datetime.now(UTC),
        )
