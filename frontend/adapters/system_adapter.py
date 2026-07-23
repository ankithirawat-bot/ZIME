from __future__ import annotations

import logging
import logging.handlers
import os
import platform
import sys
from datetime import UTC, datetime
from pathlib import Path
from typing import Any

from PySide6 import QtCore

from frontend.adapters.models import SystemStatus
from frontend.controller import ApplicationController
from frontend.logging import APPLICATION_LOG_NAME, LOG_RELATIVE_PATH


def _project_root() -> Path:
    return Path(__file__).resolve().parents[2]


def _read_log_file_state(log_path: Path) -> dict[str, str]:
    info: dict[str, str] = {}
    if log_path.exists():
        try:
            info["log_file_size"] = f"{log_path.stat().st_size} bytes"
        except OSError:
            info["log_file_size"] = "unavailable"
    else:
        info["log_file_size"] = "missing"
    return info


class SystemAdapter:
    """Collects operational state from the controller and runtime environment.

    Does not contain business logic and does not perform any I/O beyond
    reading the log file stat.
    """

    def __init__(self, controller: ApplicationController | None = None) -> None:
        self._controller = controller

    @staticmethod
    def project_root() -> Path:
        return _project_root()

    def collect(self) -> SystemStatus:
        controller = self._controller
        controller_started = bool(controller is not None and controller.is_started)
        controller_status = "running" if controller_started else "stopped"

        event_bus_status = (
            "available" if controller is not None and controller.event_bus is not None else "unknown"
        )
        worker_availability = "available"

        app_logger = logging.getLogger(APPLICATION_LOG_NAME)
        rotating_attached = any(
            isinstance(h, logging.handlers.RotatingFileHandler) for h in app_logger.handlers
        )
        logging_status = "configured" if rotating_attached else "not_configured"

        if controller is not None:
            raw = controller.log_path()
            log_path: Path = Path(raw) if raw is not None and isinstance(raw, str) else (
                Path(raw) if raw is not None else _project_root() / LOG_RELATIVE_PATH
            ) or _project_root() / LOG_RELATIVE_PATH
        else:
            log_path = _project_root() / LOG_RELATIVE_PATH
        log_exists = log_path.exists()
        log_file_path = str(log_path)

        extensions = _read_log_file_state(log_path)
        log_level_value = logging.getLevelName(app_logger.level)
        if not isinstance(log_level_value, str):
            log_level_value = "INFO"

        return SystemStatus(
            python_version=sys.version.split()[0],
            platform=platform.platform(),
            qt_version=str(QtCore.qVersion()),
            controller_status=controller_status,
            controller_started=controller_started,
            event_bus_status=event_bus_status,
            worker_availability=worker_availability,
            logging_status=logging_status,
            log_file_path=log_file_path,
            log_file_exists=log_exists,
            log_level=log_level_value,
            extensions=extensions,
        )

    @staticmethod
    def current_datetime_iso() -> str:
        return datetime.now(UTC).isoformat(timespec="seconds")

    @staticmethod
    def environment_info() -> dict[str, Any]:
        return {
            "executable": sys.executable,
            "frozen": getattr(sys, "frozen", False),
            "argv": list(sys.argv),
            "cwd": os.getcwd(),
        }
