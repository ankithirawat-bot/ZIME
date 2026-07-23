"""Grid layout of performance metrics."""

from __future__ import annotations

from PySide6.QtWidgets import QGridLayout, QLabel, QWidget


class PerformanceMetricsGrid(QWidget):
    def __init__(self, parent: QWidget | None = None) -> None:
        super().__init__(parent)
        self.setObjectName("ReportingPerformanceMetrics")
        self._layout = QGridLayout(self)
        self._layout.setContentsMargins(4, 4, 4, 4)
        self._layout.setSpacing(8)
        self._labels: dict[str, QLabel] = {}

    def set_metrics(self, metrics) -> None:
        rows = [
            ("CAGR", f"{metrics.cagr:.2f}%"),
            ("Annual Return", f"{metrics.annual_return:.2f}%"),
            ("Volatility", f"{metrics.volatility:.2f}%"),
            ("Sortino Ratio", f"{metrics.sortino_ratio:.3f}"),
            ("Calmar Ratio", f"{metrics.calmar_ratio:.2f}"),
            ("Information Ratio", f"{metrics.information_ratio:.2f}"),
            ("Profit Factor", f"{metrics.profit_factor:.2f}"),
            ("Win Rate", f"{metrics.win_rate:.1f}%"),
        ]
        for name, text in rows:
            if name not in self._labels:
                row = self._layout.count()
                n = QLabel(name)
                v = QLabel(text)
                n.setProperty("class", "metricNameLabel")
                v.setProperty("class", "valueLabel metricValueLabel")
                self._layout.addWidget(n, row, 0)
                self._layout.addWidget(v, row, 1)
                self._labels[name] = v
            else:
                self._labels[name].setText(text)
