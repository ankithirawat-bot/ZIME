from __future__ import annotations

from typing import override

from PySide6.QtCore import QSize, Qt
from PySide6.QtGui import QCloseEvent, QKeySequence, QShortcut
from PySide6.QtWidgets import (
    QApplication,
    QHBoxLayout,
    QLabel,
    QMainWindow,
    QStackedWidget,
    QStatusBar,
    QWidget,
)

from frontend.controller import (
    EVENT_APPLICATION_CLOSED,
    EVENT_APPLICATION_SHUTTING_DOWN,
    ApplicationController,
)
from frontend.views.backtesting import BacktestingView
from frontend.views.dashboard import DashboardView
from frontend.views.intelligence import IntelligenceView
from frontend.views.market_overview import MarketOverviewView
from frontend.views.portfolio import PortfolioView
from frontend.views.reporting import ReportingView
from frontend.views.screener import ScreenerView
from frontend.views.settings import SettingsView
from frontend.widgets.navigation import NavigationPanel

STATUS_READY = "Ready"

WINDOW_TITLE = "ZIME"
WINDOW_INITIAL_SIZE = QSize(1400, 900)


class MainWindow(QMainWindow):
    def __init__(
        self,
        application: QApplication | None = None,
        controller: ApplicationController | None = None,
    ) -> None:
        super().__init__()
        self._application = application
        self._controller = controller
        self.setWindowTitle(WINDOW_TITLE)
        self.resize(WINDOW_INITIAL_SIZE)
        self.setMinimumSize(QSize(1024, 640))

        self._status_label = QLabel(STATUS_READY)
        self._status_label.setObjectName("statusBarLabel")

        self._navigation = NavigationPanel(parent=self)
        self._stack = QStackedWidget(self)
        self._stack.setObjectName("contentStack")

        self._pages: tuple[QWidget, ...] = (
            DashboardView(controller=self._controller, page_index=0, parent=self._stack),
            MarketOverviewView(controller=self._controller, parent=self._stack),
            ScreenerView(self._stack, controller=self._controller),
            PortfolioView(self._stack, controller=self._controller),
            BacktestingView(self._stack, controller=self._controller),
            IntelligenceView(self._stack, controller=self._controller),
            ReportingView(self._stack, controller=self._controller),
            SettingsView(self._stack),
        )
        self._dashboard_view = self._pages[0]
        for page in self._pages:
            self._stack.addWidget(page)

        central = QWidget(self)
        central.setObjectName("centralContainer")
        body = QHBoxLayout(central)
        body.setContentsMargins(0, 0, 0, 0)
        body.setSpacing(0)
        body.addWidget(self._navigation)
        body.addWidget(self._stack, 1)
        self.setCentralWidget(central)

        status_bar = QStatusBar(self)
        status_bar.setObjectName("statusBar")
        status_bar.addPermanentWidget(self._status_label, 1)
        self.setStatusBar(status_bar)
        self._status_label.setText(STATUS_READY)

        self._navigation.page_selected.connect(self._on_navigate)
        self._navigation.set_index(0)

        self._install_shortcuts()
        self._wire_controller()

    def _install_shortcuts(self) -> None:
        for index in range(len(self._pages)):
            sequence = QKeySequence(f"Ctrl+{index + 1}")
            shortcut = QShortcut(sequence, self)
            shortcut.setContext(Qt.ShortcutContext.ApplicationShortcut)
            shortcut.activated.connect(lambda i=index: self._navigation.set_index(i))

    def _wire_controller(self) -> None:
        if self._controller is None:
            return
        bus = self._controller.event_bus
        try:
            bus.subscribe(EVENT_APPLICATION_SHUTTING_DOWN, self._on_shutting_down)
            bus.subscribe(EVENT_APPLICATION_CLOSED, self._on_application_closed)
        except ValueError:
            pass

    def _on_shutting_down(self, _event_name: str, _payload: object) -> None:
        self._persist_window_state(force=True)

    def _on_application_closed(self, _event_name: str, _payload: object) -> None:
        self._persist_window_state(force=True)

    def restore_desktop_state(self, *, last_page: int = 0) -> None:
        if self._controller is None:
            return
        settings = self._controller.settings.ensure_loaded()
        size = settings.size
        if size.width() >= self.minimumWidth() and size.height() >= self.minimumHeight():
            self.resize(size)
        position = settings.position
        self.move(position[0], position[1])
        if 0 <= last_page < self._stack.count():
            self._navigation.set_index(last_page)
            self._stack.setCurrentIndex(last_page)

    def _persist_window_state(self, *, force: bool = False) -> None:
        if self._controller is None:
            return
        if not force and not self.isVisible():
            return
        self._controller.save_window_state(
            size=self.size(),
            position=self.pos(),
            last_page=self._stack.currentIndex(),
        )

    def _on_navigate(self, index: int) -> None:
        if 0 <= index < self._stack.count():
            self._stack.setCurrentIndex(index)
            self._status_label.setText(STATUS_READY)
            self._persist_window_state()
            if index == 0:
                self._dashboard_view.set_current_page_index(index)
                self._dashboard_view.refresh()

    def current_page(self) -> QWidget:
        return self._stack.currentWidget()

    @override
    def closeEvent(self, event: QCloseEvent) -> None:
        self._persist_window_state(force=True)
        super().closeEvent(event)
