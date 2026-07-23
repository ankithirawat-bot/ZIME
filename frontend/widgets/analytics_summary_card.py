"""Analytics summary card with key portfolio metrics."""

from __future__ import annotations

from PySide6.QtWidgets import QFrame, QGridLayout, QLabel, QVBoxLayout, QWidget


class AnalyticsSummaryCard(QWidget):
    def __init__(self, parent: QWidget | None = None) -> None:
        super().__init__(parent)
        self.setObjectName("ReportingAnalyticsSummary")
        layout = QVBoxLayout(self)
        layout.setContentsMargins(4, 4, 4, 4)
        self._frame = QFrame()
        layout.addWidget(self._frame)
        self._grid = QGridLayout(self._frame)
        self._grid.setContentsMargins(6, 6, 6, 6)
        self._grid.setSpacing(8)

        labels = [
            ("Portfolio Return", None),
            ("Benchmark Return", None),
            ("Alpha", None),
            ("Beta", None),
            ("Sharpe Ratio", None),
            ("Max Drawdown", None),
        ]
        for row, (txt, _) in enumerate(labels):
            nam = QLabel(txt)
            val = QLabel(" ")
            nam.setProperty("class", "metricNameLabel")
            val.setProperty("class", "metricValueLabel")
            self._grid.addWidget(nam, row, 0)
            self._grid.addWidget(val, row, 1)

    def set_analytics(self, summary) -> None:
        rows = [
            ("Portfolio Return", f"{summary.portfolio_return:+.2f}%"),
            ("Benchmark Return", f"{summary.benchmark_return:+.2f}%"),
            ("Alpha", f"{summary.alpha:+.2f}%"),
            ("Beta", f"{summary.beta:.3f}"),
            ("Sharpe Ratio", f"{summary.sharpe_ratio:.3f}"),
            ("Max Drawdown", f"{summary.max_drawdown:.2f}%"),
        ]
        for idx, (_, v) in enumerate(rows):
            lbl = self._grid.itemAtPosition(idx, 1).widget()
            if lbl and hasattr(lbl, "setText"):
                lbl.setText(v)
