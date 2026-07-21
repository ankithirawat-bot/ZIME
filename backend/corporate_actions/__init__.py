"""
Corporate Actions platform.

Stores, validates and applies corporate actions to historical market
data while preserving raw prices. Adjusted prices are generated on
demand and raw data is never mutated.
"""

from backend.corporate_actions.adjustment_engine import AdjustmentEngine
from backend.corporate_actions.exceptions import (
    CorporateActionError,
    DuplicateActionError,
    InvalidActionError,
    OverlappingActionError,
    UnsupportedActionTypeError,
)
from backend.corporate_actions.models import (
    AdjustedPrice,
    AdjustmentRequest,
    AdjustmentResult,
    CorporateAction,
    CorporateActionBatch,
)
from backend.corporate_actions.normalizer import CorporateActionNormalizer
from backend.corporate_actions.repository import CorporateActionRepository
from backend.corporate_actions.types import ActionType, AdjustmentType
from backend.corporate_actions.validator import (
    CorporateActionValidator,
    ValidationReport,
)

__all__ = [
    "ActionType",
    "AdjustmentEngine",
    "AdjustmentRequest",
    "AdjustmentResult",
    "AdjustedPrice",
    "AdjustmentType",
    "CorporateAction",
    "CorporateActionBatch",
    "CorporateActionError",
    "CorporateActionNormalizer",
    "CorporateActionRepository",
    "CorporateActionValidator",
    "DuplicateActionError",
    "InvalidActionError",
    "OverlappingActionError",
    "UnsupportedActionTypeError",
    "ValidationReport",
]
