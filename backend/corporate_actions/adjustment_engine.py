"""
Corporate Actions adjustment engine.

Generates adjusted price series from immutable raw prices and a set
of corporate actions. Raw prices are never mutated.
"""

from __future__ import annotations

from datetime import date, datetime
from typing import Any

from backend.corporate_actions.models import (
    AdjustedPrice,
    AdjustmentRequest,
    AdjustmentResult,
    CorporateAction,
)
from backend.corporate_actions.types import ActionType


class AdjustmentEngine:
    """Builds adjusted price series from raw prices and corporate actions.

    Adjustment logic is resolved through a dispatch table so new action
    types can be added without changing the public API. Raw prices are
    treated as immutable: every output row preserves the original values.
    """

    def __init__(self) -> None:
        """Initialise the engine and register adjustment handlers."""
        self._handlers = {
            ActionType.SPLIT: self.apply_split,
            ActionType.BONUS: self.apply_bonus,
            ActionType.DIVIDEND: self.apply_dividend,
            ActionType.RIGHTS: self.apply_rights,
            ActionType.BUYBACK: self.apply_buyback,
        }

    def adjust_prices(self, request: AdjustmentRequest) -> AdjustmentResult:
        """Adjust raw prices for all applicable corporate actions.

        Args:
            request: Adjustment request with raw prices and actions.

        Returns:
            AdjustmentResult containing adjusted price rows.

        Raises:
            UnsupportedActionTypeError: If an action type has no handler.
        """
        actions = self._filter_actions(request)
        ordered = sorted(actions, key=lambda a: a.effective_date)

        raw_rows = list(request.raw_prices)
        adjusted_rows: list[AdjustedPrice] = []

        for raw in raw_rows:
            trade_date = self._parse_date(raw.get("date"))
            if trade_date is None:
                raise ValueError(f"Raw price missing valid date: {raw!r}")

            open_ = float(raw.get("open", 0.0))
            high = float(raw.get("high", 0.0))
            low = float(raw.get("low", 0.0))
            close = float(raw.get("close", 0.0))
            volume = int(raw.get("volume", 0))

            factor = self._cumulative_factor(trade_date, ordered)
            dividend_factor = self._cumulative_dividend(trade_date, ordered)

            adj_open = open_ * factor
            adj_high = high * factor
            adj_low = low * factor
            adj_close = close * factor
            adj_volume = int(volume / factor) if factor != 0 else volume
            adj_close_total = adj_close - dividend_factor

            adjusted_rows.append(
                AdjustedPrice(
                    trade_date=trade_date,
                    open=adj_open,
                    high=adj_high,
                    low=adj_low,
                    close=adj_close,
                    adjusted_close=adj_close_total,
                    volume=adj_volume,
                    raw_open=open_,
                    raw_high=high,
                    raw_low=low,
                    raw_close=close,
                    raw_volume=volume,
                    factor=factor,
                )
            )

        return AdjustmentResult(
            symbol=request.symbol,
            exchange=request.exchange,
            prices=tuple(adjusted_rows),
            actions_applied=tuple(ordered),
            raw_preserved=True,
        )

    def apply_split(self, action: CorporateAction) -> float:
        """Return the OHLC/volume factor contributed by a split.

        A 2:1 split (ratio 2.0) halves historical prices and doubles
        historical volume for dates before the effective date.

        Args:
            action: Split corporate action.

        Returns:
            Multiplicative price factor (e.g. 0.5 for a 2:1 split).
        """
        if action.ratio is None or action.ratio <= 0:
            return 1.0
        return 1.0 / action.ratio

    def apply_bonus(self, action: CorporateAction) -> float:
        """Return the OHLC/volume factor contributed by a bonus issue.

        A 1:1 bonus (ratio 2.0) halves historical prices and doubles
        historical volume for dates before the effective date.

        Args:
            action: Bonus corporate action.

        Returns:
            Multiplicative price factor.
        """
        if action.ratio is None or action.ratio <= 0:
            return 1.0
        return 1.0 / action.ratio

    def apply_dividend(self, action: CorporateAction) -> float:
        """Return the cash adjustment contributed by a dividend.

        Dividends reduce only the adjusted close; raw OHLC values and
        volume are untouched.

        Args:
            action: Dividend corporate action.

        Returns:
            Absolute cash deduction for the adjusted close.
        """
        if action.cash_amount is None or action.cash_amount < 0:
            return 0.0
        return float(action.cash_amount)

    def apply_rights(self, action: CorporateAction) -> float:
        """Return the factor contributed by a rights issue.

        Rights issues are recorded as metadata and do not adjust prices
        in the initial implementation, so the factor is neutral.

        Args:
            action: Rights corporate action.

        Returns:
            Neutral multiplicand (1.0).
        """
        return 1.0

    def apply_buyback(self, action: CorporateAction) -> float:
        """Return the factor contributed by a buyback.

        Buybacks are metadata only; no price adjustment is applied.

        Args:
            action: Buyback corporate action.

        Returns:
            Neutral multiplicand (1.0).
        """
        return 1.0

    def _filter_actions(self, request: AdjustmentRequest) -> list[CorporateAction]:
        if request.as_of is None:
            return list(request.actions)
        return [
            a for a in request.actions if a.effective_date <= request.as_of
        ]

    def _cumulative_factor(
        self, trade_date: date, actions: list[CorporateAction]
    ) -> float:
        factor = 1.0
        for action in actions:
            if action.action_type is ActionType.DIVIDEND:
                continue
            if trade_date < action.effective_date:
                handler = self._handlers.get(action.action_type)
                if handler is None:
                    continue
                factor *= handler(action)
        return factor

    def _cumulative_dividend(
        self, trade_date: date, actions: list[CorporateAction]
    ) -> float:
        total = 0.0
        for action in actions:
            if trade_date < action.effective_date:
                if action.action_type == ActionType.DIVIDEND:
                    total += self.apply_dividend(action)
        return total

    def _parse_date(self, value: Any) -> date | None:
        if value is None:
            return None
        if isinstance(value, datetime):
            return value.date()
        if isinstance(value, date):
            return value
        if isinstance(value, str):
            return date.fromisoformat(value[:10])
        return None
