from __future__ import annotations

from PySide6.QtCore import Qt
from PySide6.QtGui import QColor
from PySide6.QtWidgets import QFrame, QGridLayout, QLabel, QVBoxLayout, QWidget

from frontend.viewmodels.intelligence_viewmodels import MarketHealth


def _status_color(score: float) -> QColor:
    if score >= 60:
        return QColor("#34C77B")
    if score >= 40:
        return QColor("#FFD54F")
    return QColor("#FF6B6B")


class MarketHealthCard(QFrame):
    def __init__(self, parent: QWidget | None = None) -> None:
        super().__init__(parent)
        self.setObjectName("marketHealthCard")
        self.setFrameShape(QFrame.Shape.NoFrame)

        root = QVBoxLayout(self)
        root.setContentsMargins(16, 14, 16, 14)
        root.setSpacing(8)

        title = QLabel("Market Health", self)
        title.setObjectName("marketHealthTitle")
        root.addWidget(title)

        self._grid = QGridLayout()
        self._grid.setContentsMargins(0, 0, 0, 0)
        self._grid.setHorizontalSpacing(12)
        self._grid.setVerticalSpacing(4)
        root.addLayout(self._grid)

        self._labels: dict[str, list[QLabel]] = {}

    def update_from(self, mh: MarketHealth) -> None:
        while self._grid.count():
            item = self._grid.takeAt(0)
            w = item.widget() if item is not None else None
            if w is not None:
                w.deleteLater()
        self._labels.clear()

        rows: list[tuple[str, str, float]] = [
            ("Trend", mh.trend, mh.trend_score),
            ("Breadth", mh.breadth, mh.breadth_score),
            ("Momentum", mh.momentum, mh.momentum_score),
            ("Volatility", mh.volatility, mh.volatility_score),
            ("Liquidity", mh.liquidity, mh.liquidity_score),
        ]

        for idx, (label_text, value_text, score) in enumerate(rows):
            lbl = QLabel(label_text, self)
            lbl.setObjectName("healthMetricLabel")
            self._grid.addWidget(lbl, idx, 0)

            val = QLabel(value_text.capitalize(), self)
            val.setObjectName("healthMetricValue")
            val.setAlignment(Qt.AlignmentFlag.AlignRight | Qt.AlignmentFlag.AlignVCenter)
            val.setStyleSheet(f"color: {_status_color(score).name()};")
            self._grid.addWidget(val, idx, 1)

            sc = QLabel(f"{score:.0f}", self)
            sc.setObjectName("healthMetricScore")
            sc.setAlignment(Qt.AlignmentFlag.AlignRight | Qt.AlignmentFlag.AlignVCenter)
            sc.setStyleSheet(f"color: {_status_color(score).name()};")
            self._grid.addWidget(sc, idx, 2)

            self._labels[label_text] = [lbl, val, sc]
