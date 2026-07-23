from __future__ import annotations

from collections.abc import Iterable
from pathlib import Path
from typing import Any

from PySide6.QtCore import QSize, Qt
from PySide6.QtGui import QIcon, QPixmap
from PySide6.QtWidgets import QFrame, QGridLayout, QLabel, QVBoxLayout, QWidget

ICONS_DIR: Path = Path(__file__).resolve().parents[2] / "resources" / "icons"


class CardWidget(QFrame):
    """Reusable QFrame-based card container for dashboard sections.

    Holds a title (with optional icon) and a key/value grid. Pure presentation:
    no business logic, only render-time data injection.
    """

    def __init__(
        self,
        title: str,
        *,
        icon_name: str | None = None,
        parent: QWidget | None = None,
    ) -> None:
        super().__init__(parent)
        self.setObjectName("dashboardCard")
        self.setFrameShape(QFrame.Shape.NoFrame)
        self.setProperty("cardTitle", title)

        self._title_label = QLabel(title, self)
        self._title_label.setObjectName("cardTitleLabel")
        self._title_label.setTextInteractionFlags(Qt.TextInteractionFlag.NoTextInteraction)

        icon = _load_icon(icon_name)
        self._icon_label: QLabel | None = None
        if icon is not None and not icon.isNull():
            self._icon_label = QLabel(self)
            self._icon_label.setObjectName("cardIconLabel")
            self._icon_label.setPixmap(icon.pixmap(QSize(18, 18)))

        title_row = QWidget(self)
        title_layout = QGridLayout(title_row)
        title_layout.setContentsMargins(0, 0, 0, 0)
        title_layout.setHorizontalSpacing(8)
        if self._icon_label is not None:
            title_layout.addWidget(self._icon_label, 0, 0, Qt.AlignmentFlag.AlignVCenter)
            title_layout.addWidget(self._title_label, 0, 1, Qt.AlignmentFlag.AlignVCenter)
            title_layout.setColumnStretch(1, 1)
        else:
            title_layout.addWidget(self._title_label, 0, 0)
            title_layout.setColumnStretch(0, 1)

        self._grid_widget = QWidget(self)
        self._grid_layout = QGridLayout(self._grid_widget)
        self._grid_layout.setHorizontalSpacing(12)
        self._grid_layout.setVerticalSpacing(6)
        self._grid_layout.setContentsMargins(0, 0, 0, 0)

        outer = QVBoxLayout(self)
        outer.setContentsMargins(16, 14, 16, 14)
        outer.setSpacing(12)
        outer.addWidget(title_row)
        outer.addWidget(self._grid_widget, 1)
        self.setLayout(outer)

        self._row_keys: list[QLabel] = []
        self._row_values: list[QLabel] = []

    @staticmethod
    def _make_label(text: str, *, object_name: str) -> QLabel:
        label = QLabel(text)
        label.setObjectName(object_name)
        label.setTextInteractionFlags(Qt.TextInteractionFlag.TextSelectableByMouse)
        label.setWordWrap(True)
        return label

    def update_rows(self, rows: Iterable[tuple[str, str]]) -> None:
        new_rows = list(rows)
        while self._grid_layout.count():
            item = self._grid_layout.takeAt(0)
            widget = item.widget() if item is not None else None
            if widget is not None:
                widget.deleteLater()
        self._row_keys.clear()
        self._row_values.clear()
        for index, (key, value) in enumerate(new_rows):
            value_text = value if value not in (None, "") else "—"
            key_label = self._make_label(str(key), object_name="cardRowKey")
            value_label = self._make_label(str(value_text), object_name="cardRowValue")
            self._grid_layout.addWidget(key_label, index, 0)
            self._grid_layout.addWidget(value_label, index, 1)
            self._row_keys.append(key_label)
            self._row_values.append(value_label)
        self._grid_layout.setColumnStretch(0, 0)
        self._grid_layout.setColumnStretch(1, 1)


def _load_icon(name: str | None) -> QIcon | None:
    if not name:
        return None
    candidate = ICONS_DIR / name
    if not candidate.exists():
        return None
    pixmap = QPixmap(str(candidate))
    if pixmap.isNull():
        return None
    return QIcon(pixmap)


def build_icon_or_none(name: str | None) -> QIcon | None:
    return _load_icon(name)


def qss_safe(value: str) -> str:
    """Escape characters that Qt's QSS parser would treat as special."""
    return value.replace("\\", "\\\\").replace('"', '\\"')


def safe_dict(items: dict[str, Any]) -> dict[str, str]:
    return {k: str(v) for k, v in items.items() if v is not None}
