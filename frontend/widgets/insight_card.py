from __future__ import annotations

from PySide6.QtGui import QColor
from PySide6.QtWidgets import QFrame, QHBoxLayout, QLabel, QVBoxLayout, QWidget

from frontend.viewmodels.intelligence_viewmodels import Insight


def _severity_color(severity: str) -> QColor:
    mapping: dict[str, str] = {
        "positive": "#34C77B",
        "info": "#64B5F6",
        "warning": "#FFD54F",
        "critical": "#FF6B6B",
    }
    return QColor(mapping.get(severity, "#8A91A1"))


def _severity_icon(severity: str) -> str:
    mapping: dict[str, str] = {
        "positive": "\u2713",
        "info": "\u2139",
        "warning": "\u26A0",
        "critical": "\u2716",
    }
    return mapping.get(severity, "\u2022")


class InsightCard(QFrame):
    def __init__(self, parent: QWidget | None = None) -> None:
        super().__init__(parent)
        self.setObjectName("insightCard")
        self.setFrameShape(QFrame.Shape.NoFrame)

        root = QVBoxLayout(self)
        root.setContentsMargins(16, 12, 16, 12)
        root.setSpacing(4)

        header = QHBoxLayout()
        header.setContentsMargins(0, 0, 0, 0)
        header.setSpacing(8)

        self._icon_label = QLabel("", self)
        self._icon_label.setObjectName("insightIcon")
        header.addWidget(self._icon_label)

        self._title_label = QLabel("", self)
        self._title_label.setObjectName("insightTitle")
        header.addWidget(self._title_label, 1)

        self._category_label = QLabel("", self)
        self._category_label.setObjectName("insightCategory")
        header.addWidget(self._category_label)

        root.addLayout(header)

        self._desc_label = QLabel("", self)
        self._desc_label.setObjectName("insightDescription")
        self._desc_label.setWordWrap(True)
        root.addWidget(self._desc_label)

    def update_from(self, insight: Insight) -> None:
        color = _severity_color(insight.severity)
        self._icon_label.setText(_severity_icon(insight.severity))
        self._icon_label.setStyleSheet(f"color: {color.name()}; font-size: 16px;")
        self._title_label.setText(insight.title)
        self._category_label.setText(insight.category)
        self._desc_label.setText(insight.description)
