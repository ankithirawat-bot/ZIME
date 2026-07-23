from __future__ import annotations

import json
from dataclasses import asdict, dataclass, field
from pathlib import Path

from PySide6.QtCore import QSize

CONFIG_RELATIVE_PATH = Path("config") / "desktop.json"
SUPPORTED_THEMES: tuple[str, ...] = ("dark", "light")
DEFAULT_THEME = "dark"
DEFAULT_LOG_LEVEL = "INFO"
DEFAULT_WINDOW_WIDTH = 1400
DEFAULT_WINDOW_HEIGHT = 900
DEFAULT_LAST_PAGE = 0


@dataclass
class DesktopSettings:
    theme: str = DEFAULT_THEME
    window_size: dict[str, int] = field(
        default_factory=lambda: {"width": DEFAULT_WINDOW_WIDTH, "height": DEFAULT_WINDOW_HEIGHT}
    )
    window_position: dict[str, int] = field(default_factory=lambda: {"x": 100, "y": 80})
    last_opened_page: int = DEFAULT_LAST_PAGE
    log_level: str = DEFAULT_LOG_LEVEL

    def __post_init__(self) -> None:
        self.theme = self.theme if self.theme in SUPPORTED_THEMES else DEFAULT_THEME
        if not isinstance(self.window_size, dict):
            self.window_size = {"width": DEFAULT_WINDOW_WIDTH, "height": DEFAULT_WINDOW_HEIGHT}
        self.window_size.setdefault("width", DEFAULT_WINDOW_WIDTH)
        self.window_size.setdefault("height", DEFAULT_WINDOW_HEIGHT)
        if not isinstance(self.window_position, dict):
            self.window_position = {"x": 100, "y": 80}
        self.window_position.setdefault("x", 100)
        self.window_position.setdefault("y", 80)
        try:
            page = int(self.last_opened_page)
        except (TypeError, ValueError):
            page = DEFAULT_LAST_PAGE
        self.last_opened_page = max(0, page)
        if not isinstance(self.log_level, str) or not self.log_level:
            self.log_level = DEFAULT_LOG_LEVEL

    def to_dict(self) -> dict[str, object]:
        return asdict(self)

    @classmethod
    def from_dict(cls, data: dict[str, object]) -> DesktopSettings:
        if not isinstance(data, dict):
            return cls()
        last_raw = data.get("last_opened_page", DEFAULT_LAST_PAGE)
        try:
            last_page = int(last_raw) if last_raw is not None else DEFAULT_LAST_PAGE
        except (TypeError, ValueError):
            last_page = DEFAULT_LAST_PAGE
        return cls(
            theme=str(data.get("theme", DEFAULT_THEME)),
            window_size=dict(data.get("window_size") or {}),
            window_position=dict(data.get("window_position") or {}),
            last_opened_page=last_page,
            log_level=str(data.get("log_level", DEFAULT_LOG_LEVEL)),
        )

    @property
    def size(self) -> QSize:
        return QSize(int(self.window_size["width"]), int(self.window_size["height"]))

    @property
    def position(self) -> tuple[int, int]:
        return (int(self.window_position["x"]), int(self.window_position["y"]))


def _default_settings_path(config_path: Path | str | None) -> Path:
    if config_path is None:
        project_root = Path(__file__).resolve().parents[1]
        return project_root / CONFIG_RELATIVE_PATH
    return Path(config_path)


class DesktopSettingsStore:
    def __init__(self, config_path: Path | str | None = None) -> None:
        self._path = _default_settings_path(config_path)
        self._settings: DesktopSettings = DesktopSettings()

    @property
    def path(self) -> Path:
        return self._path

    def ensure_loaded(self) -> DesktopSettings:
        self._path.parent.mkdir(parents=True, exist_ok=True)
        if not self._path.exists():
            self.save()
            return self._settings
        try:
            raw = self._path.read_text(encoding="utf-8")
            data = json.loads(raw) if raw else {}
            self._settings = DesktopSettings.from_dict(data)
        except (json.JSONDecodeError, OSError):
            self._settings = DesktopSettings()
        return self._settings

    def settings(self) -> DesktopSettings:
        return self._settings

    def update(self, **changes: object) -> None:
        current = self._settings.to_dict()
        current.update(changes)
        self._settings = DesktopSettings.from_dict(current)
        self.save()

    def save(self) -> None:
        self._path.parent.mkdir(parents=True, exist_ok=True)
        payload = self._settings.to_dict()
        self._path.write_text(
            json.dumps(payload, indent=2, sort_keys=True),
            encoding="utf-8",
        )
