from __future__ import annotations

from PySide6.QtCore import Qt
from PySide6.QtGui import QColor
from PySide6.QtWidgets import QFrame, QHBoxLayout, QLabel, QVBoxLayout, QWidget

from frontend.viewmodels.intelligence_viewmodels import Recommendation


def _rec_color(recommendation: str) -> QColor:
    mapping: dict[str, str] = {
        "BUY": "#34C77B",
        "STRONG_BUY": "#00E676",
        "HOLD": "#FFD54F",
        "SELL": "#FF6B6B",
        "STRONG_SELL": "#FF1744",
    }
    return QColor(mapping.get(recommendation, "#8A91A1"))


class RecommendationCard(QFrame):
    def __init__(self, parent: QWidget | None = None) -> None:
        super().__init__(parent)
        self.setObjectName("recommendationCard")
        self.setFrameShape(QFrame.Shape.NoFrame)

        root = QHBoxLayout(self)
        root.setContentsMargins(16, 12, 16, 12)
        root.setSpacing(16)

        left = QVBoxLayout()
        left.setContentsMargins(0, 0, 0, 0)
        left.setSpacing(2)
        self._symbol_label = QLabel("—", self)
        self._symbol_label.setObjectName("recSymbol")
        left.addWidget(self._symbol_label)
        self._reason_label = QLabel("", self)
        self._reason_label.setObjectName("recReason")
        left.addWidget(self._reason_label)
        root.addLayout(left, 1)

        right = QVBoxLayout()
        right.setContentsMargins(0, 0, 0, 0)
        right.setSpacing(2)
        right.setAlignment(Qt.AlignmentFlag.AlignRight)

        self._action_label = QLabel("—", self)
        self._action_label.setObjectName("recAction")
        self._action_label.setAlignment(Qt.AlignmentFlag.AlignRight)
        right.addWidget(self._action_label)

        score_row = QHBoxLayout()
        score_row.setContentsMargins(0, 0, 0, 0)
        score_row.setSpacing(8)
        score_row.setAlignment(Qt.AlignmentFlag.AlignRight)

        self._confidence_label = QLabel("", self)
        self._confidence_label.setObjectName("recConfidence")
        score_row.addWidget(self._confidence_label)

        self._score_label = QLabel("", self)
        self._score_label.setObjectName("recScore")
        score_row.addWidget(self._score_label)

        right.addLayout(score_row)
        root.addLayout(right)

    def update_from(self, rec: Recommendation) -> None:
        self._symbol_label.setText(rec.symbol)
        self._reason_label.setText(rec.reason)
        self._action_label.setText(rec.recommendation)
        color = _rec_color(rec.recommendation)
        self._action_label.setStyleSheet(f"color: {color.name()}; font-weight: bold;")
        trend_icon = "\u2191" if rec.trend == "rising" else ("\u2193" if rec.trend == "falling" else "\u2192")
        self._confidence_label.setText(f"{trend_icon} {rec.confidence:.0%}")
        self._score_label.setText(f"Score: {rec.score:.1f}")
