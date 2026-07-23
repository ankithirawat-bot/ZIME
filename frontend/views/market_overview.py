from __future__ import annotations

from typing import Any

from PySide6.QtCore import Qt
from PySide6.QtWidgets import (
    QFrame,
    QGridLayout,
    QHBoxLayout,
    QLabel,
    QPushButton,
    QSizePolicy,
    QVBoxLayout,
    QWidget,
)

from frontend.adapters.market_overview_adapter import MarketOverviewAdapter
from frontend.adapters.market_overview_model import MarketOverview
from frontend.controller import ApplicationController
from frontend.widgets.cards import CardWidget

INDICES: tuple[str, ...] = ("NIFTY", "SENSEX", "BANK NIFTY", "VIX")


def _format_index_row(value: Any) -> str:
    del value  # placeholder — no live data
    return "— (Last)  ·  — (Change %)"


class MarketOverviewView(QWidget):
    """Sprint D4 placeholder view for the Market Overview page.

    All market figures are rendered as em-dashes until the live data layer
    is wired in a future sprint. The page surfaces controller + system
    health via the ``MarketOverviewAdapter``.
    """

    def __init__(
        self,
        controller: ApplicationController | None = None,
        parent: QWidget | None = None,
    ) -> None:
        super().__init__(parent)
        self._controller = controller
        self._adapter = MarketOverviewAdapter(controller=controller)
        self._view_model: MarketOverview | None = None
        self._last_update_value: str = "—"

        root = QVBoxLayout(self)
        root.setContentsMargins(24, 22, 24, 22)
        root.setSpacing(16)

        header_row = QWidget(self)
        header_layout = QHBoxLayout(header_row)
        header_layout.setContentsMargins(0, 0, 0, 0)
        header_layout.setSpacing(12)

        title_box = QWidget(header_row)
        title_layout = QVBoxLayout(title_box)
        title_layout.setContentsMargins(0, 0, 0, 0)
        title_layout.setSpacing(2)
        self._title_label = QLabel("Market Overview", title_box)
        self._title_label.setObjectName("marketOverviewTitle")
        self._subtitle_label = QLabel(
            "Live Indian market context — indices, movers, breadth, and connection state.",
            title_box,
        )
        self._subtitle_label.setObjectName("marketOverviewSubtitle")
        title_layout.addWidget(self._title_label)
        title_layout.addWidget(self._subtitle_label)
        header_layout.addWidget(title_box, 1)

        self._refresh_button = QPushButton("Refresh", header_row)
        self._refresh_button.setObjectName("marketOverviewRefreshButton")
        self._refresh_button.setCursor(Qt.CursorShape.PointingHandCursor)
        self._refresh_button.clicked.connect(self.refresh)
        header_layout.addWidget(
            self._refresh_button, 0, Qt.AlignmentFlag.AlignVCenter
        )

        root.addWidget(header_row)

        grid = QGridLayout()
        grid.setContentsMargins(0, 0, 0, 0)
        grid.setHorizontalSpacing(16)
        grid.setVerticalSpacing(16)
        grid.setColumnStretch(0, 1)
        grid.setColumnStretch(1, 1)

        self._indices_card = self._build_indices_card()
        self._movers_card = self._build_movers_card()
        self._active_card = self._build_active_card()
        self._breadth_card = self._build_breadth_card()

        grid.addWidget(self._indices_card, 0, 0)
        grid.addWidget(self._movers_card, 0, 1)
        grid.addWidget(self._active_card, 1, 0)
        grid.addWidget(self._breadth_card, 1, 1)

        grid_container = QWidget(self)
        grid_container.setLayout(grid)
        root.addWidget(grid_container, 1)

        footer = self._build_footer()
        root.addWidget(footer)

        self.refresh()

    def _build_indices_card(self) -> CardWidget:
        card = CardWidget("Indices", icon_name=None, parent=self)
        card.setProperty("cardTitle", "marketIndices")
        card.update_rows([(index, _format_index_row(index)) for index in INDICES])
        return card

    def _build_movers_card(self) -> CardWidget:
        card = CardWidget("Top Gainers / Top Losers", icon_name=None, parent=self)
        card.setProperty("cardTitle", "marketMovers")
        card.update_rows(
            [
                ("Top Gainers", "—"),
                ("Top Losers", "—"),
            ]
        )
        return card

    def _build_active_card(self) -> CardWidget:
        card = CardWidget("Most Active", icon_name=None, parent=self)
        card.setProperty("cardTitle", "marketActive")
        card.update_rows([("Volume Leaders", "—")])
        return card

    def _build_breadth_card(self) -> CardWidget:
        card = CardWidget("Market Breadth", icon_name=None, parent=self)
        card.setProperty("cardTitle", "marketBreadth")
        card.update_rows(
            [
                ("Advances", "—"),
                ("Declines", "—"),
                ("Unchanged", "—"),
                ("Advance / Decline Ratio", "—"),
            ]
        )
        return card

    def _build_footer(self) -> QFrame:
        frame = QFrame(self)
        frame.setObjectName("marketOverviewFooter")
        frame_layout = QHBoxLayout(frame)
        frame_layout.setContentsMargins(16, 12, 16, 12)
        frame_layout.setSpacing(16)

        last_update_block = self._make_footer_block("Last Update", self._last_update_value)
        self._last_update_value_label = last_update_block["value"]
        frame_layout.addWidget(last_update_block["widget"], 1)

        connection_block = self._make_footer_block("Connection Status", "○  Disconnected")
        self._connection_value_label = connection_block["value"]
        frame_layout.addWidget(connection_block["widget"], 1)

        dot_block = QWidget(frame)
        dot_layout = QHBoxLayout(dot_block)
        dot_layout.setContentsMargins(0, 0, 0, 0)
        dot_layout.setSpacing(8)
        self._status_dot = QLabel("●", dot_block)
        self._status_dot.setObjectName("marketOverviewStatusDot")
        size_policy = self._status_dot.sizePolicy()
        size_policy.setHorizontalPolicy(QSizePolicy.Policy.Fixed)
        self._status_dot.setSizePolicy(size_policy)
        dot_layout.addWidget(self._status_dot, 0, Qt.AlignmentFlag.AlignVCenter)
        self._status_label = QLabel("Idle", dot_block)
        self._status_label.setObjectName("marketOverviewStatusLabel")
        dot_layout.addWidget(self._status_label, 0, Qt.AlignmentFlag.AlignVCenter)
        frame_layout.addWidget(
            dot_block, 0, Qt.AlignmentFlag.AlignRight | Qt.AlignmentFlag.AlignVCenter
        )

        return frame

    @staticmethod
    def _make_footer_block(label_text: str, value_text: str) -> dict[str, QWidget]:
        block = QWidget()
        layout = QVBoxLayout(block)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(2)
        label = QLabel(label_text, block)
        label.setObjectName("marketOverviewFooterLabel")
        value = QLabel(value_text, block)
        value.setObjectName("marketOverviewFooterValue")
        layout.addWidget(label)
        layout.addWidget(value)
        return {"widget": block, "value": value}

    def refresh(self) -> MarketOverview:
        view_model = self._adapter.collect()
        self._view_model = view_model
        self._render(view_model)
        return view_model

    def current_view_model(self) -> MarketOverview | None:
        return self._view_model

    @property
    def adapter(self) -> MarketOverviewAdapter:
        return self._adapter

    def _render(self, view_model: MarketOverview) -> None:
        self._last_update_value_label.setText(view_model.last_update)
        if view_model.connection_connected:
            self._status_dot.setStyleSheet("color: #34C77B;")
            indicator = "●"
        else:
            self._status_dot.setStyleSheet("color: #8A91A1;")
            indicator = "○"
        self._connection_value_label.setText(f"{indicator}  {view_model.connection_detail}")
        self._status_label.setText(view_model.connection_detail)
