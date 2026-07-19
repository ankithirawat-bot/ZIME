# ZIME Roadmap

## Vision

ZIME is an AI-powered investment intelligence platform for the Indian stock market.

The goal is not to build another stock screener.

The goal is to build an AI Portfolio Manager that automatically discovers high-quality investment opportunities across multiple time horizons.

---

## Completed Milestones

- **Capability 001** -- Core Factor Framework (BaseFactor, FactorRegistry, FactorResult, enums)
- **M2.1** -- Simple Moving Average (SMA) factor
- **M2.2** -- Exponential Moving Average (EMA) factor
- **M2.3** -- Weighted Moving Average (WMA) factor
- **M2.4** -- Volume-Weighted Moving Average (VWMA) factor
- **Sprint 5** -- ATR + Bollinger Bands factors
- **Sprint 6** -- 5 momentum factors (RSI, MACD, ROC, Williams %R, Stochastic Oscillator)
- **Sprint 7** -- FactorEngine (batch execution engine)
- **Sprint 8** -- ResearchService (end-to-end research orchestration)
- **Engineering Foundation** -- pyproject.toml, AGENTS.md, .editorconfig, docs

---

## Phase 1 -- Foundation

- [x] Project setup
- [x] PostgreSQL database
- [x] SQLAlchemy
- [x] FastAPI
- [x] Company master
- [x] Historical price importer
- [x] Duplicate protection
- [x] Core factor framework (BaseFactor, FactorRegistry, FactorResult)
- [x] Engineering infrastructure (pyproject.toml, AGENTS.md, .editorconfig)

---

## Phase 2 -- Data Engine

- [ ] Historical prices (proper model + repository)
- [ ] Daily updates
- [ ] Corporate actions
- [ ] Financial statements
- [ ] Shareholding data
- [ ] News ingestion

---

## Phase 3 -- Analytics Engine

- [x] SMA factor (price)
- [x] EMA factor (price)
- [x] WMA factor (price)
- [x] VWMA factor (price)
- [x] ATR factor (risk)
- [x] Bollinger Bands factor (price)
- [x] RSI (momentum)
- [x] MACD (momentum)
- [x] ROC (momentum)
- [x] Williams %R (momentum)
- [x] Stochastic Oscillator (momentum)
- [ ] OBV (volume)
- [ ] Financial ratios (fundamentals)
- [ ] Growth metrics (fundamentals)
- [ ] Quality metrics (fundamentals)
- [ ] Risk metrics (risk)

---

## Phase 4 -- Intelligence Engine

- [ ] AI stock ranking
- [ ] Quality score
- [ ] Growth score
- [ ] Value score
- [ ] Momentum score
- [ ] Risk score
- [ ] Overall score

---

## Phase 5 -- Opportunity Engine

Daily opportunities for:

- Intraday
- Swing
- Positional
- Long-term
- Multibaggers

Each recommendation should include:

- Entry
- Stop-loss
- Targets
- Position size
- Confidence
- Explanation

---

## Phase 6 -- Portfolio Intelligence

- Portfolio analysis
- Allocation suggestions
- Risk analysis
- AI recommendations

---

## Phase 7 -- AI Research Assistant

- Compare companies
- Explain earnings
- Analyze sectors
- Find hidden opportunities

---

## Sprint 8 -- ResearchService

**Status:** COMPLETE

**Goal:** Build the first end-to-end research workflow orchestrating data retrieval, factor execution, and result aggregation.

**Deliverables:**
- `backend/services/research_service.py` -- ResearchService class with `analyze()` method
- ResearchResult frozen dataclass with symbol, period, interval, generated_at, data_start, data_end, rows, execution_time_ms, factor_results, engine_errors, metadata
- Provider-agnostic data download via `_download_history()` (yfinance currently)
- Input validation: symbol, period, interval, empty dataframe, required columns
- Duplicate factor request detection via metadata warnings
- Factor registration imports (price + momentum packages)
- 64 tests covering success, invalid symbol, download failure, empty dataframe, missing columns, engine integration, partial failures, multiple factors, execution timing, metadata, duplicate detection, immutability, regression

**Test Count:** 64

