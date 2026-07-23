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

from frontend.viewmodels.intelligence_viewmodels import Signal

_COLUMNS: tuple[str, ...] = (
    "Symbol",
    "Signal",
    "Trend",
    "Strength",
    "Confidence",
    "Score",
)


def _make_item(
    text: str,
    align: Qt.AlignmentFlag = Qt.AlignmentFlag.AlignCenter,
) -> QTableWidgetItem:
    item = QTableWidgetItem(text)
    item.setTextAlignment(align)
    return item


def _populate_row(table: QTableWidget, row_index: int, s: Signal) -> None:
    table.setItem(row_index, 0, _make_item(s.symbol))
    table.setItem(row_index, 1, _make_item(s.signal_type))
    trend_icon = "\u2191" if s.trend == "rising" else ("\u2193" if s.trend == "falling" else "\u2192")
    trend_item = _make_item(trend_icon)
    trend_color = QColor("#34C77B") if s.trend == "rising" else (
        QColor("#FF6B6B") if s.trend == "falling" else QColor("#8A91A1")
    )
    trend_item.setForeground(trend_color)
    table.setItem(row_index, 2, trend_item)
    table.setItem(row_index, 3, _make_item(f"{s.strength:.1f}", Qt.AlignmentFlag.AlignRight | Qt.AlignmentFlag.AlignVCenter))
    table.setItem(row_index, 4, _make_item(f"{s.confidence:.0%}", Qt.AlignmentFlag.AlignRight | Qt.AlignmentFlag.AlignVCenter))
    table.setItem(row_index, 5, _make_item(f"{s.score:.1f}", Qt.AlignmentFlag.AlignRight | Qt.AlignmentFlag.AlignVCenter))


class SignalTable(QWidget):
    def __init__(self, parent: QWidget | None = None) -> None:
        super().__init__(parent)
        self.setObjectName("signalTableWidget")

        root = QVBoxLayout(self)
        root.setContentsMargins(0, 0, 0, 0)
        root.setSpacing(4)

        header = QLabel("Signals", self)
        header.setObjectName("signalTableHeader")
        root.addWidget(header)

        self._table = QTableWidget(self)
        self._table.setObjectName("signalTable")
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

    def update_signals(self, signals: tuple[Signal, ...]) -> None:
        self._table.setSortingEnabled(False)
        self._table.setRowCount(len(signals))
        for idx, s in enumerate(signals):
            _populate_row(self._table, idx, s)
        self._table.setSortingEnabled(True)

        if not signals:
            self._table.setRowCount(0)

    def clear(self) -> None:
        self._table.setRowCount(0)
