"""Placeholder chart widget for equity curve, monthly returns, drawdown, allocation."""

from __future__ import annotations

from PySide6.QtCharts import QChart, QChartView, QLineSeries, QPieSeries, QValueAxis
from PySide6.QtCore import Qt
from PySide6.QtWidgets import QFrame, QLabel, QVBoxLayout, QWidget


class ChartPlaceholderWidget(QWidget):
    def __init__(self, title: str, parent: QWidget | None = None) -> None:
        super().__init__(parent)
        self.setObjectName("ChartPlaceholder")
        layout = QVBoxLayout(self)
        layout.setContentsMargins(4, 4, 4, 4)
        self._label = QLabel(title)
        self._label.setProperty("class", "sectionTitleLabel")
        self._inner_frame = QFrame()
        self._chart_view = QChartView()
        self._chart_view.setObjectName("ChartView")

        layout.addWidget(self._label)
        layout.addWidget(self._inner_frame)

        inner = QVBoxLayout(self._inner_frame)
        inner.setContentsMargins(0, 0, 0, 0)
        inner.addWidget(self._chart_view)

        self.reset(title)

    def reset(self, title: str) -> None:
        chart = QChart()
        chart.setTitle(title)
        chart.setAnimationOptions(QChart.NoAnimation)
        chart.legend().setVisible(False)
        chart.setTheme(QChart.ChartThemeLight)

        if "Equity" in title:
            series = QLineSeries()
            series.append(0, 100)
            series.append(1, 120)
            series.append(2, 110)
            series.append(3, 115)
            series.setName("Value")
            x = QValueAxis()
            y = QValueAxis()
            x.setRange(0, 4)
            x.setLabelFormat("%d")
            x.setTitleText("Period")
            y.setRange(95, 125)
            y.setTitleText("Value")
            chart.addSeries(series)
            series.attachAxis(x)
            series.attachAxis(y)
            chart.addAxis(x, Qt.AlignmentFlag.AlignBottom)
            chart.addAxis(y, Qt.AlignmentFlag.AlignLeft)

        elif "Monthly" in title:
            series = QLineSeries()
            series.setName("Return %")
            for i in range(7):
                series.append(i, (-2.0 if i % 3 == 0 else (3.2 if i % 2 == 0 else 1.5)))
            chart.addSeries(series)

        elif "Drawdown" in title:
            series = QLineSeries()
            series.setName("Drawdown %")
            for i in range(8):
                series.append(i, -i * 1.5 + 3)
            chart.addSeries(series)

        elif "Allocation" in title:
            pie = QPieSeries()
            pie.append("Equity 55.2", 55.2)
            pie.append("Debt 22.1", 22.1)
            pie.append("Alternatives 11.8", 11.8)
            pie.append("Cash 10.9", 10.9)
            for slice_ in pie.slices():
                slice_.setLabelVisible(True)
            chart.addSeries(pie)
            chart.setAnimationOptions(QChart.SeriesAnimations)

        self._chart_view.setChart(chart)
