from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any


@dataclass(frozen=True)
class MarketBreadth:
    advances: int | None
    declines: int | None
    unchanged: int | None
    advance_decline_ratio: float | None

    def to_dict(self) -> dict[str, Any]:
        return {
            "advances": self.advances,
            "declines": self.declines,
            "unchanged": self.unchanged,
            "advance_decline_ratio": self.advance_decline_ratio,
        }


@dataclass(frozen=True)
class MarketIndexSnapshot:
    symbol: str
    last: float | None
    change: float | None
    change_pct: float | None

    def to_dict(self) -> dict[str, Any]:
        return {
            "symbol": self.symbol,
            "last": self.last,
            "change": self.change,
            "change_pct": self.change_pct,
        }


@dataclass(frozen=True)
class MarketOverview:
    indices: tuple[MarketIndexSnapshot, ...]
    top_gainers: tuple[str, ...]
    top_losers: tuple[str, ...]
    most_active: tuple[str, ...]
    breadth: MarketBreadth
    last_update: str
    connection_connected: bool
    connection_detail: str
    controller_status: str
    event_bus_status: str
    worker_status: str
    extensions: dict[str, str] = field(default_factory=dict)

    def to_dict(self) -> dict[str, Any]:
        return {
            "indices": [idx.to_dict() for idx in self.indices],
            "top_gainers": list(self.top_gainers),
            "top_losers": list(self.top_losers),
            "most_active": list(self.most_active),
            "breadth": self.breadth.to_dict(),
            "last_update": self.last_update,
            "connection_connected": self.connection_connected,
            "connection_detail": self.connection_detail,
            "controller_status": self.controller_status,
            "event_bus_status": self.event_bus_status,
            "worker_status": self.worker_status,
            "extensions": dict(self.extensions),
        }
