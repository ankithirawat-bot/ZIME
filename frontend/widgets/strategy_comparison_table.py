"""Strategy comparison table widget."""

from __future__ import annotations

from PySide6.QtWidgets import QHeaderView, QTableWidget, QTableWidgetItem, QVBoxLayout, QWidget


class StrategyComparisonTable(QWidget):
    def __init__(self, parent: QWidget | None = None) -> None:
        super().__init__(parent)
        self.setObjectName("ReportingStrategyComparison")
        layout = QVBoxLayout(self)
        layout.setContentsMargins(4, 4, 4, 4)

        self._table = QTableWidget()
        self._table.setColumnCount(5)
        self._table.setHorizontalHeaderLabels([
            "Strategy",
            "Return %",
            "Sharpe",
            "Drawdown %",
            "Win Rate % / Trades",
        ])
        self._table.horizontalHeader().setStretchLastSection(True)
        self._table.horizontalHeader().setSectionResizeMode(QHeaderView.Stretch)
        self._table.verticalHeader().setVisible(False)
        self._table.setEditTriggers(QTableWidget.NoEditTriggers)
        self._table.setSelectionBehavior(QTableWidget.SelectRows)

        layout.addWidget(self._table)

    def set_strategies(self, strategies) -> None:
        if not strategies:
            return
        self._table.setRowCount(len(strategies))
        for row, s in enumerate(strategies):
            self._table.setItem(row, 0, QTableWidgetItem(str(s.strategy_return)))
            self._table.setItem(row, 1, QTableWidgetItem(f"{s.strategy_return:.1f}"))
            self._table.setItem(row, 2, QTableWidgetItem(f"{s.sharpe:.2f}"))
            self._table.setItem(row, 3, QTableWidgetItem(f"{s.drawdown:.1f}"))
            label = f"{s.win_rate:.1f}% / {s.trades}"
            self._table.setItem(row, 4, QTableWidgetItem(label))
        self._table.resizeColumnsToContents()
