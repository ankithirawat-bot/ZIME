from __future__ import annotations

from collections import defaultdict
from collections.abc import Callable
from typing import Any

Payload = Any
Callback = Callable[[str, Payload], None]


class EventBus:
    def __init__(self) -> None:
        self._subscribers: dict[str, list[Callback]] = defaultdict(list)

    def subscribe(self, event_name: str, callback: Callback) -> None:
        if not isinstance(event_name, str) or not event_name:
            raise ValueError("event_name must be a non-empty string")
        if not callable(callback):
            raise TypeError("callback must be callable")
        self._subscribers[event_name].append(callback)

    def unsubscribe(self, event_name: str, callback: Callback) -> None:
        if event_name in self._subscribers:
            try:
                self._subscribers[event_name].remove(callback)
            except ValueError:
                pass

    def publish(self, event_name: str, payload: Payload = None) -> int:
        if not isinstance(event_name, str) or not event_name:
            raise ValueError("event_name must be a non-empty string")
        delivered = 0
        for callback in list(self._subscribers.get(event_name, ())):
            callback(event_name, payload)
            delivered += 1
        return delivered

    def clear(self) -> None:
        self._subscribers.clear()

    def subscriber_count(self, event_name: str) -> int:
        return len(self._subscribers.get(event_name, ()))
