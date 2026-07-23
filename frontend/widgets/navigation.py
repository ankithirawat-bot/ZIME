from __future__ import annotations

from collections.abc import Callable

from PySide6.QtCore import Qt, Signal
from PySide6.QtWidgets import (
    QListWidget,
    QListWidgetItem,
    QVBoxLayout,
    QWidget,
)

NAV_ITEMS: tuple[str, ...] = (
    "Dashboard",
    "Market Overview",
    "Screener",
    "Portfolio",
    "Backtesting",
    "Intelligence",
    "Reports",
    "Settings",
)


class NavigationPanel(QWidget):
    page_selected = Signal(int)

    def __init__(
        self,
        items: tuple[str, ...] = NAV_ITEMS,
        parent: QWidget | None = None,
    ) -> None:
        super().__init__(parent)
        self._items = items
        self.setObjectName("navigationPanel")
        self.setMinimumWidth(200)
        self.setMaximumWidth(260)
        self._list = QListWidget(self)
        self._list.setObjectName("navigationList")
        self._list.setFrameShape(QListWidget.Shape.NoFrame)
        self._list.setFocusPolicy(Qt.FocusPolicy.NoFocus)
        self._list.setSelectionMode(QListWidget.SelectionMode.SingleSelection)
        self._list.setUniformItemSizes(True)
        self._populate(self._list, self._items)
        self._list.setCurrentRow(0)
        self._list.currentRowChanged.connect(self.page_selected.emit)

        layout = QVBoxLayout(self)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(0)
        layout.addWidget(self._list)

    @staticmethod
    def _populate(list_widget: QListWidget, items: tuple[str, ...]) -> None:
        for label in items:
            item = QListWidgetItem(label)
            item.setTextAlignment(Qt.AlignmentFlag.AlignLeft | Qt.AlignmentFlag.AlignVCenter)
            list_widget.addItem(item)

    def current_index(self) -> int:
        return self._list.currentRow()

    def set_index(self, index: int, *, callback: Callable[[int], None] | None = None) -> None:
        if callback is not None:
            self.page_selected.disconnect(callback)
        if 0 <= index < self._list.count():
            self._list.setCurrentRow(index)
