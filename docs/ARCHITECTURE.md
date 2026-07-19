# ZIME Architecture

## Tech Stack

| Component | Technology |
|-----------|------------|
| Language | Python 3.12+ |
| Web Framework | FastAPI |
| ORM | SQLAlchemy 2.0 |
| Database | PostgreSQL |
| Data Source | yfinance (Yahoo Finance) |
| Analytics | pandas |
| Linting/Formatting | Ruff |
| Testing | pytest |

## Directory Structure

```
ZIME/
  backend/
    app/              FastAPI application
      main.py         App entry point
      database/       SQLAlchemy engine + session
      routers/        API route handlers
    config/           Settings (empty, to be implemented)
    core/             Shared types and enums
      enums.py        Signal, FactorCategory
      factor_result.py  FactorResult dataclass
      config.py       (empty, to be implemented)
      scoring.py      (empty, to be implemented)
    factors/          Quantitative factor framework
      base.py         BaseFactor ABC
      registry.py     FactorRegistry singleton
      price/          Price-based factors (SMA, EMA)
      momentum/       Momentum factors (empty)
      volume/         Volume factors (empty)
      risk/           Risk factors (empty)
      liquidity/      Liquidity factors (empty)
      fundamentals/   Fundamental factors (empty)
    engines/          Analysis engines (all empty)
    models/           SQLAlchemy models
      company.py      Company model
    repositories/     Data access layer
    services/         Business logic
      market_data.py  yfinance data importer
  data/               (empty, local data storage)
  docs/               Documentation
  tests/              Test suite
  frontend/           (empty, to be implemented)
  scripts/            (empty, utility scripts)
  research/           (empty, research notebooks)
```

## Layer Architecture

```
API Layer (FastAPI routers)
    |
Service Layer (business logic, orchestration)
    |
Engine Layer (scoring, strategy, evidence)
    |
Factor Layer (BaseFactor subclasses)
    |
Core Layer (enums, FactorResult, shared types)
    |
Data Layer (SQLAlchemy models, repositories)
```

Each layer imports only from layers below it. No upward imports.

## Factor Framework

### BaseFactor (abstract base class)

All quantitative factors inherit from BaseFactor. Each factor:

- Has a unique `name` (ClassVar[str])
- Has a `display_name` (ClassVar[str])
- Belongs to a `category` (ClassVar[FactorCategory])
- Implements `compute(symbol, **kwargs) -> FactorResult`
- Never raises exceptions (returns value=None on failure)

### FactorRegistry

Singleton that maps factor names to their classes. Factors register at import time. Used for discovery and lookup by the engine layer.

### FactorResult

Frozen dataclass representing standardized factor output. Contains:

- `factor_name`: Which factor produced this
- `factor_category`: Domain (technical, fundamental, etc.)
- `symbol`: Ticker symbol
- `value`: Numeric result (None if uncomputed)
- `signal`: Directional interpretation (BULLISH/BEARISH/NEUTRAL)
- `as_of`: Data freshness date
- `confidence`: Optional confidence score
- `metadata`: Factor-specific附加 data

## Data Flow

```
yfinance download -> PostgreSQL storage
                          |
                    Factor computation
                          |
                    Engine scoring
                          |
                    API response
```

## Current State

| Component | Status |
|-----------|--------|
| FastAPI app | Working (/, /health, /companies endpoints) |
| Company model | Working (6 columns) |
| Market data service | Working (5-day yfinance download) |
| Factor framework | Working (BaseFactor, FactorRegistry, FactorResult) |
| SMA factor | Working (configurable period) |
| EMA factor | Working (configurable period) |
| Price repository | Empty |
| All engines | Empty stubs |
| All other factors | Empty stubs |
| Tests | None |
| Frontend | None |
