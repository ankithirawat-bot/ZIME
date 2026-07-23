"""Backtesting workspace view replacing the placeholder."""

from __future__ import annotations

from dataclasses import asdict

from PySide6.QtCore import Slot, Qt
from PySide6.QtWidgets import (
    QFrame,
    QHBoxLayout,
    QLabel,
    QPushButton,
    QScrollArea,
    QVBoxLayout,
    QWidget,
)

from frontend.viewmodels.backtesting_viewmodels import BacktestConfiguration, BacktestingViewModel
from frontend.widgets import (
    EquityCurveWidget,
    PerformanceSummaryCard,
    StrategySelector,
    TradesTable,
)


class BacktestingView(QWidget):
    def __init__(self, stack: QWidget, controller, parent: QWidget | None = None) -> None:
        super().__init__(parent)
        self.setObjectName("BacktestingWorkspace")
        self._stack = stack
        self._controller = controller

        self._adapter = controller.get_backtesting_adapter()

        self._layout = QVBoxLayout(self)
        self._layout.setContentsMargins(8, 8, 8, 8)
        self._layout.setSpacing(8)

        content = QFrame()
        content.setObjectName("BacktestingContentFrame")
        inner = QVBoxLayout(content)
        inner.setContentsMargins(0, 0, 0, 0)

        scroll = QScrollArea()
        scroll.setWidgetResizable(True)
        scroll.setFrameShape(QFrame.NoFrame)
        scroll.setVerticalScrollBarPolicy(Qt.ScrollBarPolicy.ScrollBarAsNeeded)
        scroll.setHorizontalScrollBarPolicy(Qt.ScrollBarPolicy.ScrollBarAsNeeded)
        scroll.setWidget(content)
        self._layout.addWidget(scroll)

        self._header = QLabel("Backtesting Workspace")
        self._header.setProperty("class", "workspaceTitleLabel")
        inner.addWidget(self._header)

        self._config_row = QFrame()
        self._config_row.setObjectName("ConfigRow")
        rl = QHBoxLayout(self._config_row)
        rl.setContentsMargins(0, 0, 0, 12)
        rl.setSpacing(12)

        self._strategy = StrategySelector()
        rl.addWidget(self._strategy)

        self._universe = self._make_input("Universe")
        self._timeframe = self._make_input("Timeframe")
        self._start_date = self._make_input("Start Date")
        self._end_date = self._make_input("End Date")
        self._capital = self._make_input("Initial Capital")
        self._commission = self._make_input("Commission")
        self._slippage = self._make_input("Slippage")

        rl.addWidget(self._universe)
        rl.addWidget(self._timeframe)
        rl.addWidget(self._start_date)
        rl.addWidget(self._end_date)
        rl.addWidget(self._capital)
        rl.addWidget(self._commission)
        rl.addWidget(self._slippage)

        self._run_button = QPushButton("Run Backtest")
        self._run_button.setAutoDefault(False)
        self._run_button.clicked.connect(self._on_run_backtest)
        rl.addWidget(self._run_button)
        rl.addStretch()
        inner.addWidget(self._config_row)

        self._summary_card = PerformanceSummaryCard()
        inner.addWidget(self._summary_card)

        self._equity_widget = EquityCurveWidget()
        inner.addWidget(self._equity_widget)

        self._trades_table = TradesTable()
        inner.addWidget(self._trades_table)

        inner.addSpacing(16)

        self._status_row = QFrame()
        self._status_row.setObjectName("StatusRow")
        sl = QHBoxLayout(self._status_row)
        sl.setContentsMargins(0, 0, 0, 0)
        sl.setSpacing(16)
        self._status_label = QLabel("Ready")
        self._last_run_label = QLabel("Never")
        self._backend_status = QLabel("Backend: ready")
        sl.addWidget(QLabel("Execution Status:"))
        sl.addWidget(self._status_label)
        sl.addWidget(QLabel("Last Run:"))
        sl.addWidget(self._last_run_label)
        sl.addWidget(self._backend_status)
        sl.addStretch()
        inner.addWidget(self._status_row)

        cfg = self._adapter.sample_configuration()
        self._apply_configuration(cfg)

    def _make_input(self, name: str) -> QLabel:
        w = QLabel(name + ": ")
        w.setProperty("class", "configLabel")
        return w

    def _apply_configuration(self, cfg: BacktestConfiguration) -> None:
        self._strategy.choose(cfg.strategy_name or "Composite")
        self._universe.setText(f"Universe: {cfg.universe}")
        self._timeframe.setText(f"Timeframe: {cfg.timeframe}")
        self._start_date.setText(f"Start: {cfg.start_date}")
        self._end_date.setText(f"End: {cfg.end_date}")
        self._capital.setText(f"Capital: {cfg.initial_capital:,.2f}")
        self._commission.setText(f"Commission: {cfg.commission}")
        self._slippage.setText(f"Slippage: {cfg.slippage}")
        self._controller.event_bus.publish(
            "backtesting.page.opened",
            payload={"configuration": asdict(cfg) if cfg else None},
        )

    def update_view(self, vm: BacktestingViewModel | None) -> None:
        if vm is None:
            return
        self._set_result_data(vm)

    def _set_result_data(self, vm: BacktestingViewModel) -> None:
        if vm.result:
            self._summary_card.set_metrics(vm.result.metrics)
            self._equity_widget.set_curve(vm.result.equity_curve)
            self._trades_table.set_trades(vm.result.trades)
        if vm.error_message:
            self._status_label.setText("Failed")
            self._backend_status.setText(f"Backend: error {vm.error_message}")
        else:
            self._status_label.setText("Ready")
            if vm.last_run_at_utc:
                self._last_run_label.setText(vm.last_run_at_utc[:19])
            self._backend_status.setText(
                f"Backend: {'success' if vm.result else 'n/a'}")

    @Slot()
    def _on_run_backtest(self) -> None:
        if not self._run_button.isEnabled():
            return
        self._run_button.setEnabled(False)
        self._status_label.setText("Running... please wait")
        self._controller.event_bus.publish(
            "backtesting.run.started",
            payload={"strategy": self._strategy.selected_strategy()},
        )

        from frontend.worker import WorkerThread

        cfg = BacktestConfiguration(
            strategy_name=self._strategy.selected_strategy(),
            universe="NIFTY50",
            timeframe="D1",
            start_date="2020-01-01",
            end_date="2024-12-31",
            initial_capital=1_000_000.0,
            commission=0.001,
            slippage=0.001,
        )

        def _task(_worker) -> Exception | None:
            try:
                result = self._adapter.load_backtest(cfg)
                if isinstance(result, Exception):
                    return result
                self._controller.event_bus.publish(
                    "backtesting.run.completed",
                    payload={"result": str(result)[:200]},
                )
                return None
            except Exception as exc:
                self._controller.event_bus.publish(
                    "backtesting.run.failed",
                    payload={"error": str(exc)},
                )
                return exc

        thread = WorkerThread(task=_task)
        thread.finished.connect(self._on_task_finished)
        thread.start()

    def _on_task_finished(self) -> None:
        self._run_button.setEnabled(True)
        # Adapter will push results to controller which emits adapterUpdated back to view via viewmodel
