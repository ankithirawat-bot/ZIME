"""Report status card showing backend and refresh info."""

from __future__ import annotations

from datetime import datetime

from PySide6.QtWidgets import QFrame, QLabel, QVBoxLayout, QWidget


class ReportStatusCard(QWidget):
    def __init__(self, parent: QWidget | None = None) -> None:
        super().__init__(parent)
        self.setObjectName("ReportStatusCard")
        self._layout = QVBoxLayout(self)
        self._layout.setContentsMargins(4, 4, 4, 4)
        self._frame = QFrame()
        self._layout.addWidget(self._frame)
        inner = QVBoxLayout(self._frame)
        inner.setSpacing(6)

        self._status_header = QLabel("Execution Status")
        self._status_header.setProperty("class", "sectionTitleLabel")
        self._backend_label = QLabel("Backend: ready")
        self._data_label = QLabel("Data: healthy")
        self._refresh_label = QLabel("Last Refresh: never")
        self._available_reports = QLabel("Available Reports: none")

        inner.addWidget(self._status_header)
        inner.addWidget(self._backend_label)
        inner.addWidget(self._data_label)
        inner.addWidget(self._refresh_label)
        inner.addWidget(self._available_reports)
        inner.addSpacing(8)

    def set_status(self, status) -> None:
        self._backend_label.setText(f"Backend: {status.backend_status}")
        self._data_label.setText(f"Data: {status.data_status}")
        ts = (
            datetime.fromisoformat(status.last_refresh_utc[:19]).strftime("%Y-%m-%d %H:%M:%S %Z")
            if status.last_refresh_utc
            else "never"
        )
        self._refresh_label.setText(f"Last Refresh: {ts}")
        replist = ", ".join(status.available_reports) if status.available_reports else "none"
        self._available_reports.setText(f"Available Reports: {replist}")
