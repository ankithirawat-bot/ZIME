"""
Schema DDL definitions.

Defines table creation SQL and indexes.
"""

from __future__ import annotations

SYMBOLS_TABLE = """
CREATE TABLE IF NOT EXISTS symbols (
    id          SERIAL PRIMARY KEY,
    symbol      VARCHAR(50)  NOT NULL,
    exchange    VARCHAR(10)  NOT NULL,
    instrument_type VARCHAR(20) NOT NULL DEFAULT 'EQ',
    isin        VARCHAR(12),
    provider_symbol VARCHAR(50) NOT NULL,
    created_at  TIMESTAMP    NOT NULL DEFAULT NOW(),
    updated_at  TIMESTAMP    NOT NULL DEFAULT NOW(),
    UNIQUE (symbol, exchange)
);
"""

DAILY_PRICES_TABLE = """
CREATE TABLE IF NOT EXISTS daily_prices (
    id          SERIAL PRIMARY KEY,
    symbol_id   INTEGER      NOT NULL,
    trade_date  TIMESTAMP    NOT NULL,
    open        DOUBLE PRECISION NOT NULL,
    high        DOUBLE PRECISION NOT NULL,
    low         DOUBLE PRECISION NOT NULL,
    close       DOUBLE PRECISION NOT NULL,
    volume      BIGINT       NOT NULL DEFAULT 0,
    provider    VARCHAR(50)  NOT NULL,
    created_at  TIMESTAMP    NOT NULL DEFAULT NOW(),
    UNIQUE (symbol_id, trade_date, provider)
);
"""

DATASET_VERSIONS_TABLE = """
CREATE TABLE IF NOT EXISTS dataset_versions (
    id            SERIAL PRIMARY KEY,
    symbol        VARCHAR(50)  NOT NULL,
    exchange      VARCHAR(10)  NOT NULL,
    dataset_type  VARCHAR(30)  NOT NULL,
    provider      VARCHAR(50)  NOT NULL,
    version       VARCHAR(100) NOT NULL,
    checksum      VARCHAR(64)  NOT NULL DEFAULT '',
    record_count  INTEGER      NOT NULL DEFAULT 0,
    created_at    TIMESTAMP    NOT NULL DEFAULT NOW(),
    UNIQUE (symbol, exchange, dataset_type, version)
);
"""

PROVIDERS_TABLE = """
CREATE TABLE IF NOT EXISTS providers (
    id              SERIAL PRIMARY KEY,
    name            VARCHAR(50)  NOT NULL UNIQUE,
    version         VARCHAR(20)  NOT NULL DEFAULT '1.0.0',
    supports_price_daily      BOOLEAN NOT NULL DEFAULT FALSE,
    supports_price_intraday   BOOLEAN NOT NULL DEFAULT FALSE,
    supports_financials       BOOLEAN NOT NULL DEFAULT FALSE,
    supports_corporate_actions BOOLEAN NOT NULL DEFAULT FALSE,
    supports_shareholding     BOOLEAN NOT NULL DEFAULT FALSE,
    supports_news             BOOLEAN NOT NULL DEFAULT FALSE,
    supports_earnings         BOOLEAN NOT NULL DEFAULT FALSE,
    created_at      TIMESTAMP    NOT NULL DEFAULT NOW()
);
"""

UPDATE_LOGS_TABLE = """
CREATE TABLE IF NOT EXISTS update_logs (
    id              SERIAL PRIMARY KEY,
    symbol          VARCHAR(50)  NOT NULL,
    exchange        VARCHAR(10)  NOT NULL,
    dataset_type    VARCHAR(30)  NOT NULL,
    provider        VARCHAR(50)  NOT NULL,
    version         VARCHAR(100) NOT NULL,
    start_date      TIMESTAMP,
    end_date        TIMESTAMP,
    records_inserted INTEGER     NOT NULL DEFAULT 0,
    status          VARCHAR(20) NOT NULL DEFAULT 'success',
    started_at      TIMESTAMP,
    completed_at    TIMESTAMP,
    created_at      TIMESTAMP    NOT NULL DEFAULT NOW()
);
"""

