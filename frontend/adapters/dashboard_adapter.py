from __future__ import annotations

import re
import subprocess
import tomllib
from datetime import datetime
from pathlib import Path

from frontend.adapters.models import DashboardSummary
from frontend.adapters.system_adapter import SystemAdapter
from frontend.controller import ApplicationController

PAGE_NAMES: tuple[str, ...] = (
    "Dashboard",
    "Screener",
    "Portfolio",
    "Backtesting",
    "Intelligence",
    "Reports",
    "Settings",
)


_PYPROJECT_PATTERN = re.compile(r'^\s*version\s*=\s*"([^"]+)"', re.MULTILINE)
_VERSION_FALLBACK = "0.0.0"
_DEFAULT_APP_NAME = "ZIME"


def _project_root() -> Path:
    return Path(__file__).resolve().parents[2]


def read_application_version(pyproject_path: Path | None = None) -> str:
    path = pyproject_path or (_project_root() / "pyproject.toml")
    try:
        text = path.read_text(encoding="utf-8")
    except OSError:
        text = ""
    if text:
        match = _PYPROJECT_PATTERN.search(text)
        if match:
            return match.group(1)
    try:
        with path.open("rb") as fh:
            data = tomllib.load(fh)
        project = data.get("project", {}) if isinstance(data, dict) else {}
        version = project.get("version")
        if isinstance(version, str) and version:
            return version
    except (OSError, tomllib.TOMLDecodeError, UnicodeDecodeError):
        pass
    return _VERSION_FALLBACK


def read_git_branch(project_root: Path | None = None) -> str | None:
    root = project_root or _project_root()
    head_file = root / ".git" / "HEAD"
    if not head_file.exists():
        return None
    try:
        head = head_file.read_text(encoding="utf-8").strip()
    except OSError:
        return None
    if not head:
        return None
    if head.startswith("ref:"):
        ref = head.split(":", 1)[1].strip()
        return ref.split("/")[-1] or None
    return head[:7]


def read_git_short_hash(project_root: Path | None = None) -> str | None:
    root = project_root or _project_root()
    try:
        completed = subprocess.run(
            ["git", "rev-parse", "--short", "HEAD"],
            cwd=str(root),
            capture_output=True,
            text=True,
            timeout=2,
            check=False,
        )
    except (OSError, subprocess.TimeoutExpired, ValueError):
        return None
    if completed.returncode != 0:
        return None
    return completed.stdout.strip() or None


def _detect_build() -> str:
    short_hash = read_git_short_hash()
    if short_hash:
        return short_hash
    timestamp = datetime.utcnow().strftime("%Y%m%d")
    return f"local-{timestamp}"


def _resolve_page_name(index: int) -> str:
    if 0 <= index < len(PAGE_NAMES):
        return PAGE_NAMES[index]
    return "Unknown"


def _read_latest_lifecycle_timestamp(log_path: Path) -> str | None:
    if not log_path.exists():
        return None
    try:
        with log_path.open("r", encoding="utf-8", errors="replace") as fh:
            tail_lines = fh.readlines()[-200:]
    except OSError:
        return None
    for line in reversed(tail_lines):
        if "Application started" in line or "Application closed" in line:
            timestamp = line.split(" INFO ", 1)[0]
            return timestamp.strip()
    return None


class DashboardAdapter:
    """Adapts the controller + system into a render-friendly DashboardSummary.

    No business logic; only reads state from the controller and the file
    system.
    """

    def __init__(
        self,
        controller: ApplicationController | None = None,
        system_adapter: SystemAdapter | None = None,
        *,
        current_page_index: int = 0,
    ) -> None:
        self._controller = controller
        self._system_adapter = system_adapter or SystemAdapter(controller=controller)
        self._current_page_index = int(current_page_index)

    def set_current_page_index(self, index: int) -> None:
        self._current_page_index = max(0, int(index))

    def collect(self) -> DashboardSummary:
        controller = self._controller
        system_status = self._system_adapter.collect()

        theme = "dark"
        size_tuple: tuple[int, int] = (1400, 900)
        position_tuple: tuple[int, int] = (100, 80)
        last_page_index = 0
        if controller is not None:
            loaded = controller.settings.ensure_loaded()
            theme = loaded.theme
            size = loaded.size
            position = loaded.position
            size_tuple = (int(size.width()), int(size.height()))
            position_tuple = (int(position[0]), int(position[1]))
            last_page_index = int(loaded.last_opened_page)

        application_version = read_application_version()
        branch = read_git_branch()
        build = _detect_build()
        application_name = _DEFAULT_APP_NAME
        try:
            from PySide6.QtWidgets import QApplication

            qapp_name = QApplication.applicationName()
            if isinstance(qapp_name, str) and qapp_name:
                application_name = qapp_name
        except Exception:
            pass

        log_path = Path(system_status.log_file_path)
        last_start = _read_latest_lifecycle_timestamp(log_path) or "n/a"

        return DashboardSummary(
            application_version=application_version,
            application_name=application_name,
            branch=branch,
            build=build,
            theme=theme,
            window_size=size_tuple,
            window_position=position_tuple,
            current_datetime=SystemAdapter.current_datetime_iso(),
            current_page=_resolve_page_name(self._current_page_index),
            current_page_index=self._current_page_index,
            last_start=last_start,
            last_opened_page=_resolve_page_name(last_page_index),
            log_file_path=system_status.log_file_path,
            system=system_status,
        )

    @staticmethod
    def page_names() -> tuple[str, ...]:
        return PAGE_NAMES
