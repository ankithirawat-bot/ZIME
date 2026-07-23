"""Equity curve visualization widget."""

from __future__ import annotations

from PySide6.QtCharts import QChart, QChartView, QLineSeries, QValueAxis
from PySide6.QtCore import Qt
from PySide6.QtGui import QColor, QPainter
from PySide6.QtWidgets import QFrame, QLabel, QVBoxLayout, QWidget


class EquityCurveWidget(QWidget):
    def __init__(self, parent: QWidget | None = None) -> None:
        super().__init__(parent)
        self.setObjectName("BacktestingEquityCurve")

        self._layout = QVBoxLayout(self)
        self._layout.setContentsMargins(4, 4, 4, 4)
        self._layout.setSpacing(6)

        self._label = QLabel("Equity Curve (sample)")
        self._label.setProperty("class", "sectionTitleLabel")
        self._layout.addWidget(self._label)

        self._frame = QFrame()
        self._frame.setObjectName("EquityCurveFrame")
        inner = QVBoxLayout(self._frame)
        inner.setContentsMargins(0, 0, 0, 0)
        self._chart_view = QChartView()
        self._chart_view.setRenderHint(QPainter.Antialiasing)
        inner.addWidget(self._chart_view)

        self._layout.addWidget(self._frame)

        self._reset_chart()

    def _reset_chart(self) -> None:
        series = QLineSeries()
        series.setColor(QColor("#26a69a"))
        series.setName("Equity %")
        pen = series.pen()
        pen.setWidth(2)
        series.setPen(pen)

        x_axis = QValueAxis()
        y_axis = QValueAxis()
        x_axis.setLabelFormat("%d-%m")
        x_axis.setTitleText("Date")
        y_axis.setLabelFormat("%d")
        y_axis.setTitleText("Cumulative Value")

        chart = QChart()
        chart.addSeries(series)
        chart.addAxis(x_axis, Qt.AlignmentFlag.AlignBottom)
        chart.addAxis(y_axis, Qt.AlignmentFlag.AlignLeft)
        series.attachAxis(x_axis)
        series.attachAxis(y_axis)
        chart.setTitle("")
        chart.setAnimationOptions(QChart.NoAnimation)
        chart.legend().setVisible(False)

        self._chart_view.setChart(chart)
        self._series = series
        self._x_axis = x_axis
        self._y_axis = y_axis

    def set_curve(self, points) -> None:
        series = self._series
        series.clear()
        if not points:
            return
        max_y = float("-inf")
        for p in points:
            series.append(
                float(p.timestamp[:10].replace("-", "")),
                p.cumulative_value,
            )
            max_y = max(max_y, p.cumulative_value)
        self._chart_view.chart().axes(Qt.Orientation.Horizontal)[0].setRange(
            points[0].timestamp[:10].replace("-", ""), points[-1].timestamp[:10].replace("-", ""),
        )
        self._chart_view.chart().axes(Qt.Orientation.Vertical)[0].setRange(
            0, max_y * 1.05
        )
