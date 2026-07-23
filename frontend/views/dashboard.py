from __future__ import annotations

from PySide6.QtCore import Qt, QTimer
from PySide6.QtWidgets import (
    QGridLayout,
    QLabel,
    QSizePolicy,
    QVBoxLayout,
    QWidget,
)

from frontend.adapters.dashboard_adapter import DashboardAdapter
from frontend.adapters.models import DashboardSummary
from frontend.controller import ApplicationController
from frontend.widgets.cards import CardWidget

REFRESH_INTERVAL_MS = 30_000


class DashboardView(QWidget):
    """Functional Dashboard with reusable cards.

    All business state is collected by ``DashboardAdapter``. The view contains
    only render and orchestration code, and is intentionally U(controller)-
    driven.
    """

    def __init__(
        self,
        controller: ApplicationController | None = None,
        *,
        page_index: int = 0,
        parent: QWidget | None = None,
    ) -> None:
        super().__init__(parent)
        self._controller = controller
        self._adapter = DashboardAdapter(
            controller=controller,
            current_page_index=page_index,
        )
        self._summary: DashboardSummary | None = None
        self._current_page_index = page_index

        root = QVBoxLayout(self)
        root.setContentsMargins(24, 22, 24, 22)
        root.setSpacing(16)

        self._header_label = QLabel("Dashboard", self)
        self._header_label.setObjectName("dashboardHeader")
        self._header_label.setAlignment(Qt.AlignmentFlag.AlignLeft | Qt.AlignmentFlag.AlignVCenter)
        root.addWidget(self._header_label)

        self._cards_grid = QGridLayout()
        self._cards_grid.setContentsMargins(0, 0, 0, 0)
        self._cards_grid.setHorizontalSpacing(16)
        self._cards_grid.setVerticalSpacing(16)
        self._cards_grid.setColumnStretch(0, 1)
        self._cards_grid.setColumnStretch(1, 1)
        self._cards_grid.setColumnMinimumWidth(0, 320)
        self._cards_grid.setColumnMinimumWidth(1, 320)

        self._application_card = CardWidget("Application", icon_name=None, parent=self)
        self._system_card = CardWidget("System", icon_name=None, parent=self)
        self._status_card = CardWidget("Status", icon_name=None, parent=self)
        self._recent_card = CardWidget("Recent Activity", icon_name=None, parent=self)

        for card in (self._application_card, self._system_card, self._status_card, self._recent_card):
            size_policy = card.sizePolicy()
            size_policy.setHorizontalPolicy(QSizePolicy.Policy.Expanding)
            size_policy.setVerticalPolicy(QSizePolicy.Policy.Preferred)
            card.setSizePolicy(size_policy)
            card.setMinimumHeight(180)

        self._cards_grid.addWidget(self._application_card, 0, 0)
        self._cards_grid.addWidget(self._system_card, 0, 1)
        self._cards_grid.addWidget(self._status_card, 1, 0)
        self._cards_grid.addWidget(self._recent_card, 1, 1)

        grid_container = QWidget(self)
        grid_container.setLayout(self._cards_grid)
        root.addWidget(grid_container, 1)

        footer = QWidget(self)
        footer_layout = QVBoxLayout(footer)
        footer_layout.setContentsMargins(0, 0, 0, 0)
        footer_layout.setSpacing(4)
        self._footer_label = QLabel("Updating automatically every 30 seconds.", self)
        self._footer_label.setObjectName("dashboardFooterLabel")
        self._footer_label.setAlignment(Qt.AlignmentFlag.AlignLeft)
        footer_layout.addWidget(self._footer_label)
        root.addWidget(footer)

        self._timer = QTimer(self)
        self._timer.setInterval(REFRESH_INTERVAL_MS)
        self._timer.setTimerType(Qt.TimerType.CoarseTimer)
        self._timer.timeout.connect(self.refresh)
        self._timer.start()
        self.refresh()

    def set_current_page_index(self, index: int) -> None:
        self._current_page_index = max(0, int(index))
        self._adapter.set_current_page_index(self._current_page_index)
        self.refresh()

    @property
    def current_page_index(self) -> int:
        return self._current_page_index

    def refresh(self) -> DashboardSummary:
        self._adapter.set_current_page_index(self._current_page_index)
        summary = self._adapter.collect()
        self._summary = summary
        self._render(summary)
        return summary

    def current_summary(self) -> DashboardSummary | None:
        return self._summary

    def _render(self, summary: DashboardSummary) -> None:
        self._application_card.update_rows(self._application_rows(summary))
        self._system_card.update_rows(self._system_rows(summary))
        self._status_card.update_rows(self._status_rows(summary))
        self._recent_card.update_rows(self._recent_rows(summary))
        self._header_label.setText(
            f"Dashboard  ·  {summary.current_datetime}"
        )
        self._footer_label.setText(
            f"Refreshing every {REFRESH_INTERVAL_MS // 1000} seconds · {summary.application_name} v{summary.application_version}"
        )

    @staticmethod
    def _application_rows(summary: DashboardSummary) -> list[tuple[str, str]]:
        return [
            ("Version", summary.application_version),
            ("Branch", summary.branch or "n/a"),
            ("Build", summary.build),
        ]

    @staticmethod
    def _system_rows(summary: DashboardSummary) -> list[tuple[str, str]]:
        sys = summary.system
        size_w, size_h = summary.window_size
        pos_x, pos_y = summary.window_position
        return [
            ("Python Version", sys.python_version),
            ("Qt Version", sys.qt_version),
            ("Theme", summary.theme),
            ("Platform", sys.platform),
            ("Window Size", f"{size_w} × {size_h}"),
            ("Window Position", f"({pos_x}, {pos_y})"),
        ]

    @staticmethod
    def _status_rows(summary: DashboardSummary) -> list[tuple[str, str]]:
        sys = summary.system
        return [
            ("Controller", sys.controller_status),
            ("Event Bus", sys.event_bus_status),
            ("Worker", sys.worker_availability),
            ("Logging", sys.logging_status),
            ("Log Level", sys.log_level),
        ]

    @staticmethod
    def _recent_rows(summary: DashboardSummary) -> list[tuple[str, str]]:
        sys = summary.system
        return [
            ("Last Start", summary.last_start),
            ("Last Page", summary.last_opened_page),
            ("Log File", sys.log_file_path),
            (
                "Log Size",
                sys.extensions.get("log_file_size", "—"),
            ),
        ]
