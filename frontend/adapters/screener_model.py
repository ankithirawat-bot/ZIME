"""Screener view models.

Immutable, frozen dataclasses exposed by the ``ScreenerAdapter`` to the UI
layer. The view never imports backend modules directly — it only consumes
these dataclasses.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from datetime import datetime
from typing import Any


@dataclass(frozen=True)
class ScreenerFilter:
    """A single filter entry shown in the Screener filter panel."""

    name: str
    category: str
    operator: str
    value: str
    enabled: bool = True

    def to_dict(self) -> dict[str, Any]:
        return {
            "name": self.name,
            "category": self.category,
            "operator": self.operator,
            "value": self.value,
            "enabled": self.enabled,
        }


@dataclass(frozen=True)
class ScreenerResultRow:
    """A single screener result row."""

    symbol: str
    exchange: str
    last_price: float | None
    change_pct: float | None
    volume: int | None
    passed: bool
    notes: str = ""

    def to_dict(self) -> dict[str, Any]:
        return {
            "symbol": self.symbol,
            "exchange": self.exchange,
            "last_price": self.last_price,
            "change_pct": self.change_pct,
            "volume": self.volume,
            "passed": self.passed,
            "notes": self.notes,
        }


@dataclass(frozen=True)
class ScreenerRunStatus:
    """Lifecycle status for a screener run."""

    state: str
    started_at: str
    completed_at: str
    elapsed_seconds: float
    result_count: int
    error: str | None
    controller_status: str
    event_bus_status: str
    worker_status: str
    extensions: dict[str, str] = field(default_factory=dict)

    def to_dict(self) -> dict[str, Any]:
        return {
            "state": self.state,
            "started_at": self.started_at,
            "completed_at": self.completed_at,
            "elapsed_seconds": self.elapsed_seconds,
            "result_count": self.result_count,
            "error": self.error,
            "controller_status": self.controller_status,
            "event_bus_status": self.event_bus_status,
            "worker_status": self.worker_status,
            "extensions": dict(self.extensions),
        }


@dataclass(frozen=True)
class ScreenerViewModel:
    """Immutable view model rendered by the Screener workspace."""

    screen_name: str
    screen_description: str
    filters: tuple[ScreenerFilter, ...]
    results: tuple[ScreenerResultRow, ...]
    status: ScreenerRunStatus
    available_filters: tuple[str, ...]
    generated_at: datetime

    def to_dict(self) -> dict[str, Any]:
        return {
            "screen_name": self.screen_name,
            "screen_description": self.screen_description,
            "filters": [f.to_dict() for f in self.filters],
            "results": [r.to_dict() for r in self.results],
            "status": self.status.to_dict(),
            "available_filters": list(self.available_filters),
            "generated_at": self.generated_at.isoformat(timespec="seconds"),
        }

    def result_count(self) -> int:
        return len(self.results)
