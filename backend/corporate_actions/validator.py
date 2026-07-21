"""
Corporate Actions validator.

Validates corporate action events and rejects invalid ones.
"""

from __future__ import annotations

from dataclasses import dataclass

from backend.corporate_actions.exceptions import (
    InvalidActionError,
    OverlappingActionError,
    UnsupportedActionTypeError,
)
from backend.corporate_actions.models import CorporateAction, CorporateActionBatch
from backend.corporate_actions.types import ActionType


@dataclass(frozen=True)
class ValidationReport:
    """Outcome of validating corporate actions.

    Attributes:
        valid:                 True when all actions are valid.
        valid_actions:         Actions that passed validation.
        errors:                Blocking errors keyed by action index.
        duplicate_keys:        Detected duplicate identifiers.
    """

    valid: bool
    valid_actions: tuple[CorporateAction, ...]
    errors: tuple[str, ...]
    duplicate_keys: tuple[str, ...]


class CorporateActionValidator:
    """Validates corporate action events."""

    def validate_batch(self, batch: CorporateActionBatch) -> ValidationReport:
        """Validate every action in a batch.

        Args:
            batch: Batch of corporate actions.

        Returns:
            ValidationReport with valid actions and errors.
        """
        errors: list[str] = []
        valid_actions: list[CorporateAction] = []
        seen: set[str] = set()
        duplicate_keys: list[str] = []

        for action in batch.actions:
            try:
                self.validate(action)
            except (
                InvalidActionError,
                UnsupportedActionTypeError,
                OverlappingActionError,
            ) as exc:
                errors.append(str(exc))
                continue

            key = self._identity_key(action)
            if key in seen:
                dup = f"{action.symbol}:{action.action_type.value}:{action.effective_date.isoformat()}"
                errors.append(f"Duplicate corporate action: {dup}")
                duplicate_keys.append(dup)
                continue

            seen.add(key)
            valid_actions.append(action)

        return ValidationReport(
            valid=len(errors) == 0,
            valid_actions=tuple(valid_actions),
            errors=tuple(errors),
            duplicate_keys=tuple(duplicate_keys),
        )

    def validate(self, action: CorporateAction) -> None:
        """Validate a single corporate action in place.

        Raises:
            InvalidActionError:        On malformed fields.
            UnsupportedActionTypeError: On unknown action type.
            OverlappingActionError:    On incompatible overlaps.
        """
        if not action.symbol:
            raise InvalidActionError("Corporate action missing symbol")
        if not action.exchange:
            raise InvalidActionError("Corporate action missing exchange")

        self._validate_action_type(action)
        self._validate_effective_date(action)
        self._validate_ratio(action)
        self._validate_cash(action)
        self._validate_overlap_constraints(action)

    def _validate_action_type(self, action: CorporateAction) -> None:
        if action.action_type not in ActionType:
            raise UnsupportedActionTypeError(action.action_type.value)

    def _validate_effective_date(self, action: CorporateAction) -> None:
        if action.effective_date is None:
            raise InvalidActionError(
                f"{action.symbol}: corporate action missing effective_date"
            )

    def _validate_ratio(self, action: CorporateAction) -> None:
        if action.ratio is None:
            return
        if action.action_type in (ActionType.SPLIT, ActionType.BONUS):
            if action.ratio <= 0:
                raise InvalidActionError(
                    f"{action.symbol}: {action.action_type.value} ratio must be positive, got {action.ratio}"
                )
            if action.ratio == 1.0:
                raise InvalidActionError(
                    f"{action.symbol}: {action.action_type.value} ratio must differ from 1.0"
                )
        elif action.ratio <= 0:
            raise InvalidActionError(
                f"{action.symbol}: negative or zero ratio is invalid: {action.ratio}"
            )

    def _validate_cash(self, action: CorporateAction) -> None:
        if action.cash_amount is None:
            return
        if action.action_type == ActionType.DIVIDEND:
            if action.cash_amount < 0:
                raise InvalidActionError(
                    f"{action.symbol}: dividend cash_amount must be non-negative, got {action.cash_amount}"
                )
        elif action.cash_amount < 0:
            raise InvalidActionError(
                f"{action.symbol}: negative cash_amount is invalid: {action.cash_amount}"
            )

    def _validate_overlap_constraints(self, action: CorporateAction) -> None:
        if action.action_type in (ActionType.RIGHTS, ActionType.BUYBACK):
            if action.ratio is None and action.cash_amount is None:
                raise InvalidActionError(
                    f"{action.symbol}: {action.action_type.value} requires ratio or cash_amount metadata"
                )

    def _identity_key(self, action: CorporateAction) -> str:
        return (
            f"{action.symbol}:{action.exchange}:"
            f"{action.action_type.value}:{action.effective_date.isoformat()}"
        )

    def detect_duplicates(self, actions: tuple[CorporateAction, ...]) -> list[str]:
        """Return identifiers of duplicate actions within a collection.

        Args:
            actions: Corporate actions to inspect.

        Returns:
            List of duplicate identity keys (first occurrence excluded).
        """
        seen: set[str] = set()
        duplicates: list[str] = []
        for action in actions:
            key = self._identity_key(action)
            if key in seen:
                duplicates.append(key)
            else:
                seen.add(key)
        return duplicates
