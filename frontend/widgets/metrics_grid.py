"""Grid layout of read-only metric labels."""

from __future__ import annotations

from PySide6.QtWidgets import QGridLayout, QLabel, QWidget


class MetricsGrid(QWidget):
    def __init__(self, parent: QWidget | None = None) -> None:
        super().__init__(parent)
        self.setObjectName("BacktestingMetricsGrid")
        self._layout = QGridLayout(self)
        self._layout.setContentsMargins(4, 4, 4, 4)
        self._labels: dict[str, QLabel] = {}

    def set_metrics(self, metrics) -> None:
        labels = {
            "Net Return": f"{metrics.net_return:+.2f}%",
            "CAGR": f"{metrics.cagr:.2f}%",
            "Sharpe Ratio": f"{metrics.sharpe_ratio:.3f}",
            "Max Drawdown": f"{metrics.max_drawdown:.2f}%",
            "Win Rate": f"{metrics.win_rate:.1f}%",
            "Profit Factor": f"{metrics.profit_factor:.2f}",
            "Total Trades": str(metrics.total_trades),
            "Expectancy": f"{metrics.expectancy:.2f}",
        }
        for name, text in labels.items():
            if name not in self._labels:
                row = self._layout.count()
                namelabel = QLabel(name)
                valuelabel = QLabel(text)
                namelabel.setProperty("class", "configLabel")
                valuelabel.setProperty("class", "valueLabel")
                self._layout.addWidget(namelabel, row, 0)
                self._layout.addWidget(valuelabel, row, 1)
                self._labels[name] = valuelabel
            else:
                self._labels[name].setText(text)