**Key Design Decisions:**
- FactorRequest from `factor_engine.py` reused directly (no new request type)
- `_download_history()` isolated for future provider swap
- Column normalization: lowercase to match factor expectations, data copied to avoid mutation
- `_error_result()` helper centralizes error result construction
- All errors captured in ResearchResult (never crashes)
- No API, no database, no caching, no threading, no async

---

## Sprint 9 -- Research API

**Status:** COMPLETE

**Goal:** Expose the ResearchService through FastAPI endpoints with Pydantic validation.

**Deliverables:**
- `backend/api/__init__.py` -- API package init
- `backend/api/models.py` -- Pydantic request/response models (ResearchRequest, ResearchResponse, FactorRequestModel, FactorResultResponse, EngineErrorResponse, HealthResponse)
- `backend/api/research.py` -- FastAPI router with POST /api/v1/research and GET /api/v1/research/health
- `backend/api/test_research.py` -- 63 tests covering success, validation errors, unknown factor, internal failure, health endpoint, OpenAPI generation

**Test Count:** 63

**Key Design Decisions:**
- API layer contains no business logic — delegates entirely to ResearchService
- Pydantic models validate: empty symbol, invalid period, invalid interval, empty factor list, missing fields
- HTTP 400 for validation errors, HTTP 500 for internal failures, HTTP 422 for schema errors
- Stack traces never exposed to clients
- ResearchService mocked in all tests — no internet, no yfinance
- OpenAPI schema auto-generated with request/response models and examples

---

## Sprint 10 -- Market Data Provider Abstraction

**Status:** COMPLETE

**Goal:** Decouple ResearchService from yfinance by introducing a provider interface.

**Deliverables:**
- `backend/providers/__init__.py` -- Providers package init
- `backend/providers/base.py` -- MarketDataProvider ABC with `get_history()` abstract method
- `backend/providers/yfinance_provider.py` -- YFinanceProvider implementation
- `backend/providers/test_providers.py` -- 47 tests covering interface, DI, mocked provider scenarios, FakeProvider concrete implementation
- `backend/services/research_service.py` -- Refactored for dependency injection (provider param)

**Test Count:** 47

**Key Design Decisions:**
- MarketDataProvider ABC defines `get_history(symbol, period, interval) -> DataFrame | None`
- YFinanceProvider encapsulates all yfinance-specific logic
- ResearchService accepts optional `provider` param, defaults to YFinanceProvider
- No yfinance import in ResearchService — fully decoupled
- All existing tests pass unchanged (regression verified)

---

## Sprint 11 -- Command Line Interface (CLI)

**Status:** COMPLETE

**Goal:** Create a production-quality CLI exposing the ResearchService.

**Deliverables:**
- `backend/cli/__init__.py` -- CLI package init
- `backend/cli/main.py` -- argparse-based CLI with `analyze` command
- `backend/cli/formatter.py` -- terminal output formatting
- `backend/cli/test_cli.py` -- 54 tests covering parser, factor parsing, analysis, errors, help, formatting

**Test Count:** 54

**Key Design Decisions:**
- CLI delegates entirely to ResearchService — no business logic
- `parse_factor()` handles `EMA:20`, `RSI:14`, `MACD` formats
- Multiple `--factor` arguments supported
- Graceful error handling: invalid args, unknown factor, provider failure
- No stack traces exposed to users
- All tests mock ResearchService — no internet, no yfinance

---

## Sprint 12 -- Explainable Research Report

**Status:** COMPLETE

**Goal:** Convert raw factor results into deterministic, human-readable research reports using rule-based interpretation.

**Deliverables:**
- `backend/reporting/__init__.py` -- Reporting package init
- `backend/reporting/models.py` -- ResearchReport, Section, DataSummary dataclasses
- `backend/reporting/report_builder.py` -- rule-based interpretation (trend, momentum, volatility, warnings, summary)
- `backend/reporting/test_reporting.py` -- 47 tests covering all interpretation rules

**Test Count:** 47

**Key Design Decisions:**
- 100% deterministic rules — no AI/LLM
- Trend: MA alignment (bullish/bearish/mixed)
- Momentum: RSI zones, MACD crossovers, ROC direction, Williams %R, Stochastic
- Volatility: ATR states, Bollinger bandwidth and position
- Warnings: missing indicators, failed factors, insufficient history
- Overall summary generated from section interpretations
- Pure functions, no side effects
