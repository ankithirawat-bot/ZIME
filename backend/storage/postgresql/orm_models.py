"""
SQLAlchemy ORM models.

Maps Python objects to PostgreSQL tables.
"""

from __future__ import annotations

from datetime import UTC, datetime

from sqlalchemy import (
    BigInteger,
    Boolean,
    Column,
    DateTime,
    Float,
    Integer,
    String,
    Text,
    UniqueConstraint,
)
from sqlalchemy.orm import DeclarativeBase

from backend.core.constants import DEFAULT_INSTRUMENT_TYPE


class Base(DeclarativeBase):
    """Declarative base for all ORM models."""


class Symbol(Base):
    """Unique symbol master table.

    Tracks every ticker symbol seen by any provider.
    """

    __tablename__ = "symbols"

    id = Column(Integer, primary_key=True, autoincrement=True)
    symbol = Column(String(50), nullable=False, index=True)
    exchange = Column(String(10), nullable=False)
    instrument_type = Column(String(20), nullable=False, default=DEFAULT_INSTRUMENT_TYPE)
    isin = Column(String(12), nullable=True)
    provider_symbol = Column(String(50), nullable=False)
    created_at = Column(DateTime, nullable=False, default=lambda: datetime.now(UTC))
    updated_at = Column(
        DateTime,
        nullable=False,
        default=lambda: datetime.now(UTC),
        onupdate=lambda: datetime.now(UTC),
    )

    __table_args__ = (
        UniqueConstraint("symbol", "exchange", name="uq_symbol_exchange"),
    )


class DailyPrice(Base):
    """Daily OHLCV price data table.

    Each row is one day of trading data for one symbol.
    """

    __tablename__ = "daily_prices"

    id = Column(Integer, primary_key=True, autoincrement=True)
    symbol_id = Column(Integer, nullable=False, index=True)
    trade_date = Column(DateTime, nullable=False, index=True)
    open = Column(Float, nullable=False)
    high = Column(Float, nullable=False)
    low = Column(Float, nullable=False)
    close = Column(Float, nullable=False)
    volume = Column(BigInteger, nullable=False, default=0)
    provider = Column(String(50), nullable=False, index=True)
    created_at = Column(DateTime, nullable=False, default=lambda: datetime.now(UTC))

    __table_args__ = (
        UniqueConstraint("symbol_id", "trade_date", "provider", name="uq_price_symbol_date_provider"),
    )


class DatasetVersion(Base):
    """Dataset version metadata table.

    Persists version tracking for all stored datasets.
    """

    __tablename__ = "dataset_versions"

    id = Column(Integer, primary_key=True, autoincrement=True)
    symbol = Column(String(50), nullable=False, index=True)
    exchange = Column(String(10), nullable=False)
    dataset_type = Column(String(30), nullable=False, index=True)
    provider = Column(String(50), nullable=False, index=True)
    version = Column(String(100), nullable=False, index=True)
    checksum = Column(String(64), nullable=False, default="")
    record_count = Column(Integer, nullable=False, default=0)
    created_at = Column(DateTime, nullable=False, default=lambda: datetime.now(UTC))

    __table_args__ = (
        UniqueConstraint(
            "symbol", "exchange", "dataset_type", "version",
            name="uq_version_symbol_type",
        ),
    )


class Provider(Base):
    """Provider registry table.

    Records known data providers.
    """

    __tablename__ = "providers"

    id = Column(Integer, primary_key=True, autoincrement=True)
    name = Column(String(50), nullable=False, unique=True)
    version = Column(String(20), nullable=False, default="1.0.0")
    supports_price_daily = Column(Boolean, nullable=False, default=False)
    supports_price_intraday = Column(Boolean, nullable=False, default=False)
    supports_financials = Column(Boolean, nullable=False, default=False)
    supports_corporate_actions = Column(Boolean, nullable=False, default=False)
    supports_shareholding = Column(Boolean, nullable=False, default=False)
    supports_news = Column(Boolean, nullable=False, default=False)
    supports_earnings = Column(Boolean, nullable=False, default=False)
    created_at = Column(DateTime, nullable=False, default=lambda: datetime.now(UTC))


