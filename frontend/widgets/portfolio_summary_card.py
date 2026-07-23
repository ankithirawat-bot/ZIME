from __future__ import annotations

from PySide6.QtGui import QColor
from PySide6.QtWidgets import QFrame, QGridLayout, QLabel, QVBoxLayout, QWidget

from frontend.viewmodels.portfolio_viewmodels import PortfolioSummary


def _money(value: float) -> str:
    if abs(value) >= 1_00_00_000:
        return f"\u20B9{value / 1_00_00_000:,.2f}Cr"
    if abs(value) >= 1_00_000:
        return f"\u20B9{value / 1_00_000:,.2f}L"
    return f"\u20B9{value:,.2f}"


def _format_change(value: float, pct: float) -> str:
    sign = "+" if value >= 0 else ""
    return f"{sign}{_money(value)} ({sign}{pct:.2f}%)"


class PortfolioSummaryCard(QFrame):
    def __init__(self, parent: QWidget | None = None) -> None:
        super().__init__(parent)
        self.setObjectName("portfolioSummaryCard")
        self.setFrameShape(QFrame.Shape.NoFrame)

        root = QVBoxLayout(self)
        root.setContentsMargins(16, 14, 16, 14)
        root.setSpacing(12)

        title = QLabel("Portfolio Summary", self)
        title.setObjectName("portfolioSummaryCardTitle")
        root.addWidget(title)

        grid = QGridLayout()
        grid.setContentsMargins(0, 0, 0, 0)
        grid.setHorizontalSpacing(24)
        grid.setVerticalSpacing(8)

        self._total_value_label = QLabel("\u20B90.00", self)
        self._total_value_label.setObjectName("portfolioSummaryValue")
        grid.addWidget(QLabel("Total Value", self), 0, 0)
        grid.addWidget(self._total_value_label, 0, 1)

        self._todays_pnl_label = QLabel("+0.00 (0.00%)", self)
        self._todays_pnl_label.setObjectName("portfolioSummaryChange")
        grid.addWidget(QLabel("Today\u2019s P/L", self), 1, 0)
        grid.addWidget(self._todays_pnl_label, 1, 1)

        self._total_pnl_label = QLabel("+0.00 (0.00%)", self)
        self._total_pnl_label.setObjectName("portfolioSummaryChange")
        grid.addWidget(QLabel("Total P/L", self), 2, 0)
        grid.addWidget(self._total_pnl_label, 2, 1)

        self._cash_label = QLabel("\u20B90.00", self)
        self._cash_label.setObjectName("portfolioSummaryValue")
        grid.addWidget(QLabel("Cash Balance", self), 3, 0)
        grid.addWidget(self._cash_label, 3, 1)

        root.addLayout(grid)

    def update_from(self, summary: PortfolioSummary) -> None:
        self._total_value_label.setText(_money(summary.total_value))

        todays_text = _format_change(summary.todays_pnl, summary.todays_pnl_pct)
        self._todays_pnl_label.setText(todays_text)
        todays_color = QColor("#34C77B") if summary.todays_pnl >= 0 else QColor("#FF6B6B")
        self._todays_pnl_label.setStyleSheet(f"color: {todays_color.name()};")

        total_text = _format_change(summary.total_pnl, summary.total_pnl_pct)
        self._total_pnl_label.setText(total_text)
        total_color = QColor("#34C77B") if summary.total_pnl >= 0 else QColor("#FF6B6B")
        self._total_pnl_label.setStyleSheet(f"color: {total_color.name()};")

        self._cash_label.setText(_money(summary.cash_balance))
