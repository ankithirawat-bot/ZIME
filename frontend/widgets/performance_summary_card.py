"""Performance summary metric cards."""

from __future__ import annotations

from PySide6.QtWidgets import QFrame, QGridLayout, QLabel, QVBoxLayout, QWidget


class PerformanceSummaryCard(QWidget):
    def __init__(self, parent: QWidget | None = None) -> None:
        super().__init__(parent)
        self.setObjectName("BacktestingPerformanceCard")
        self._layout = QVBoxLayout(self)
        self._layout.setContentsMargins(0, 0, 0, 0)
        self._metrics_frame = QFrame()
        self._metrics_frame.setObjectName("PerfMetricsFrame")
        self._metrics_layout = QGridLayout(self._metrics_frame)
        self._metrics_layout.setContentsMargins(6, 6, 6, 6)
        self._metrics_layout.setSpacing(8)
        self._layout.addWidget(self._metrics_frame)

        labels = [
            ("Net Return", None),
            ("CAGR", None),
            ("Sharpe Ratio", None),
            ("Max Drawdown", None),
            ("Win Rate", None),
            ("Profit Factor", None),
            ("Total Trades", None),
            ("Expectancy", None),
        ]
        for row, (lbl, _) in enumerate(labels):
            name = QLabel(lbl)
            name.setProperty("class", "metricNameLabel")
            val = QLabel(" ")
            val.setProperty("class", "metricValueLabel")
            self._metrics_layout.addWidget(name, row, 0)
            self._metrics_layout.addWidget(val, row, 1)

    def set_metrics(self, metrics) -> None:
        rows = [
            ("Net Return", f"{metrics.net_return:+.2f}%"),
            ("CAGR", f"{metrics.cagr:.2f}%"),
            ("Sharpe Ratio", f"{metrics.sharpe_ratio:.3f}"),
            ("Max Drawdown", f"{metrics.max_drawdown:.2f}%"),
            ("Win Rate", f"{metrics.win_rate:.1f}%"),
            ("Profit Factor", f"{metrics.profit_factor:.2f}"),
            ("Total Trades", str(metrics.total_trades)),
            ("Expectancy", f"{metrics.expectancy:.2f}"),
        ]
        for row, (t, v) in enumerate(rows):
            label = self._metrics_frame.layout().itemAtPosition(row, 1).widget()
            if label and hasattr(label, "setText"):
                label.setText(v)
