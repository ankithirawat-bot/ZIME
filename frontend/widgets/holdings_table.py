from __future__ import annotations

from PySide6.QtCore import Qt
from PySide6.QtGui import QColor
from PySide6.QtWidgets import (
    QHeaderView,
    QLabel,
    QTableWidget,
    QTableWidgetItem,
    QVBoxLayout,
    QWidget,
)

from frontend.viewmodels.portfolio_viewmodels import Holding

_COLUMNS: tuple[str, ...] = (
    "Symbol",
    "Qty",
    "Avg Price",
    "Current",
    "Market Value",
    "Today\u2019s P/L",
    "Overall P/L",
    "Weight",
)


def _money(value: float) -> str:
    return f"\u20B9{value:,.2f}"


def _pct(value: float) -> str:
    return f"{value:+.2f}%"


def _make_item(text: str, align: Qt.AlignmentFlag = Qt.AlignmentFlag.AlignCenter) -> QTableWidgetItem:
    item = QTableWidgetItem(text)
    item.setTextAlignment(align)
    return item


def _populate_row(table: QTableWidget, row_index: int, h: Holding) -> None:
    table.setItem(row_index, 0, _make_item(h.symbol))
    table.setItem(row_index, 1, _make_item(str(h.quantity)))
    table.setItem(row_index, 2, _make_item(_money(h.average_price), Qt.AlignmentFlag.AlignRight | Qt.AlignmentFlag.AlignVCenter))
    table.setItem(row_index, 3, _make_item(_money(h.current_price), Qt.AlignmentFlag.AlignRight | Qt.AlignmentFlag.AlignVCenter))
    table.setItem(row_index, 4, _make_item(_money(h.market_value), Qt.AlignmentFlag.AlignRight | Qt.AlignmentFlag.AlignVCenter))

    todays_item = _make_item(_money(h.todays_pnl), Qt.AlignmentFlag.AlignRight | Qt.AlignmentFlag.AlignVCenter)
    color = QColor("#34C77B") if h.todays_pnl >= 0 else QColor("#FF6B6B")
    todays_item.setForeground(color)
    table.setItem(row_index, 5, todays_item)

    overall_item = _make_item(
        f"{_money(h.overall_pnl)} ({_pct(h.overall_pnl_pct)})",
        Qt.AlignmentFlag.AlignRight | Qt.AlignmentFlag.AlignVCenter,
    )
    overall_color = QColor("#34C77B") if h.overall_pnl >= 0 else QColor("#FF6B6B")
    overall_item.setForeground(overall_color)
    table.setItem(row_index, 6, overall_item)

    table.setItem(row_index, 7, _make_item(_pct(h.weight), Qt.AlignmentFlag.AlignRight | Qt.AlignmentFlag.AlignVCenter))


class HoldingsTable(QWidget):
    def __init__(self, parent: QWidget | None = None) -> None:
        super().__init__(parent)
        self.setObjectName("holdingsTableWidget")

        root = QVBoxLayout(self)
        root.setContentsMargins(0, 0, 0, 0)
        root.setSpacing(4)

        header = QLabel("Holdings", self)
        header.setObjectName("holdingsTableHeader")
        root.addWidget(header)

        self._table = QTableWidget(self)
        self._table.setObjectName("holdingsTable")
        self._table.setColumnCount(len(_COLUMNS))
        self._table.setHorizontalHeaderLabels(list(_COLUMNS))
        self._table.horizontalHeader().setStretchLastSection(False)
        self._table.horizontalHeader().setSectionResizeMode(QHeaderView.ResizeMode.Stretch)
        self._table.setSelectionBehavior(QTableWidget.SelectionBehavior.SelectRows)
        self._table.setAlternatingRowColors(True)
        self._table.setEditTriggers(QTableWidget.EditTrigger.NoEditTriggers)
        self._table.verticalHeader().setVisible(False)
        self._table.setSortingEnabled(True)

        root.addWidget(self._table, 1)

    def update_holdings(self, holdings: tuple[Holding, ...]) -> None:
        self._table.setSortingEnabled(False)
        self._table.setRowCount(len(holdings))
        for idx, h in enumerate(holdings):
            _populate_row(self._table, idx, h)
        self._table.setSortingEnabled(True)

        if not holdings:
            self._table.setRowCount(0)

    def clear(self) -> None:
        self._table.setRowCount(0)

    def table_widget(self) -> QTableWidget:
        return self._table