class CorporateAction(Base):
    """Corporate actions master table.

    Stores validated corporate action events linked to a symbol.
    """

    __tablename__ = "corporate_actions"

    id = Column(Integer, primary_key=True, autoincrement=True)
    symbol_id = Column(Integer, nullable=False, index=True)
    action_type = Column(String(20), nullable=False, index=True)
    effective_date = Column(DateTime, nullable=False, index=True)
    ratio = Column(Float, nullable=True)
    cash_amount = Column(Float, nullable=True)
    currency = Column(String(10), nullable=False, default="INR")
    provider = Column(String(50), nullable=False, index=True)
    description = Column(Text, nullable=False, default="")
    metadata_json = Column(Text, nullable=False, default="{}")
    created_at = Column(DateTime, nullable=False, default=lambda: datetime.now(UTC))

    __table_args__ = (
        UniqueConstraint(
            "symbol_id", "action_type", "effective_date", "provider",
            name="uq_corporate_action_symbol_type_date_provider",
        ),
    )


class UpdateLog(Base):
    """Update audit log table.

    Records every storage operation for auditing.
    """

    __tablename__ = "update_logs"

    id = Column(Integer, primary_key=True, autoincrement=True)
    symbol = Column(String(50), nullable=False, index=True)
    exchange = Column(String(10), nullable=False)
    dataset_type = Column(String(30), nullable=False, index=True)
    provider = Column(String(50), nullable=False, index=True)
    version = Column(String(100), nullable=False)
    start_date = Column(DateTime, nullable=True)
    end_date = Column(DateTime, nullable=True)
    records_inserted = Column(Integer, nullable=False, default=0)
    status = Column(String(20), nullable=False, default="success")
    started_at = Column(DateTime, nullable=True)
    completed_at = Column(DateTime, nullable=True)
    created_at = Column(DateTime, nullable=False, default=lambda: datetime.now(UTC))


class _FundamentalColumns:
    """Shared columns for all fundamental statement tables."""

    symbol_id = Column(Integer, nullable=False, index=True)
    period_type = Column(String(20), nullable=False, index=True)
    fiscal_year = Column(Integer, nullable=False, index=True)
    fiscal_quarter = Column(Integer, nullable=True)
    report_date = Column(DateTime, nullable=False, index=True)
    filing_date = Column(DateTime, nullable=False, index=True)
    currency = Column(String(10), nullable=False, default="INR")
    provider = Column(String(50), nullable=False, index=True)
    effective_from = Column(DateTime, nullable=False, index=True)
    effective_to = Column(DateTime, nullable=True, index=True)
    metadata_json = Column(Text, nullable=False, default="{}")
    data_json = Column(Text, nullable=False, default="{}")
    created_at = Column(DateTime, nullable=False, default=lambda: datetime.now(UTC))


def _fundamental_unique(table_name: str) -> tuple:
    return (
        UniqueConstraint(
            "symbol_id", "period_type", "fiscal_year", "fiscal_quarter",
            "provider", "effective_from",
            name=f"uq_{table_name}_symbol_period_provider_eff",
        ),
    )


class CompanyProfileORM(Base, _FundamentalColumns):
    """Company profile table."""

    __tablename__ = "company_profiles"
    id = Column(Integer, primary_key=True, autoincrement=True)
    __table_args__ = _fundamental_unique("company_profiles")


class IncomeStatementORM(Base, _FundamentalColumns):
    """Income statement table."""

    __tablename__ = "income_statements"
    id = Column(Integer, primary_key=True, autoincrement=True)
    __table_args__ = _fundamental_unique("income_statements")


class BalanceSheetORM(Base, _FundamentalColumns):
    """Balance sheet table."""

    __tablename__ = "balance_sheets"
    id = Column(Integer, primary_key=True, autoincrement=True)
    __table_args__ = _fundamental_unique("balance_sheets")


class CashFlowORM(Base, _FundamentalColumns):
    """Cash flow statement table."""

    __tablename__ = "cash_flows"
    id = Column(Integer, primary_key=True, autoincrement=True)
    __table_args__ = _fundamental_unique("cash_flows")


class ShareholdingPatternORM(Base, _FundamentalColumns):
    """Shareholding pattern table."""

    __tablename__ = "shareholding_patterns"
    id = Column(Integer, primary_key=True, autoincrement=True)
    __table_args__ = _fundamental_unique("shareholding_patterns")


class KeyRatiosORM(Base, _FundamentalColumns):
    """Key ratios table."""

    __tablename__ = "key_ratios"
    id = Column(Integer, primary_key=True, autoincrement=True)
    __table_args__ = _fundamental_unique("key_ratios")