CORPORATE_ACTIONS_TABLE = """
CREATE TABLE IF NOT EXISTS corporate_actions (
    id              SERIAL PRIMARY KEY,
    symbol_id       INTEGER      NOT NULL,
    action_type     VARCHAR(20)  NOT NULL,
    effective_date  TIMESTAMP    NOT NULL,
    ratio           DOUBLE PRECISION,
    cash_amount     DOUBLE PRECISION,
    currency        VARCHAR(10)  NOT NULL DEFAULT 'INR',
    provider        VARCHAR(50)  NOT NULL,
    description     TEXT         NOT NULL DEFAULT '',
    metadata_json   TEXT         NOT NULL DEFAULT '{}',
    created_at      TIMESTAMP    NOT NULL DEFAULT NOW(),
    UNIQUE (symbol_id, action_type, effective_date, provider)
);
"""

INDEX_SYMBOLS = "CREATE INDEX IF NOT EXISTS idx_symbols_symbol ON symbols (symbol);"
INDEX_PRICES_SYMBOL_DATE = (
    "CREATE INDEX IF NOT EXISTS idx_prices_symbol_date ON daily_prices (symbol_id, trade_date);"
)
INDEX_PRICES_PROVIDER = "CREATE INDEX IF NOT EXISTS idx_prices_provider ON daily_prices (provider);"
INDEX_VERSIONS_SYMBOL = (
    "CREATE INDEX IF NOT EXISTS idx_versions_symbol ON dataset_versions (symbol);"
)
INDEX_VERSIONS_PROVIDER = (
    "CREATE INDEX IF NOT EXISTS idx_versions_provider ON dataset_versions (provider);"
)
INDEX_VERSIONS_TYPE = (
    "CREATE INDEX IF NOT EXISTS idx_versions_type ON dataset_versions (dataset_type);"
)
INDEX_LOGS_SYMBOL = "CREATE INDEX IF NOT EXISTS idx_logs_symbol ON update_logs (symbol);"
INDEX_LOGS_PROVIDER = "CREATE INDEX IF NOT EXISTS idx_logs_provider ON update_logs (provider);"
INDEX_LOGS_TYPE = "CREATE INDEX IF NOT EXISTS idx_logs_type ON update_logs (dataset_type);"
INDEX_CORP_ACTIONS_SYMBOL_DATE = (
    "CREATE INDEX IF NOT EXISTS idx_corp_actions_symbol_date "
    "ON corporate_actions (symbol_id, effective_date);"
)
INDEX_CORP_ACTIONS_PROVIDER = (
    "CREATE INDEX IF NOT EXISTS idx_corp_actions_provider "
    "ON corporate_actions (provider);"
)
INDEX_CORP_ACTIONS_TYPE = (
    "CREATE INDEX IF NOT EXISTS idx_corp_actions_type "
    "ON corporate_actions (action_type);"
)

_FUNDAMENTAL_COLUMNS = """
    id              SERIAL PRIMARY KEY,
    symbol_id       INTEGER      NOT NULL,
    period_type     VARCHAR(20)  NOT NULL,
    fiscal_year     INTEGER      NOT NULL,
    fiscal_quarter  INTEGER,
    report_date     TIMESTAMP    NOT NULL,
    filing_date     TIMESTAMP    NOT NULL,
    currency        VARCHAR(10)  NOT NULL DEFAULT 'INR',
    provider        VARCHAR(50)  NOT NULL,
    effective_from  TIMESTAMP    NOT NULL,
    effective_to    TIMESTAMP,
    metadata_json   TEXT         NOT NULL DEFAULT '{}',
    data_json       TEXT         NOT NULL DEFAULT '{}',
    created_at      TIMESTAMP    NOT NULL DEFAULT NOW(),
    UNIQUE (symbol_id, period_type, fiscal_year, fiscal_quarter, provider)
"""

