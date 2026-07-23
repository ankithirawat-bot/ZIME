from __future__ import annotations

from typing import Any

from PySide6.QtCore import Qt
from PySide6.QtGui import QColor
from PySide6.QtWidgets import (
    QComboBox,
    QFrame,
    QHBoxLayout,
    QHeaderView,
    QLabel,
    QPushButton,
    QTableWidget,
    QTableWidgetItem,
    QVBoxLayout,
    QWidget,
)

from frontend.adapters.screener_adapter import ScreenerAdapter
from frontend.adapters.screener_model import (
    ScreenerResultRow,
    ScreenerViewModel,
)
from frontend.controller import ApplicationController
from frontend.worker import WorkerThread

SCREENER_PAGE_OPENED = "screener.page.opened"
SCREENER_RUN_STARTED = "screener.run.started"
SCREENER_RUN_COMPLETED = "screener.run.completed"
SCREENER_RUN_FAILED = "screener.run.failed"


def _populate_result_row(
    table: QTableWidget,
    row_index: int,
    result: ScreenerResultRow,
) -> None:
    symbol_item = QTableWidgetItem(result.symbol)
    symbol_item.setTextAlignment(Qt.AlignmentFlag.AlignCenter)
    table.setItem(row_index, 0, symbol_item)

    exchange_item = QTableWidgetItem(result.exchange)
    exchange_item.setTextAlignment(Qt.AlignmentFlag.AlignCenter)
    table.setItem(row_index, 1, exchange_item)

    price_text = f"{result.last_price:,.2f}" if result.last_price is not None else "—"
    price_item = QTableWidgetItem(price_text)
    price_item.setTextAlignment(Qt.AlignmentFlag.AlignRight | Qt.AlignmentFlag.AlignVCenter)
    table.setItem(row_index, 2, price_item)

    chg_text = f"{result.change_pct:+.2f}%" if result.change_pct is not None else "—"
    chg_item = QTableWidgetItem(chg_text)
    chg_item.setTextAlignment(Qt.AlignmentFlag.AlignRight | Qt.AlignmentFlag.AlignVCenter)
    if result.change_pct is not None:
        color = QColor("#34C77B") if result.change_pct >= 0 else QColor("#FF6B6B")
        chg_item.setForeground(color)
    table.setItem(row_index, 3, chg_item)

    vol_text = f"{result.volume:,}" if result.volume is not None else "—"
    vol_item = QTableWidgetItem(vol_text)
    vol_item.setTextAlignment(Qt.AlignmentFlag.AlignRight | Qt.AlignmentFlag.AlignVCenter)
    table.setItem(row_index, 4, vol_item)

    status_text = "PASS" if result.passed else "FAIL"
    status_item = QTableWidgetItem(status_text)
    status_item.setTextAlignment(Qt.AlignmentFlag.AlignCenter)
    status_color = QColor("#34C77B") if result.passed else QColor("#FF6B6B")
    status_item.setForeground(status_color)
    table.setItem(row_index, 5, status_item)


