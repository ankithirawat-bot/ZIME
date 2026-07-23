from __future__ import annotations

from typing import Any

from PySide6.QtCore import Qt, QTimer
from PySide6.QtWidgets import (
    QFrame,
    QHBoxLayout,
    QLabel,
    QPushButton,
    QVBoxLayout,
    QWidget,
)

from frontend.adapters.portfolio_adapter import PortfolioAdapter
from frontend.controller import ApplicationController
from frontend.viewmodels.portfolio_viewmodels import PortfolioViewModel
from frontend.widgets.allocation_card import AllocationCard
from frontend.widgets.holdings_table import HoldingsTable
from frontend.widgets.portfolio_summary_card import PortfolioSummaryCard
from frontend.worker import WorkerThread

PORTFOLIO_PAGE_OPENED = "portfolio.page.opened"
PORTFOLIO_REFRESH_STARTED = "portfolio.refresh.started"
PORTFOLIO_REFRESH_COMPLETED = "portfolio.refresh.completed"
PORTFOLIO_REFRESH_FAILED = "portfolio.refresh.failed"

REFRESH_INTERVAL_MS = 30_000


class PortfolioView(QWidget):
    def __init__(
        self,
        parent: QWidget | None = None,
        controller: ApplicationController | None = None,
    ) -> None:
        super().__init__(parent)
        self._controller = controller
        self._adapter = PortfolioAdapter(controller=controller)
        self._view_model: PortfolioViewModel | None = None
        self._is_refreshing = False
        self._log = controller.logger if controller is not None else None
        self._bus = controller.event_bus if controller is not None else None

        root = QVBoxLayout(self)
        root.setContentsMargins(24, 22, 24, 22)
        root.setSpacing(16)

        self._build_header(root)
        self._build_summary(root)
        self._build_holdings(root)
        self._build_allocations(root)
        self._build_performance(root)
        self._build_status(root)

        self._publish_event(PORTFOLIO_PAGE_OPENED)
        if self._log:
            self._log.info("Portfolio page opened")

        self._timer = QTimer(self)
        self._timer.setInterval(REFRESH_INTERVAL_MS)
        self._timer.setTimerType(Qt.TimerType.CoarseTimer)
        self._timer.timeout.connect(self._on_refresh)
        self._timer.start()

        self._on_refresh()

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
        self._title_label = QLabel("Portfolio", title_box)
        self._title_label.setObjectName("portfolioTitle")
        self._subtitle_label = QLabel(
            "Holdings, allocations and exposure.",
            title_box,
        )
        self._subtitle_label.setObjectName("portfolioSubtitle")
        title_layout.addWidget(self._title_label)
        title_layout.addWidget(self._subtitle_label)
        header_layout.addWidget(title_box, 1)

        self._refresh_button = QPushButton("Refresh", header_row)
        self._refresh_button.setObjectName("portfolioRefreshButton")
        self._refresh_button.setCursor(Qt.CursorShape.PointingHandCursor)
        self._refresh_button.setMinimumWidth(100)
        self._refresh_button.clicked.connect(self._on_refresh)
        header_layout.addWidget(self._refresh_button, 0, Qt.AlignmentFlag.AlignVCenter)

        root.addWidget(header_row)

    def _build_summary(self, root: QVBoxLayout) -> None:
        self._summary_card = PortfolioSummaryCard(self)
        root.addWidget(self._summary_card)

    def _build_holdings(self, root: QVBoxLayout) -> None:
        self._holdings_table = HoldingsTable(self)
        root.addWidget(self._holdings_table, 1)

    def _build_allocations(self, root: QVBoxLayout) -> None:
        alloc_row = QWidget(self)
        alloc_layout = QHBoxLayout(alloc_row)
        alloc_layout.setContentsMargins(0, 0, 0, 0)
        alloc_layout.setSpacing(16)

        self._sector_card = AllocationCard("Sector Allocation", alloc_row)
        self._asset_card = AllocationCard("Asset Allocation", alloc_row)
        self._risk_card = AllocationCard("Risk Allocation", alloc_row)

        alloc_layout.addWidget(self._sector_card, 1)
        alloc_layout.addWidget(self._asset_card, 1)
        alloc_layout.addWidget(self._risk_card, 1)

        root.addWidget(alloc_row)

    def _build_performance(self, root: QVBoxLayout) -> None:
        perf_frame = QFrame(self)
        perf_frame.setObjectName("portfolioPerformance")
        perf_layout = QHBoxLayout(perf_frame)
        perf_layout.setContentsMargins(16, 14, 16, 14)
        perf_layout.setSpacing(24)

        self._return_label = self._make_perf_block(perf_layout, "Total Return", "+0.00%")
        self._cagr_label = self._make_perf_block(perf_layout, "CAGR", "—")
        self._sharpe_label = self._make_perf_block(perf_layout, "Sharpe Ratio", "—")
        self._drawdown_label = self._make_perf_block(perf_layout, "Max Drawdown", "—")

        root.addWidget(perf_frame)

    def _make_perf_block(
        self, parent_layout: QHBoxLayout, label_text: str, initial_value: str
    ) -> list[QLabel]:
        block = QWidget(self)
        bl = QVBoxLayout(block)
        bl.setContentsMargins(0, 0, 0, 0)
        bl.setSpacing(2)
        lbl = QLabel(label_text, block)
        lbl.setObjectName("portfolioPerfLabel")
        val = QLabel(initial_value, block)
        val.setObjectName("portfolioPerfValue")
        bl.addWidget(lbl)
        bl.addWidget(val)
        parent_layout.addWidget(block, 1)
        return [lbl, val]

    def _build_status(self, root: QVBoxLayout) -> None:
        self._status_frame = QFrame(self)
        self._status_frame.setObjectName("portfolioStatusPanel")
        status_layout = QHBoxLayout(self._status_frame)
        status_layout.setContentsMargins(16, 10, 16, 10)
        status_layout.setSpacing(24)

        self._connection_label = QLabel("Disconnected", self._status_frame)
        self._connection_label.setObjectName("portfolioConnectionLabel")
        status_layout.addWidget(self._connection_label)

        self._last_refresh_label = QLabel("", self._status_frame)
        self._last_refresh_label.setObjectName("portfolioLastRefreshLabel")
        status_layout.addWidget(self._last_refresh_label)

        holding_count_label = QLabel("Holdings", self._status_frame)
        holding_count_label.setObjectName("portfolioStatusLabel")
        status_layout.addWidget(holding_count_label)
        self._holding_count_label = QLabel("0", self._status_frame)
        self._holding_count_label.setObjectName("portfolioHoldingCountLabel")
        status_layout.addWidget(self._holding_count_label)

        status_layout.addStretch(1)

        ctrl_icon = QLabel("\u25CF", self._status_frame)
        ctrl_icon.setObjectName("portfolioControllerIcon")
        ctrl_icon.setStyleSheet("color: #34C77B;")
        status_layout.addWidget(ctrl_icon)
        self._controller_label = QLabel("running", self._status_frame)
        self._controller_label.setObjectName("portfolioControllerLabel")
        status_layout.addWidget(self._controller_label)

        bus_icon = QLabel("\u25CF", self._status_frame)
        bus_icon.setObjectName("portfolioBusIcon")
        bus_icon.setStyleSheet("color: #34C77B;")
        status_layout.addWidget(bus_icon)
        self._bus_label = QLabel("available", self._status_frame)
        self._bus_label.setObjectName("portfolioBusLabel")
        status_layout.addWidget(self._bus_label)

        wkr_icon = QLabel("\u25CF", self._status_frame)
        wkr_icon.setObjectName("portfolioWorkerIcon")
        wkr_icon.setStyleSheet("color: #34C77B;")
        status_layout.addWidget(wkr_icon)
        self._worker_label = QLabel("available", self._status_frame)
        self._worker_label.setObjectName("portfolioWorkerLabel")
        status_layout.addWidget(self._worker_label)

        root.addWidget(self._status_frame)

    def _on_refresh(self) -> None:
        if self._is_refreshing:
            return
        self._is_refreshing = True
        self._refresh_button.setEnabled(False)
        self._refresh_button.setText("Loading\u2026")

        self._publish_event(PORTFOLIO_REFRESH_STARTED)
        if self._log:
            self._log.info("Portfolio refresh started")

        self._worker = WorkerThread(task=self._refresh_task)
        self._worker.worker_finished.connect(self._on_refresh_completed)
        self._worker.worker_error.connect(self._on_refresh_failed)
        self._worker.start()

    def _refresh_task(self, w: Any) -> None:
        del w
        return self._adapter.refresh()

    def _on_refresh_completed(self) -> None:
        self._is_refreshing = False
        self._refresh_button.setEnabled(True)
        self._refresh_button.setText("Refresh")

        if self._worker is not None:
            worker_obj = self._worker.worker()
            result = getattr(worker_obj, "_result", None)
        else:
            result = None

        if result is None:
            result = self._adapter.refresh()

        self._view_model = result
        self._render(result)

        self._publish_event(PORTFOLIO_REFRESH_COMPLETED, payload={"holdings": result.holding_count})
        if self._log:
            self._log.info("Portfolio refresh completed (%d holdings)", result.holding_count)

    def _on_refresh_failed(self, error_msg: str) -> None:
        self._is_refreshing = False
        self._refresh_button.setEnabled(True)
        self._refresh_button.setText("Refresh")

        self._publish_event(PORTFOLIO_REFRESH_FAILED, payload={"error": error_msg})
        if self._log:
            self._log.info("Portfolio refresh failed: %s", error_msg)

    def _render(self, vm: PortfolioViewModel) -> None:
        self._summary_card.update_from(vm.summary)
        self._holdings_table.update_holdings(vm.holdings)
        self._sector_card.update_from(vm.sector_allocation)
        self._asset_card.update_from(vm.asset_allocation)
        self._risk_card.update_from(vm.risk_allocation)

        self._render_performance(vm)
        self._render_status(vm)

    def _render_performance(self, vm: PortfolioViewModel) -> None:
        p = vm.performance
        self._set_perf_value(self._return_label, f"{p.total_return_pct:+.2f}%")
        if p.cagr is not None:
            self._set_perf_value(self._cagr_label, f"{p.cagr:.2f}%")
        else:
            self._set_perf_value(self._cagr_label, "\u2014")
        if p.sharpe_ratio is not None:
            self._set_perf_value(self._sharpe_label, f"{p.sharpe_ratio:.2f}")
        else:
            self._set_perf_value(self._sharpe_label, "\u2014")
        if p.max_drawdown is not None:
            self._set_perf_value(self._drawdown_label, f"{p.max_drawdown:.2f}%")
        else:
            self._set_perf_value(self._drawdown_label, "\u2014")

    def _set_perf_value(self, block: list[QLabel], text: str) -> None:
        if len(block) >= 2:
            block[1].setText(text)

    def _render_status(self, vm: PortfolioViewModel) -> None:
        self._connection_label.setText(
            f"\u25CF  {'Connected' if vm.connection_status == 'Connected' else 'Disconnected'}"
        )
        self._last_refresh_label.setText(f"Last: {vm.last_refresh}")
        self._holding_count_label.setText(str(vm.holding_count))
        self._controller_label.setText(vm.controller_status)
        self._bus_label.setText(vm.event_bus_status)
        self._worker_label.setText(vm.worker_status)

    @property
    def adapter(self) -> PortfolioAdapter:
        return self._adapter

    def refresh(self) -> PortfolioViewModel:
        self._on_refresh()
        if self._view_model is not None:
            return self._view_model
        return self._adapter.refresh()

    def current_view_model(self) -> PortfolioViewModel | None:
        return self._view_model
