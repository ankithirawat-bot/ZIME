from __future__ import annotations

from PySide6.QtCore import Qt
from PySide6.QtWidgets import QFrame, QGridLayout, QLabel, QVBoxLayout, QWidget

from frontend.viewmodels.portfolio_viewmodels import AllocationSlice


class AllocationCard(QFrame):
    def __init__(self, title: str, parent: QWidget | None = None) -> None:
        super().__init__(parent)
        self.setObjectName("allocationCard")
        self.setFrameShape(QFrame.Shape.NoFrame)

        root = QVBoxLayout(self)
        root.setContentsMargins(16, 14, 16, 14)
        root.setSpacing(8)

        title_label = QLabel(title, self)
        title_label.setObjectName("allocationCardTitle")
        root.addWidget(title_label)

        self._grid = QGridLayout()
        self._grid.setContentsMargins(0, 0, 0, 0)
        self._grid.setHorizontalSpacing(12)
        self._grid.setVerticalSpacing(6)
        root.addLayout(self._grid)

        self._labels: list[QLabel] = []
        self._values: list[QLabel] = []
        self._pcts: list[QLabel] = []

    def update_from(self, slices: tuple[AllocationSlice, ...]) -> None:
        while self._grid.count():
            item = self._grid.takeAt(0)
            w = item.widget() if item is not None else None
            if w is not None:
                w.deleteLater()
        self._labels.clear()
        self._values.clear()
        self._pcts.clear()

        for idx, s in enumerate(slices):
            label = QLabel(s.label, self)
            label.setObjectName("allocationSliceLabel")
            self._grid.addWidget(label, idx, 0)

            val_text = f"\u20B9{s.value:,.2f}" if abs(s.value) < 1_00_000 else (
                f"\u20B9{s.value / 1_00_000:,.2f}L" if abs(s.value) < 1_00_00_000 else f"\u20B9{s.value / 1_00_00_000:,.2f}Cr"
            )
            val = QLabel(val_text, self)
            val.setObjectName("allocationSliceValue")
            val.setAlignment(Qt.AlignmentFlag.AlignRight | Qt.AlignmentFlag.AlignVCenter)
            self._grid.addWidget(val, idx, 1)

            pct = QLabel(f"{s.percentage:.1f}%", self)
            pct.setObjectName("allocationSlicePct")
            pct.setAlignment(Qt.AlignmentFlag.AlignRight | Qt.AlignmentFlag.AlignVCenter)
            self._grid.addWidget(pct, idx, 2)

            self._labels.append(label)
            self._values.append(val)
            self._pcts.append(pct)
