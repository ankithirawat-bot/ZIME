from __future__ import annotations

from PySide6.QtCore import Qt
from PySide6.QtWidgets import QLabel, QVBoxLayout, QWidget


class SettingsView(QWidget):
    def __init__(self, parent: QWidget | None = None) -> None:
        super().__init__(parent)
        self._title = QLabel("Settings")
        self._title.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self._title.setObjectName("placeholderTitle")

        self._subtitle = QLabel("Application preferences and integrations will appear here.")
        self._subtitle.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self._subtitle.setObjectName("placeholderSubtitle")

        layout = QVBoxLayout(self)
        layout.setContentsMargins(40, 40, 40, 40)
        layout.addStretch(1)
        layout.addWidget(self._title)
        layout.addWidget(self._subtitle)
        layout.addStretch(1)
