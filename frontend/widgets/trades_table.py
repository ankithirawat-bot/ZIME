"""Trades history flat table widget."""

from __future__ import annotations

from PySide6.QtCore import QAbstractTableModel, QModelIndex, Qt
from PySide6.QtGui import QColor
from PySide6.QtWidgets import QLabel, QTableView, QVBoxLayout, QWidget


class TradesTableModel(QAbstractTableModel):
    def __init__(self, trades, parent=None):
        super().__init__(parent)
        self._trades = trades or []

    def data(self, index: QModelIndex, role=Qt.DisplayRole):
        if not index.isValid():
            return None
        row, col = index.row(), index.column()
        if role == Qt.DisplayRole:
            t = self._trades[row]
            cols = [
                t.trade_id,
                t.symbol,
                t.entry_date,
                t.exit_date,
                t.direction,
                t.entry_price,
                t.exit_price,
                t.pnl,
                f"{t.return_pct:.2f} %",
            ]
            return str(cols[col])
        if role == Qt.ForegroundRole and col in (6, 7):
            val = self._trades[row].pnl
            if val > 0:
                return QColor("#2E7D32")  # green
            if val < 0:
                return QColor("#C62828")  # red
        return None

    def header_data(self, section, orientation, role=Qt.DisplayRole):
        if role == Qt.DisplayRole and orientation == Qt.Horizontal:
            headers = [
                "ID",
                "Symbol",
                "Entry Date",
                "Exit Date",
                "Direction",
                "Entry",
                "Exit",
                "PnL",
                "Return",
            ]
            return headers[section]
        return None

    def row_count(self, _=None):
        return len(self._trades)

    def column_count(self, _=None):
        return 9




class TradesTable(QWidget):
    def __init__(self, parent: QWidget | None = None) -> None:
        super().__init__(parent)
        self.setObjectName("BacktestingTradesTable")
        self._layout = QVBoxLayout(self)
        self._layout.setContentsMargins(4, 4, 4, 4)
        self._label = QLabel("Trade History")
        self._label.setProperty("class", "sectionTitleLabel")
        self._label.setProperty("class", "sectionTitleLabel")
        self._layout.addWidget(self._label)
        self._view = QTableView()
        self._view.setEditTriggers(QTableView.NoEditTriggers)
        self._view.setSelectionBehavior(QTableView.SelectRows)
        self._view.horizontalHeader().setStretchLastSection(True)
        self._view.verticalHeader().setVisible(False)
        self._view.setAlternatingRowColors(True)
        self._layout.addWidget(self._view)
        self._model = TradesTableModel([])
        self._view.setModel(self._model)

    def set_trades(self, trades) -> None:
        self._model = TradesTableModel(trades)
        self._view.setModel(self._model)
        self._view.resizeColumnsToContents()