COMPANY_PROFILES_TABLE = (
    "CREATE TABLE IF NOT EXISTS company_profiles (" + _FUNDAMENTAL_COLUMNS + ");"
)
INCOME_STATEMENTS_TABLE = (
    "CREATE TABLE IF NOT EXISTS income_statements (" + _FUNDAMENTAL_COLUMNS + ");"
)
BALANCE_SHEETS_TABLE = (
    "CREATE TABLE IF NOT EXISTS balance_sheets (" + _FUNDAMENTAL_COLUMNS + ");"
)
CASH_FLOWS_TABLE = (
    "CREATE TABLE IF NOT EXISTS cash_flows (" + _FUNDAMENTAL_COLUMNS + ");"
)
SHAREHOLDING_PATTERNS_TABLE = (
    "CREATE TABLE IF NOT EXISTS shareholding_patterns (" + _FUNDAMENTAL_COLUMNS + ");"
)
KEY_RATIOS_TABLE = (
    "CREATE TABLE IF NOT EXISTS key_ratios (" + _FUNDAMENTAL_COLUMNS + ");"
)

_FUNDAMENTAL_INDEXES = """
CREATE INDEX IF NOT EXISTS idx_{table}_symbol ON {table} (symbol_id);
CREATE INDEX IF NOT EXISTS idx_{table}_report ON {table} (report_date);
CREATE INDEX IF NOT EXISTS idx_{table}_filing ON {table} (filing_date);
CREATE INDEX IF NOT EXISTS idx_{table}_provider ON {table} (provider);
"""

INDEX_COMPANY_PROFILES = _FUNDAMENTAL_INDEXES.format(table="company_profiles")
INDEX_INCOME_STATEMENTS = _FUNDAMENTAL_INDEXES.format(table="income_statements")
INDEX_BALANCE_SHEETS = _FUNDAMENTAL_INDEXES.format(table="balance_sheets")
INDEX_CASH_FLOWS = _FUNDAMENTAL_INDEXES.format(table="cash_flows")
INDEX_SHAREHOLDING_PATTERNS = _FUNDAMENTAL_INDEXES.format(table="shareholding_patterns")
INDEX_KEY_RATIOS = _FUNDAMENTAL_INDEXES.format(table="key_ratios")

ALL_DDL = [
    SYMBOLS_TABLE,
    DAILY_PRICES_TABLE,
    DATASET_VERSIONS_TABLE,
    PROVIDERS_TABLE,
    UPDATE_LOGS_TABLE,
    CORPORATE_ACTIONS_TABLE,
    COMPANY_PROFILES_TABLE,
    INCOME_STATEMENTS_TABLE,
    BALANCE_SHEETS_TABLE,
    CASH_FLOWS_TABLE,
    SHAREHOLDING_PATTERNS_TABLE,
    KEY_RATIOS_TABLE,
    INDEX_SYMBOLS,
    INDEX_PRICES_SYMBOL_DATE,
    INDEX_PRICES_PROVIDER,
    INDEX_VERSIONS_SYMBOL,
    INDEX_VERSIONS_PROVIDER,
    INDEX_VERSIONS_TYPE,
    INDEX_LOGS_SYMBOL,
    INDEX_LOGS_PROVIDER,
    INDEX_LOGS_TYPE,
    INDEX_CORP_ACTIONS_SYMBOL_DATE,
    INDEX_CORP_ACTIONS_PROVIDER,
    INDEX_CORP_ACTIONS_TYPE,
    INDEX_COMPANY_PROFILES,
    INDEX_INCOME_STATEMENTS,
    INDEX_BALANCE_SHEETS,
    INDEX_CASH_FLOWS,
    INDEX_SHAREHOLDING_PATTERNS,
    INDEX_KEY_RATIOS,
]
