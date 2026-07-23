from __future__ import annotations

from typing import Any

from PySide6.QtCore import Qt, QTimer
from PySide6.QtWidgets import (
    QFrame,
    QHBoxLayout,
    QLabel,
    QPushButton,
    QScrollArea,
    QVBoxLayout,
    QWidget,
)

from frontend.adapters.intelligence_adapter import IntelligenceAdapter
from frontend.controller import ApplicationController
from frontend.viewmodels.intelligence_viewmodels import IntelligenceViewModel
from frontend.widgets.insight_card import InsightCard
from frontend.widgets.market_health_card import MarketHealthCard
from frontend.widgets.recommendation_card import RecommendationCard
from frontend.widgets.signal_table import SignalTable
from frontend.worker import WorkerThread

INTELLIGENCE_PAGE_OPENED = "intelligence.page.opened"
INTELLIGENCE_REFRESH_STARTED = "intelligence.refresh.started"
INTELLIGENCE_REFRESH_COMPLETED = "intelligence.refresh.completed"
INTELLIGENCE_REFRESH_FAILED = "intelligence.refresh.failed"

REFRESH_INTERVAL_MS = 30_000


class IntelligenceView(QWidget):
    def __init__(
        self,
        parent: QWidget | None = None,
        controller: ApplicationController | None = None,
    ) -> None:
        super().__init__(parent)
        self._controller = controller
        self._adapter = IntelligenceAdapter(controller=controller)
        self._view_model: IntelligenceViewModel | None = None
        self._is_refreshing = False
        self._log = controller.logger if controller is not None else None
        self._bus = controller.event_bus if controller is not None else None

        root = QVBoxLayout(self)
        root.setContentsMargins(24, 22, 24, 22)
        root.setSpacing(16)

        self._build_header(root)
        self._build_summary(root)
        self._build_recommendations(root)
        self._build_signals(root)
        self._build_market_health(root)
        self._build_insights(root)
        self._build_status(root)

        self._publish_event(INTELLIGENCE_PAGE_OPENED)
        if self._log:
            self._log.info("Intelligence page opened")

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
        self._title_label = QLabel("Intelligence", title_box)
        self._title_label.setObjectName("intelligenceTitle")
        self._subtitle_label = QLabel(
            "Market regime, signals and analytics insights.",
            title_box,
        )
        self._subtitle_label.setObjectName("intelligenceSubtitle")
        title_layout.addWidget(self._title_label)
        title_layout.addWidget(self._subtitle_label)
        header_layout.addWidget(title_box, 1)

        self._refresh_button = QPushButton("Refresh", header_row)
        self._refresh_button.setObjectName("intelligenceRefreshButton")
        self._refresh_button.setCursor(Qt.CursorShape.PointingHandCursor)
        self._refresh_button.setMinimumWidth(100)
        self._refresh_button.clicked.connect(self._on_refresh)
        header_layout.addWidget(self._refresh_button, 0, Qt.AlignmentFlag.AlignVCenter)

        root.addWidget(header_row)

    def _build_summary(self, root: QVBoxLayout) -> None:
        self._summary_frame = QFrame(self)
        self._summary_frame.setObjectName("intelligenceSummary")
        summary_layout = QHBoxLayout(self._summary_frame)
        summary_layout.setContentsMargins(16, 14, 16, 14)
        summary_layout.setSpacing(24)

        self._regime_label = self._make_summary_block(summary_layout, "Market Regime", "\u2014")
        self._risk_label = self._make_summary_block(summary_layout, "Risk Level", "\u2014")
        self._score_label = self._make_summary_block(summary_layout, "Overall Score", "\u2014")
        self._last_refresh_label_2 = self._make_summary_block(summary_layout, "Last Refresh", "\u2014")

        root.addWidget(self._summary_frame)

    def _make_summary_block(
        self, parent_layout: QHBoxLayout, label_text: str, initial_value: str
    ) -> list[QLabel]:
        block = QWidget(self)
        bl = QVBoxLayout(block)
        bl.setContentsMargins(0, 0, 0, 0)
        bl.setSpacing(2)
        lbl = QLabel(label_text, block)
        lbl.setObjectName("intelSummaryLabel")
        val = QLabel(initial_value, block)
        val.setObjectName("intelSummaryValue")
        bl.addWidget(lbl)
        bl.addWidget(val)
        parent_layout.addWidget(block, 1)
        return [lbl, val]

    def _build_recommendations(self, root: QVBoxLayout) -> None:
        rec_section = QWidget(self)
        rec_layout = QVBoxLayout(rec_section)
        rec_layout.setContentsMargins(0, 0, 0, 0)
        rec_layout.setSpacing(8)

        rec_header = QLabel("High Conviction Ideas", rec_section)
        rec_header.setObjectName("intelligenceRecHeader")
        rec_layout.addWidget(rec_header)

        scroll = QScrollArea(rec_section)
        scroll.setObjectName("intelligenceRecScroll")
        scroll.setWidgetResizable(True)
        scroll.setFrameShape(QFrame.Shape.NoFrame)

        self._rec_container = QWidget(scroll)
        self._rec_container.setObjectName("intelligenceRecContainer")
        self._rec_container_layout = QVBoxLayout(self._rec_container)
        self._rec_container_layout.setContentsMargins(0, 0, 0, 0)
        self._rec_container_layout.setSpacing(6)
        self._rec_container_layout.addStretch(1)

        scroll.setWidget(self._rec_container)
        rec_layout.addWidget(scroll, 1)

        root.addWidget(rec_section, 1)

    def _build_signals(self, root: QVBoxLayout) -> None:
        self._signal_table = SignalTable(self)
        root.addWidget(self._signal_table)

    def _build_market_health(self, root: QVBoxLayout) -> None:
        self._market_health_card = MarketHealthCard(self)
        root.addWidget(self._market_health_card)

    def _build_insights(self, root: QVBoxLayout) -> None:
        insights_section = QWidget(self)
        insights_layout = QVBoxLayout(insights_section)
        insights_layout.setContentsMargins(0, 0, 0, 0)
        insights_layout.setSpacing(8)

        insights_header = QLabel("Insights", insights_section)
        insights_header.setObjectName("intelligenceInsightsHeader")
        insights_layout.addWidget(insights_header)

        self._insights_container = QWidget(insights_section)
        self._insights_container.setObjectName("intelligenceInsightsContainer")
        self._insights_container_layout = QVBoxLayout(self._insights_container)
        self._insights_container_layout.setContentsMargins(0, 0, 0, 0)
        self._insights_container_layout.setSpacing(6)
        insights_layout.addWidget(self._insights_container)

        root.addWidget(insights_section)

    def _build_status(self, root: QVBoxLayout) -> None:
        self._status_frame = QFrame(self)
        self._status_frame.setObjectName("intelligenceStatusPanel")
        status_layout = QHBoxLayout(self._status_frame)
        status_layout.setContentsMargins(16, 10, 16, 10)
        status_layout.setSpacing(24)

        self._connection_label = QLabel("\u25CF  Disconnected", self._status_frame)
        self._connection_label.setObjectName("intelligenceConnectionLabel")
        status_layout.addWidget(self._connection_label)

        self._last_refresh_label = QLabel("", self._status_frame)
        self._last_refresh_label.setObjectName("intelligenceLastRefreshLabel")
        status_layout.addWidget(self._last_refresh_label)

        rec_count_label = QLabel("Recommendations", self._status_frame)
        rec_count_label.setObjectName("intelligenceStatusLabel")
        status_layout.addWidget(rec_count_label)
        self._rec_count_label = QLabel("0", self._status_frame)
        self._rec_count_label.setObjectName("intelligenceRecCountLabel")
        status_layout.addWidget(self._rec_count_label)

        status_layout.addStretch(1)

        ctrl_icon = QLabel("\u25CF", self._status_frame)
        ctrl_icon.setObjectName("intelligenceControllerIcon")
        ctrl_icon.setStyleSheet("color: #34C77B;")
        status_layout.addWidget(ctrl_icon)
        self._controller_label = QLabel("running", self._status_frame)
        self._controller_label.setObjectName("intelligenceControllerLabel")
        status_layout.addWidget(self._controller_label)

        bus_icon = QLabel("\u25CF", self._status_frame)
        bus_icon.setObjectName("intelligenceBusIcon")
        bus_icon.setStyleSheet("color: #34C77B;")
        status_layout.addWidget(bus_icon)
        self._bus_label = QLabel("available", self._status_frame)
        self._bus_label.setObjectName("intelligenceBusLabel")
        status_layout.addWidget(self._bus_label)

        wkr_icon = QLabel("\u25CF", self._status_frame)
        wkr_icon.setObjectName("intelligenceWorkerIcon")
        wkr_icon.setStyleSheet("color: #34C77B;")
        status_layout.addWidget(wkr_icon)
        self._worker_label = QLabel("available", self._status_frame)
        self._worker_label.setObjectName("intelligenceWorkerLabel")
        status_layout.addWidget(self._worker_label)

        root.addWidget(self._status_frame)

    def _on_refresh(self) -> None:
        if self._is_refreshing:
            return
        self._is_refreshing = True
        self._refresh_button.setEnabled(False)
        self._refresh_button.setText("Loading\u2026")

        self._publish_event(INTELLIGENCE_REFRESH_STARTED)
        if self._log:
            self._log.info("Intelligence refresh started")

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

        self._publish_event(
            INTELLIGENCE_REFRESH_COMPLETED,
            payload={"recommendations": result.recommendation_count},
        )
        if self._log:
            self._log.info("Intelligence refresh completed (%d recommendations)", result.recommendation_count)

    def _on_refresh_failed(self, error_msg: str) -> None:
        self._is_refreshing = False
        self._refresh_button.setEnabled(True)
        self._refresh_button.setText("Refresh")

        self._publish_event(INTELLIGENCE_REFRESH_FAILED, payload={"error": error_msg})
        if self._log:
            self._log.info("Intelligence refresh failed: %s", error_msg)

    def _render(self, vm: IntelligenceViewModel) -> None:
        self._render_summary(vm)
        self._render_recommendations(vm)
        self._signal_table.update_signals(vm.signals)
        self._market_health_card.update_from(vm.market_health)
        self._render_insights(vm)
        self._render_status(vm)

    def _render_summary(self, vm: IntelligenceViewModel) -> None:
        self._set_summary_value(self._regime_label, vm.summary.market_regime)
        self._set_summary_value(self._risk_label, vm.summary.risk_level)
        self._set_summary_value(self._score_label, f"{vm.summary.overall_score:.1f}")
        self._set_summary_value(self._last_refresh_label_2, vm.summary.last_refresh)

    def _set_summary_value(self, block: list[QLabel], text: str) -> None:
        if len(block) >= 2:
            block[1].setText(text)

    def _render_recommendations(self, vm: IntelligenceViewModel) -> None:
        while self._rec_container_layout.count():
            item = self._rec_container_layout.takeAt(0)
            w = item.widget() if item is not None else None
            if w is not None:
                w.deleteLater()
        if vm.recommendations:
            for rec in vm.recommendations:
                card = RecommendationCard(self._rec_container)
                card.update_from(rec)
                self._rec_container_layout.addWidget(card)
        self._rec_container_layout.addStretch(1)

    def _render_insights(self, vm: IntelligenceViewModel) -> None:
        while self._insights_container_layout.count():
            item = self._insights_container_layout.takeAt(0)
            w = item.widget() if item is not None else None
            if w is not None:
                w.deleteLater()
        for insight in vm.insights:
            card = InsightCard(self._insights_container)
            card.update_from(insight)
            self._insights_container_layout.addWidget(card)

    def _render_status(self, vm: IntelligenceViewModel) -> None:
        self._connection_label.setText(
            f"\u25CF  {'Connected' if vm.connection_status == 'Connected' else 'Disconnected'}"
        )
        self._last_refresh_label.setText(f"Last: {vm.last_refresh}")
        self._rec_count_label.setText(str(vm.recommendation_count))
        self._controller_label.setText(vm.controller_status)
        self._bus_label.setText(vm.event_bus_status)
        self._worker_label.setText(vm.worker_status)

    @property
    def adapter(self) -> IntelligenceAdapter:
        return self._adapter

    def refresh(self) -> IntelligenceViewModel:
        self._on_refresh()
        if self._view_model is not None:
            return self._view_model
        return self._adapter.refresh()

    def current_view_model(self) -> IntelligenceViewModel | None:
        return self._view_model
