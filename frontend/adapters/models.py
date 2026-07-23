from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any


@dataclass(frozen=True)
class SystemStatus:
    python_version: str
    platform: str
    qt_version: str
    controller_status: str
    controller_started: bool
    event_bus_status: str
    worker_availability: str
    logging_status: str
    log_file_path: str
    log_file_exists: bool
    log_level: str
    extensions: dict[str, str] = field(default_factory=dict)

    def to_dict(self) -> dict[str, Any]:
        return {
            "python_version": self.python_version,
            "platform": self.platform,
            "qt_version": self.qt_version,
            "controller_status": self.controller_status,
            "controller_started": self.controller_started,
            "event_bus_status": self.event_bus_status,
            "worker_availability": self.worker_availability,
            "logging_status": self.logging_status,
            "log_file_path": self.log_file_path,
            "log_file_exists": self.log_file_exists,
            "log_level": self.log_level,
            **self.extensions,
        }


@dataclass(frozen=True)
class DashboardSummary:
    application_version: str
    application_name: str
    branch: str | None
    build: str
    theme: str
    window_size: tuple[int, int]
    window_position: tuple[int, int]
    current_datetime: str
    current_page: str
    current_page_index: int
    last_start: str
    last_opened_page: str
    log_file_path: str
    system: SystemStatus

    def to_dict(self) -> dict[str, Any]:
        return {
            "application_name": self.application_name,
            "application_version": self.application_version,
            "branch": self.branch,
            "build": self.build,
            "theme": self.theme,
            "window_size": list(self.window_size),
            "window_position": list(self.window_position),
            "current_datetime": self.current_datetime,
            "current_page": self.current_page,
            "current_page_index": self.current_page_index,
            "last_start": self.last_start,
            "last_opened_page": self.last_opened_page,
            "log_file_path": self.log_file_path,
            "system": self.system.to_dict(),
        }
