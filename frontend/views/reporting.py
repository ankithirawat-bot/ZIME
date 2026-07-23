"""Reporting & Analytics workspace replacing the placeholder."""

from __future__ import annotations

from PySide6.QtCore import Qt, QTimer, Slot
from PySide6.QtWidgets import (
    QFrame,
    QHBoxLayout,
    QLabel,
    QPushButton,
    QScrollArea,
    QVBoxLayout,
    QWidget,
)

from frontend.viewmodels.reporting_viewmodels import ReportingViewModel
from frontend.widgets import (
    AnalyticsSummaryCard,
    ChartPlaceholderWidget,
    PerformanceMetricsGrid,
    ReportStatusCard,
    StrategyComparisonTable,
)


class ReportingView(QWidget):
    def __init__(self, stack: QWidget, controller, parent: QWidget | None = None) -> None:
        super().__init__(parent)
        self.setObjectName("ReportingWorkspace")
        self._stack = stack
        self._controller = controller
        self._adapter = controller.get_reporting_adapter()

        self._layout = QVBoxLayout(self)
        self._layout.setContentsMargins(8, 8, 8, 8)
        self._layout.setSpacing(8)

        content = QFrame()
        content.setObjectName("ReportingContentFrame")
        inner = QVBoxLayout(content)
        inner.setContentsMargins(0, 0, 0, 0)

        scroll = QScrollArea()
        scroll.setWidgetResizable(True)
        scroll.setFrameShape(QFrame.NoFrame)
        scroll.setVerticalScrollBarPolicy(Qt.ScrollBarPolicy.ScrollBarAsNeeded)
        scroll.setHorizontalScrollBarPolicy(Qt.ScrollBarPolicy.ScrollBarAsNeeded)
        scroll.setWidget(content)
        self._layout.addWidget(scroll)

        self._header = QLabel("Reporting & Analytics Workspace")
        self._header.setProperty("class", "workspaceTitleLabel")
        inner.addWidget(self._header)

        # Analytics Summary Section
        self._analytics_card = AnalyticsSummaryCard()
        inner.addWidget(self._analytics_card)

        inner.addSpacing(16)

        # Performance Metrics Section
        self._metrics_grid = PerformanceMetricsGrid()
        inner.addWidget(self._metrics_grid)

        inner.addSpacing(16)

        # Strategy Comparison Section
        self._strategy_table = StrategyComparisonTable()
        inner.addWidget(self._strategy_table)

        inner.addSpacing(16)

        # Charts Row: Equity Curve | Monthly Returns
        charts_row = QHBoxLayout()
        charts_row.setSpacing(12)
        charts_row.addWidget(ChartPlaceholderWidget("Equity Curve"), stretch=1)
        charts_row.addWidget(ChartPlaceholderWidget("Monthly Returns"), stretch=1)
        inner.addLayout(charts_row)

        # Charts Row: Drawdown | Allocation
        charts_row2 = QHBoxLayout()
        charts_row2.setSpacing(12)
        charts_row2.addWidget(ChartPlaceholderWidget("Drawdown"), stretch=1)
        charts_row2.addWidget(ChartPlaceholderWidget("Allocation"), stretch=1)
        inner.addLayout(charts_row2)

        inner.addSpacing(16)

        # Export / Status Footer
        footer = QFrame()
        footer.setObjectName("ReportFooter")
        f_layout = QHBoxLayout(footer)
        f_layout.setContentsMargins(0, 0, 0, 0)
        f_layout.setSpacing(8)

        self._export_csv = QPushButton("Export CSV")
        self._export_pdf = QPushButton("Export PDF")
        self._export_csv.setAutoDefault(False)
        self._export_pdf.setAutoDefault(False)
        self._export_csv.clicked.connect(lambda: self._publish_export("csv"))
        self._export_pdf.clicked.connect(lambda: self._publish_export("pdf"))

        f_layout.addStretch()
        f_layout.addWidget(self._export_csv)
        f_layout.addWidget(self._export_pdf)
        f_layout.addSpacing(12)

        self._status_card = ReportStatusCard()
        f_layout.addWidget(self._status_card, stretch=1)
        inner.addWidget(footer)

        # schedule auto-refresh (shorter interval for probe speed)
        self._refresh_timer = QTimer(self)
        self._refresh_timer.timeout.connect(self.refresh)
        self._refresh_timer.start(30_000)

        # initial load
        self.update_view(self._adapter.sample_view_model())

        # publish event
        self._controller.event_bus.publish(
            "reporting.page.opened",
            payload={"controller_status": self._controller.status},
        )

    def current_view_model(self) -> ReportingViewModel | None:
        return getattr(self, "_vm", None)

    @Slot()
    def refresh(self) -> None:
        from frontend.worker import WorkerThread

        self._controller.event_bus.publish("reporting.refresh.started")

        def _task(_w):
            adapter = self._adapter
            try:
                out = adapter.load_view_model()
                self._controller.logger.info("Reporting refreshed")
                self._controller.event_bus.publish("reporting.refresh.completed")
                return out
            except Exception as exc:
                self._controller.event_bus.publish("reporting.refresh.failed", payload={"error": str(exc)[:200]})
                return adapter.sample_view_model()
            finally:
                self._refresh_timer.start(30_000)

        object.__setattr__(self, "_is_refreshing", True)
        thread = WorkerThread(task=_task)
        thread.finished.connect(self._on_refresh_finished)
        thread.start()

    @Slot(object)
    def _on_refresh_finished(self, vm: ReportingViewModel | None | Exception) -> None:
        if not isinstance(vm, ReportingViewModel):
            return
        self.update_view(vm)

    def update_view(self, vm: ReportingViewModel) -> None:
        self._vm = vm
        if vm.analytics:
            self._analytics_card.set_analytics(vm.analytics)
        if vm.metrics:
            self._metrics_grid.set_metrics(vm.metrics)
        if vm.strategies:
            self._strategy_table.set_strategies(vm.strategies)
        if vm.status:
            self._status_card.set_status(vm.status)

    def _publish_export(self, fmt: str) -> None:
        self._controller.event_bus.publish("reporting.export.requested", payload={"format": fmt})
