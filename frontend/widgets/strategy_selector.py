"""Strategy selection dropdown widget."""

from __future__ import annotations

from PySide6.QtWidgets import (
    QComboBox,
    QHBoxLayout,
    QLabel,
    QWidget,
)


class StrategySelector(QWidget):
    def __init__(self, parent: QWidget | None = None) -> None:
        super().__init__(parent)
        self.setObjectName("BacktestingStrategySelector")

        layout = QHBoxLayout(self)
        layout.setContentsMargins(4, 4, 4, 4)
        layout.setSpacing(8)

        layout.addWidget(QLabel("Strategy:"))
        self._combo = QComboBox()
        self._combo.addItems([
            "Momentum",
            "MeanReversion",
            "TrendFollower",
            "RS (Relative Strength)",
            "Volatility",
            "Composite",
        ])
        self._combo.setMinimumWidth(180)
        layout.addWidget(self._combo)
        layout.addStretch()

    def selected_strategy(self) -> str:
        return self._combo.currentText()

    def choose(self, name: str) -> None:
        idx = self._combo.findText(name, Qt.MatchFixedString)
        if idx >= 0:
            self._combo.setCurrentIndex(idx)



from PySide6.QtCore import Qt  # noqa: E402
