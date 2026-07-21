"""
Fundamentals platform.

Stores, validates, versions and retrieves company fundamentals for
point-in-time research. Historical queries never expose data that was
not available on the reference date.
"""

from backend.fundamentals.exceptions import (
    DuplicateStatementError,
    FundamentalError,
    InvalidFundamentalError,
    StatementNotFoundError,
    UnsupportedStatementTypeError,
)
from backend.fundamentals.models import (
    BalanceSheet,
    CashFlowStatement,
    CompanyProfile,
    FundamentalBatch,
    FundamentalSnapshot,
    IncomeStatement,
    KeyRatios,
    ShareholdingPattern,
)
from backend.fundamentals.normalizer import FundamentalNormalizer
from backend.fundamentals.repository import FundamentalRepository
from backend.fundamentals.service import FundamentalService
from backend.fundamentals.types import PeriodType, StatementType
from backend.fundamentals.validator import (
    FundamentalValidator,
    ValidationReport,
)

__all__ = [
    "BalanceSheet",
    "CashFlowStatement",
    "CompanyProfile",
    "DuplicateStatementError",
    "FundamentalBatch",
    "FundamentalError",
    "FundamentalNormalizer",
    "FundamentalRepository",
    "FundamentalService",
    "FundamentalSnapshot",
    "IncomeStatement",
    "InvalidFundamentalError",
    "KeyRatios",
    "PeriodType",
    "ShareholdingPattern",
    "StatementNotFoundError",
    "StatementType",
    "UnsupportedStatementTypeError",
    "FundamentalValidator",
    "ValidationReport",
]
