"""
Corporate Actions normalizer.

Converts provider-specific payloads into canonical CorporateAction
models. Provider-specific formats MUST NOT leak outside this layer.
"""

from __future__ import annotations

from datetime import date, datetime
from typing import Any

from backend.core.constants import DEFAULT_EXCHANGE
from backend.corporate_actions.exceptions import UnsupportedActionTypeError
from backend.corporate_actions.models import CorporateAction, CorporateActionBatch
from backend.corporate_actions.types import ActionType


class CorporateActionNormalizer:
    """Translates provider payloads into canonical models."""

    _TYPE_MAP: dict[str, ActionType] = {
        "split": ActionType.SPLIT,
        "bonus": ActionType.BONUS,
        "dividend": ActionType.DIVIDEND,
        "rights": ActionType.RIGHTS,
        "buyback": ActionType.BUYBACK,
    }

    def normalize(self, payload: dict[str, Any], provider: str) -> CorporateAction:
        """Normalize a single provider payload.

        Args:
            payload: Provider-specific raw record.
            provider: Originating provider name.

        Returns:
            Canonical CorporateAction.

        Raises:
            UnsupportedActionTypeError: If action_type is unknown.
            ValueError: If required fields are missing or malformed.
        """
        raw_type = payload.get("action_type") or payload.get("type")
        if raw_type is None:
            raise ValueError("Missing action_type in payload")
        action_type = self._resolve_type(str(raw_type))

        symbol = payload.get("symbol")
        exchange = payload.get("exchange", DEFAULT_EXCHANGE)
        if not symbol:
            raise ValueError("Missing symbol in payload")

        effective_date = self._parse_date(
            payload.get("effective_date") or payload.get("date")
        )
        if effective_date is None:
            raise ValueError("Missing effective_date in payload")

        ratio = self._parse_float(payload.get("ratio"))
        cash_amount = self._parse_float(payload.get("cash_amount") or payload.get("amount"))
        currency = str(payload.get("currency", "INR"))

        description = str(payload.get("description", ""))
        raw_metadata = payload.get("metadata", {})
        if not isinstance(raw_metadata, dict):
            raw_metadata = {}
        metadata = dict(raw_metadata)

        return CorporateAction(
            symbol=str(symbol),
            exchange=str(exchange),
            action_type=action_type,
            effective_date=effective_date,
            provider=provider,
            ratio=ratio,
            cash_amount=cash_amount,
            currency=currency,
            description=description,
            metadata=metadata,
        )

    def normalize_batch(
        self,
        payloads: list[dict[str, Any]],
        provider: str,
        source: str = "",
    ) -> CorporateActionBatch:
        """Normalize a list of provider payloads into a batch.

        Args:
            payloads: Provider-specific raw records.
            provider: Originating provider name.
            source: Origin label for the batch.

        Returns:
            CorporateActionBatch of normalized actions.
        """
        actions = tuple(self.normalize(p, provider) for p in payloads)
        return CorporateActionBatch(actions=actions, source=source)

    def _resolve_type(self, raw_type: str) -> ActionType:
        key = raw_type.strip().lower()
        mapped = self._TYPE_MAP.get(key)
        if mapped is None:
            raise UnsupportedActionTypeError(raw_type)
        return mapped

    def _parse_date(self, value: Any) -> date | None:
        if value is None:
            return None
        if isinstance(value, datetime):
            return value.date()
        if isinstance(value, date):
            return value
        if isinstance(value, str):
            return date.fromisoformat(value[:10])
        raise ValueError(f"Unrecognized date value: {value!r}")

    def _parse_float(self, value: Any) -> float | None:
        if value is None or value == "":
            return None
        if isinstance(value, (int, float)):
            return float(value)
        if isinstance(value, str):
            return float(value.strip())
        raise ValueError(f"Unrecognized numeric value: {value!r}")
