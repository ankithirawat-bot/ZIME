from __future__ import annotations

from dataclasses import dataclass


@dataclass(frozen=True)
class PlaceholderService:
    name: str

    def __repr__(self) -> str:
        return f"PlaceholderService(name={self.name!r})"


class ServiceRegistry:
    def __init__(self) -> None:
        self._services: dict[str, object] = {}

    def register(self, name: str, service: object) -> None:
        if not isinstance(name, str) or not name:
            raise ValueError("service name must be a non-empty string")
        self._services[name] = service

    def get(self, name: str) -> object:
        if name not in self._services:
            raise KeyError(f"service not registered: {name}")
        return self._services[name]

    def has(self, name: str) -> bool:
        return name in self._services

    def unregister(self, name: str) -> None:
        if name not in self._services:
            raise KeyError(f"service not registered: {name}")
        del self._services[name]

    def names(self) -> tuple[str, ...]:
        return tuple(self._services.keys())

    def __contains__(self, name: object) -> bool:
        return isinstance(name, str) and name in self._services


PLACEHOLDER_SERVICES: tuple[str, ...] = (
    "analytics",
    "backtesting_adapter",
    "reporting_adapter",
    "screener",
    "portfolio",
    "intelligence",
    "backtesting_engine",
    "reporting_engine",
    "settings",
)


def create_default_registry() -> ServiceRegistry:
    registry = ServiceRegistry()
    for service_name in PLACEHOLDER_SERVICES:
        registry.register(service_name, PlaceholderService(name=service_name))
    return registry
