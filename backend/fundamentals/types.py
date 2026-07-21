"""
Fundamentals platform types.

Enumerations used across the fundamentals platform.
"""

from __future__ import annotations

from enum import StrEnum


class PeriodType(StrEnum):
    """Reporting period cadence for a fundamental statement."""

    ANNUAL = "annual"
    QUARTERLY = "quarterly"
    TTM = "ttm"
    INTERIM = "interim"


class StatementType(StrEnum):
    """Supported fundamental dataset types.

    New statement types can be added here without changing any
    public API — the repository dispatches by statement type to its
    dedicated table through a registry.
    """

    PROFILE = "company_profile"
    INCOME_STATEMENT = "income_statement"
    BALANCE_SHEET = "balance_sheet"
    CASH_FLOW = "cash_flow"
    SHAREHOLDING = "shareholding_pattern"
    KEY_RATIOS = "key_ratios"