class ScreenerView(QWidget):
    def __init__(
        self,
        parent: QWidget | None = None,
        controller: ApplicationController | None = None,
    ) -> None:
        super().__init__(parent)
        self._controller = controller
        self._adapter = ScreenerAdapter(controller=controller)
        self._view_model: ScreenerViewModel | None = None
        self._is_running = False
        self._log = controller.logger if controller is not None else None
        self._bus = controller.event_bus if controller is not None else None

        root = QVBoxLayout(self)
        root.setContentsMargins(24, 22, 24, 22)
        root.setSpacing(16)

        self._build_header(root)
        self._build_filter_panel(root)
        self._build_results_table(root)
        self._build_status_panel(root)

        self._publish_event(SCREENER_PAGE_OPENED)
        if self._log:
            self._log.info("Screener page opened")

        self._refresh_view()

    def _publish_event(self, event_name: str, payload: Any = None) -> None:
        if self._bus is not None:
            try:
                self._bus.publish(event_name, payload)
            except Exception:
                pass

    def _build_header(self, root: QVBoxLayout) -> None:
        header_row = QWidget(self)
        header_layout = QHBoxLayout(header_row)
        header_layout.setContentsMargins(0, 0, 0, 0)
        header_layout.setSpacing(12)

        title_box = QWidget(header_row)
        title_layout = QVBoxLayout(title_box)
        title_layout.setContentsMargins(0, 0, 0, 0)
        title_layout.setSpacing(2)
        self._title_label = QLabel("Screener", title_box)
        self._title_label.setObjectName("screenerTitle")
        self._subtitle_label = QLabel(
            "Universe scanning and filtering tools.",
            title_box,
        )
        self._subtitle_label.setObjectName("screenerSubtitle")
        title_layout.addWidget(self._title_label)
        title_layout.addWidget(self._subtitle_label)
        header_layout.addWidget(title_box, 1)

        self._run_button = QPushButton("Run Screen", header_row)
        self._run_button.setObjectName("screenerRunButton")
        self._run_button.setCursor(Qt.CursorShape.PointingHandCursor)
        self._run_button.setMinimumWidth(140)
        self._run_button.clicked.connect(self._on_run_screen)
        header_layout.addWidget(
            self._run_button, 0, Qt.AlignmentFlag.AlignVCenter
        )

        self._run_button.setEnabled(True)

        root.addWidget(header_row)

    def _build_filter_panel(self, root: QVBoxLayout) -> None:
        self._filter_frame = QFrame(self)
        self._filter_frame.setObjectName("screenerFilterPanel")
        filter_layout = QHBoxLayout(self._filter_frame)
        filter_layout.setContentsMargins(16, 12, 16, 12)
        filter_layout.setSpacing(12)

        cat_label = QLabel("Category:", self._filter_frame)
        cat_label.setObjectName("screenerFilterLabel")
        filter_layout.addWidget(cat_label)

        self._category_combo = QComboBox(self._filter_frame)
        self._category_combo.setObjectName("screenerCategoryCombo")
        self._category_combo.addItems(
            ["All", "fundamental", "technical", "price", "liquidity", "custom"]
        )
        self._category_combo.setMinimumWidth(120)
        filter_layout.addWidget(self._category_combo)

        op_label = QLabel("Operator:", self._filter_frame)
        op_label.setObjectName("screenerFilterLabel")
        filter_layout.addWidget(op_label)

        self._operator_combo = QComboBox(self._filter_frame)
        self._operator_combo.setObjectName("screenerOperatorCombo")
        self._operator_combo.addItems(
            [">", ">=", "<", "<=", "==", "!="]
        )
        self._operator_combo.setMinimumWidth(100)
        filter_layout.addWidget(self._operator_combo)

        val_label = QLabel("Value:", self._filter_frame)
        val_label.setObjectName("screenerFilterLabel")
        filter_layout.addWidget(val_label)

        self._value_combo = QComboBox(self._filter_frame)
        self._value_combo.setObjectName("screenerValueCombo")
        self._value_combo.setEditable(True)
        self._value_combo.setMinimumWidth(140)
        self._value_combo.addItems(["5000", "10000", "50000", "100000"])
        filter_layout.addWidget(self._value_combo, 1)

        self._apply_filter_button = QPushButton("Apply", self._filter_frame)
        self._apply_filter_button.setObjectName("screenerApplyFilterButton")
        self._apply_filter_button.setCursor(Qt.CursorShape.PointingHandCursor)
        self._apply_filter_button.clicked.connect(self._refresh_view)
        filter_layout.addWidget(self._apply_filter_button)

        root.addWidget(self._filter_frame)

    def _build_results_table(self, root: QVBoxLayout) -> None:
        table_container = QWidget(self)
        table_layout = QVBoxLayout(table_container)
        table_layout.setContentsMargins(0, 0, 0, 0)
        table_layout.setSpacing(4)

        table_header = QLabel("Results", table_container)
        table_header.setObjectName("screenerResultsHeader")
        table_layout.addWidget(table_header)

        self._results_table = QTableWidget(table_container)
        self._results_table.setObjectName("screenerResultsTable")
        self._results_table.setColumnCount(6)
        self._results_table.setHorizontalHeaderLabels(
            ["Symbol", "Exchange", "Price", "Change", "Volume", "Status"]
        )
        self._results_table.horizontalHeader().setStretchLastSection(True)
        self._results_table.horizontalHeader().setSectionResizeMode(
            QHeaderView.ResizeMode.Stretch
        )
        self._results_table.setSelectionBehavior(QTableWidget.SelectionBehavior.SelectRows)
        self._results_table.setAlternatingRowColors(True)
        self._results_table.setEditTriggers(QTableWidget.EditTrigger.NoEditTriggers)
        self._results_table.verticalHeader().setVisible(False)

        table_layout.addWidget(self._results_table, 1)
        root.addWidget(table_container, 1)

    def _build_status_panel(self, root: QVBoxLayout) -> None:
        self._status_frame = QFrame(self)
        self._status_frame.setObjectName("screenerStatusPanel")
        status_layout = QHBoxLayout(self._status_frame)
        status_layout.setContentsMargins(16, 10, 16, 10)
        status_layout.setSpacing(24)

        self._state_label = QLabel("Idle", self._status_frame)
        self._state_label.setObjectName("screenerStateLabel")
        status_layout.addWidget(self._state_label)

        self._time_label = QLabel("", self._status_frame)
        self._time_label.setObjectName("screenerTimeLabel")
        status_layout.addWidget(self._time_label)

        self._count_label = QLabel("", self._status_frame)
        self._count_label.setObjectName("screenerCountLabel")
        status_layout.addWidget(self._count_label)

        status_layout.addStretch(1)

        controller_icon = QLabel("●", self._status_frame)
        controller_icon.setObjectName("screenerControllerIcon")
        controller_icon.setStyleSheet("color: #34C77B;")
        status_layout.addWidget(controller_icon)
        self._controller_label = QLabel("running", self._status_frame)
        self._controller_label.setObjectName("screenerControllerLabel")
        status_layout.addWidget(self._controller_label)

        bus_icon = QLabel("●", self._status_frame)
        bus_icon.setObjectName("screenerBusIcon")
        bus_icon.setStyleSheet("color: #34C77B;")
        status_layout.addWidget(bus_icon)
        self._bus_label = QLabel("available", self._status_frame)
        self._bus_label.setObjectName("screenerBusLabel")
        status_layout.addWidget(self._bus_label)

        worker_icon = QLabel("●", self._status_frame)
        worker_icon.setObjectName("screenerWorkerIcon")
        worker_icon.setStyleSheet("color: #34C77B;")
        status_layout.addWidget(worker_icon)
        self._worker_label = QLabel("available", self._status_frame)
        self._worker_label.setObjectName("screenerWorkerLabel")
        status_layout.addWidget(self._worker_label)

        root.addWidget(self._status_frame)

    def _refresh_view(self) -> None:
        view_model = self._adapter.collect()
        self._view_model = view_model
        self._render_results(view_model)
        self._render_status(view_model)

    def _on_run_screen(self) -> None:
        if self._is_running:
            return
        self._is_running = True
        self._run_button.setEnabled(False)
        self._run_button.setText("Running…")

        self._publish_event(SCREENER_RUN_STARTED)
        if self._log:
            self._log.info("Screen started")

        self._state_label.setText("Running…")

        self._worker = WorkerThread(task=self._run_screen_task)
        self._worker.worker_finished.connect(self._on_screen_completed)
        self._worker.worker_error.connect(self._on_screen_failed)
        self._worker.start()

    def _run_screen_task(self, w: Any) -> None:
        del w
        import time  # noqa: PLC0415

        time.sleep(0.05)
        return self._adapter.execute(filters=self._view_model.filters if self._view_model else ())

    def _on_screen_completed(self) -> None:
        self._is_running = False
        self._run_button.setEnabled(True)
        self._run_button.setText("Run Screen")

        if self._worker is not None:
            worker_obj = self._worker.worker()
            result = getattr(worker_obj, "_result", None)
        else:
            result = None

        if result is None:
            result = self._adapter.execute()

        self._view_model = result
        self._render_results(result)
        self._render_status(result)

        self._publish_event(SCREENER_RUN_COMPLETED, payload={"symbols": result.result_count()})
        if self._log:
            self._log.info("Screen completed with %d results in %.3fs", result.result_count(), result.status.elapsed_seconds)

    def _on_screen_failed(self, error_msg: str) -> None:
        self._is_running = False
        self._run_button.setEnabled(True)
        self._run_button.setText("Run Screen")

        self._state_label.setText("Failed")
        self._publish_event(SCREENER_RUN_FAILED, payload={"error": error_msg})
        if self._log:
            self._log.info("Screen failed: %s", error_msg)

    def _render_results(self, view_model: ScreenerViewModel) -> None:
        results = view_model.results
        self._results_table.setRowCount(len(results))
        for idx, result_row in enumerate(results):
            _populate_result_row(self._results_table, idx, result_row)

    def _render_status(self, view_model: ScreenerViewModel) -> None:
        status = view_model.status
        self._state_label.setText(status.state.capitalize() if status.state else "Idle")
        if status.state == "completed" and status.elapsed_seconds > 0:
            self._time_label.setText(f"{status.elapsed_seconds:.3f}s")
        else:
            self._time_label.setText("")
        self._count_label.setText(f"{status.result_count} results" if status.result_count > 0 else "")
        self._controller_label.setText(status.controller_status)
        self._bus_label.setText(status.event_bus_status)
        self._worker_label.setText(status.worker_status)

    @property
    def adapter(self) -> ScreenerAdapter:
        return self._adapter

    @property
    def run_button(self) -> QPushButton:
        return self._run_button

    def refresh(self) -> ScreenerViewModel:
        self._refresh_view()
        if self._view_model is not None:
            return self._view_model
        return self._adapter.collect()

    def current_view_model(self) -> ScreenerViewModel | None:
        return self._view_model
