from __future__ import annotations

import logging
from collections.abc import Callable
from pathlib import Path
from typing import Any

from PySide6.QtCore import QByteArray

from frontend.adapters.backtesting_adapter import BacktestingAdapter
from frontend.adapters.reporting_adapter import ReportingAdapter
from frontend.event_bus import EventBus
from pathlib import Path

from frontend.logging import (
    LOG_RELATIVE_PATH,
    configure_logging,
    get_logger,
    install_excepthook,
)
from frontend.service_registry import ServiceRegistry, create_default_registry
from frontend.settings import DesktopSettingsStore

EVENT_APPLICATION_STARTING = "application.starting"
EVENT_APPLICATION_STARTED = "application.started"
EVENT_APPLICATION_SHUTTING_DOWN = "application.shutting_down"
EVENT_APPLICATION_CLOSED = "application.closed"
EVENT_SETTINGS_LOADED = "settings.loaded"
EVENT_SETTINGS_SAVED = "settings.saved"


READY_CALLBACK = Callable[[Any], None]


class ApplicationController:
    def __init__(
        self,
        *,
        config_path: Path | None = None,
        log_path: Path | None = None,
        registry: ServiceRegistry | None = None,
        event_bus: EventBus | None = None,
        settings_store: DesktopSettingsStore | None = None,
    ) -> None:
        self._event_bus = event_bus or EventBus()
        self._registry = registry or create_default_registry()
        self._settings_store = settings_store or DesktopSettingsStore(config_path=config_path)
        self._logger: logging.Logger | None = None
        self._started = False
        self._log_path = log_path
        self._resolved_log_path: Path | None = None
    @property
    def event_bus(self) -> EventBus:
        return self._event_bus

    @property
    def registry(self) -> ServiceRegistry:
        return self._registry

    @property
    def settings(self) -> DesktopSettingsStore:
        return self._settings_store

    @property
    def logger(self) -> logging.Logger:
        return self._logger or get_logger("controller")

    @property
    def is_started(self) -> bool:
        return self._started

    @property
    def status(self) -> str:
        return "running" if self._started else "stopped"

    def startup(self) -> None:
        if self._started:
            return
        level = getattr(logging, self._settings_store.ensure_loaded().log_level.upper(), logging.INFO)
        self._logger = configure_logging(
            log_path=self._log_path,
            level=level,
        )
        self._resolved_log_path = (
            self._log_path if self._log_path is not None else Path(__file__).resolve().parent / LOG_RELATIVE_PATH
        )
        install_excepthook(self._logger)
        self._event_bus.publish(EVENT_APPLICATION_STARTING, payload={"config_path": str(self._settings_store.path)})
        self.register_default_services()
        self._event_bus.publish(EVENT_SETTINGS_LOADED, payload=self._settings_store.settings().to_dict())
        self._event_bus.publish(EVENT_APPLICATION_STARTED, payload={"services": list(self._registry.names())})
        self._logger.info("Application started")
        self._started = True

    def log_path(self) -> Path | None:
        if self._resolved_log_path is not None:
            return self._resolved_log_path
        if self._log_path is not None:
            return self._log_path
        return Path(__file__).resolve().parent / LOG_RELATIVE_PATH

    def shutdown(self) -> None:
        if not self._started:
            return
        try:
            self._event_bus.publish(EVENT_APPLICATION_SHUTTING_DOWN)
            try:
                self._settings_store.save()
            except OSError:
                pass
            self._event_bus.publish(EVENT_APPLICATION_CLOSED)
            self.logger.info("Application closed")
        finally:
            self._started = False

    def register_default_services(self) -> None:
        for name in self._registry.names():
            self._event_bus.subscribe(EVENT_APPLICATION_CLOSED, lambda _e, _p, _n=name: self._finalize_service(_n))
        self._registry.register("BacktestingAdapter", BacktestingAdapter(self))
        self._registry.register("ReportingAdapter", ReportingAdapter(self))

    def _finalize_service(self, name: str) -> None:
        self.logger.debug("Service finalized: %s", name)

    def save_window_state(self, *, geometry: QByteArray | None = None, size=None, position=None, last_page: int | None = None) -> None:
        changes: dict[str, object] = {}
        if size is not None:
            changes["window_size"] = {"width": int(size.width()), "height": int(size.height())}
        if position is not None:
            changes["window_position"] = {"x": int(position.x()), "y": int(position.y())}
        if last_page is not None:
            changes["last_opened_page"] = int(last_page)
        if changes:
            self._settings_store.update(**changes)
            self._event_bus.publish(EVENT_SETTINGS_SAVED, payload=changes)

    def register_service(self, name: str, service: object) -> None:
        self._registry.register(name, service)

    def get_backtesting_adapter(self) -> BacktestingAdapter:
        return self._registry.get("BacktestingAdapter")

    def get_reporting_adapter(self) -> ReportingAdapter:
        return self._registry.get("ReportingAdapter")
