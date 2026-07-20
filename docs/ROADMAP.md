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
- **Sprint 9** -- Research API (FastAPI endpoints)
- **Sprint 10** -- Market Data Provider Abstraction
- **Sprint 11** -- Command Line Interface (CLI)
- **Sprint 12** -- Explainable Research Report (rule-based)
- **Sprint 13** -- Market Regime Engine
- **Sprint 14** -- Relative Strength Engine (weighted multi-timeframe returns)
- **Sprint 15** -- Trend Quality Engine (structural trend health, trend stages)
- **Sprint 16** -- Pattern Recognition Engine (plugin-based, 5 detectors)
- **Sprint 17** -- Volume Intelligence Engine (institutional-quality volume analysis)
- **Sprint 18** -- Composite Decision Engine (weighted multi-engine scoring)
- **Sprint 19** -- Trade Planning Engine (entry/exit, stop-loss, position sizing, confidence)
- **Sprint 20** -- Risk Management Engine (per-trade risk, portfolio risk, rejection logic)
- **Sprint 20.1** -- Shared Core Package (constants, types, validation helpers, enums)
- **Sprint 21** -- Portfolio Construction Engine (ranked portfolio assembly, allocation)
- **Sprint 22** -- Simulation Engine (backtest, walk-forward, paper, Monte Carlo, stress test)
- **Sprint 23A** -- Strategy Infrastructure (StrategyEngine, EvaluationPipeline, StrategyRegistry)
- **Sprint 23B** -- Strategy Library (6 strategies: Momentum, Breakout, TrendFollowing, Growth, Quality, Custom)
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

---

## Sprint 13 -- Market Regime Engine

**Status:** COMPLETE

**Goal:** Implement a deterministic Market Regime Engine that evaluates overall market conditions and classifies the environment.

**Deliverables:**
- `backend/regime/__init__.py` -- Regime package init
- `backend/regime/models.py` -- MarketSnapshot, IndexData, BreadthData, MarketRegime, Regime dataclasses
- `backend/regime/regime_engine.py` -- rule-based scoring and classification
- `backend/regime/test_regime.py` -- 38 tests covering all regimes, missing data, confidence

**Test Count:** 38

**Key Design Decisions:**
- 100% deterministic rules — no AI/LLM
- Scoring: trend (+45), momentum (+10), breadth (+35), VIX (+/-5) = max 100
- Classification: Strong Bull (90+), Bull (75-89), Neutral (55-74), Weak (35-54), Bear (<35)
- Confidence based on data completeness
- Pure functions, frozen dataclasses
- All tests use mock MarketSnapshot objects — no internet

---

## Sprint 14 -- Relative Strength Engine

**Status:** COMPLETE

**Goal:** Implement a Relative Strength Engine that identifies whether a stock is a true market leader by comparing its performance against market, sector, and industry benchmarks.

**Deliverables:**
- `backend/relative_strength/__init__.py` -- Package init
- `backend/relative_strength/models.py` -- StockSnapshot, BenchmarkData, RelativeStrengthResult, Leadership dataclasses
- `backend/relative_strength/rs_engine.py` -- rule-based scoring and classification
- `backend/relative_strength/test_rs_engine.py` -- 55 tests covering weighted returns, leadership tiers, outperformance, missing data, confidence

**Test Count:** 55

**Key Design Decisions:**
- 100% deterministic rules — no AI/LLM
- Weighted multi-timeframe returns: 1M=10%, 3M=20%, 6M=30%, 12M=40%
- Scoring: market vs Nifty (+30), sector (+25), industry (+15), 52-week high distance (+20), relative momentum (+10) = max 100
- Classification: Leader (90+), Strong (75-89), Average (55-74), Weak (35-54), Laggard (<35)
- Outperformance thresholds: >20% → max, 10-20% → 0.67x, 0-10% → 0.33x, ≤0 → 0
- High score: within 5% → max, 5-10% → 0.75x, 10-20% → 0.5x, >20% → 0
- Relative momentum: acceleration = (stock_1m - market_1m) - (stock_1y - market_1y)
- Missing returns detection generates warnings and reduces confidence
- `low_52w` field added to StockSnapshot for future use
- Confidence based on data completeness (missing benchmarks, insufficient history)
- Pure functions, frozen dataclasses
- All tests use mock StockSnapshot objects — no internet

---

## Sprint 15 — Trend Quality Engine

**Status:** COMPLETE

**Goal:** Evaluate the structural quality of a stock's trend — whether it is healthy, persistent, and investable. This is one of the highest-weighted components of the ZIME Decision Engine.

**Deliverables:**
- `backend/trend/__init__.py` -- Package init
- `backend/trend/models.py` -- TrendSnapshot, TrendResult, TrendQuality, TrendStage dataclasses
- `backend/trend/trend_engine.py` -- rule-based scoring and classification
- `backend/trend/test_trend_engine.py` -- 62 tests covering all trend tiers, stages, alignment, slopes, structure, persistence, missing data, confidence

**Test Count:** 62

**Key Design Decisions:**
- 100% deterministic rules — no AI/LLM
- Scoring: MA alignment (+20), price position (+15), slopes (+20), structure (+20), persistence (+10), 52-week position (+15) = max 100
- Quality: Exceptional (90+), Strong (75-89), Healthy (55-74), Weak (35-54), Broken (<35)
- Stage: Early (<20 bars), Established (20-120), Extended (>120 + >20% above EMA20), Late (>120), Broken
- MA alignment: counts correctly ordered adjacent pairs (EMA20→EMA50→SMA150→SMA200)
- Structure: (higher_high_count + higher_low_count) × 4, max 20
- Persistence: trend_age thresholds (0, <20, 20-60, 60-120, 120+)
- Price extension warning: >20% above EMA20
- Missing data generates warnings and reduces confidence
- Pure functions, frozen dataclasses
- All tests use mock TrendSnapshot objects — no internet
- Future-ready: architecture supports ADX, Supertrend, linear regression without interface changes

---

## Sprint 16 — Pattern Recognition Engine

**Status:** COMPLETE

**Goal:** Implement a plugin-based pattern detection engine that identifies actionable chart patterns and provides breakout entry/exit levels.

**Deliverables:**
- `backend/patterns/__init__.py` -- Package init
- `backend/patterns/base.py` -- PatternDetector abstract base class
- `backend/patterns/models.py` -- PatternSnapshot, PatternResult, PatternType dataclasses
- `backend/patterns/engine.py` -- PatternEngine orchestrator with plugin registry
- `backend/patterns/detectors/vcp.py` -- VCP detector (35+20+20+15+10 scoring)
- `backend/patterns/detectors/flat_base.py` -- Flat base detector
- `backend/patterns/detectors/ascending_triangle.py` -- Ascending triangle detector
- `backend/patterns/detectors/cup_handle.py` -- Cup & handle detector
- `backend/patterns/detectors/high_tight_flag.py` -- High tight flag detector
- `tests/test_pattern_engine.py` -- 62 tests covering all detectors, entry/exit, missing data, confidence
- `tests/test_vcp.py` -- 31 VCP-specific tests
- `tests/test_flat_base.py` -- 10 flat base tests

**Test Count:** 103

**Key Design Decisions:**
- Plugin architecture: all detectors inherit from PatternDetector ABC
- Each detector has a `detect()` method returning PatternResult or None
- PatternEngine aggregates results from all detectors
- Entry/exit calculations: pivot, breakout, stop-loss, risk/reward
- Missing data returns None (no pattern detected) — never crashes
- Confidence based on data quality and pattern clarity

---

## Sprint 17 — Volume Intelligence Engine

**Status:** COMPLETE

**Goal:** Implement a volume intelligence engine that evaluates institutional-quality volume patterns for accumulation, distribution, and breakout confirmation.

**Deliverables:**
- `backend/volume/__init__.py` -- Package init
- `backend/volume/models.py` -- VolumeSnapshot, VolumeResult, VolumeQuality dataclasses
- `backend/volume/volume_engine.py` -- VolumeEngine class with `evaluate()` method
- `backend/volume/test_volume_engine.py` -- 44 tests covering all volume components, missing data, confidence

**Test Count:** 44

**Key Design Decisions:**
- Scoring: RVOL (+20), Breakout (+20), Dryup (+15), Accumulation (+20), Distribution (-15), Institutional (+10) = max 100
- Quality: Exceptional (90+), Strong (75-89), Healthy (55-74), Weak (35-54), Poor (<35)
- RVOL: 1.0-1.5 optimal, 1.5-2.0 high, 2.0-3.0 excessive, >3.0 dangerous
- Dry-up: <0.3x average signals consolidation before breakout
- Accumulation: positive close + volume surge = institutional buying
- Distribution: negative close + volume surge = institutional selling
- Missing data generates warnings and reduces confidence
- All tests use mock VolumeSnapshot objects — no internet

---

## Sprint 19 — Trade Planning Engine

**Status:** COMPLETE

**Goal:** Convert CompositeResult + PatternResult into executable trade plans with entry/exit levels, stop-losses, position sizing, and confidence scoring.

**Deliverables:**
- `backend/trade/__init__.py` -- Package init
- `backend/trade/models.py` -- TradePlan, TradeDecisionTrace, EntryType, TradeQuality, ExecutionStatus
- `backend/trade/trade_engine.py` -- TradeEngine with `evaluate(composite, pattern) → TradePlan`
- `tests/test_trade_engine.py` -- 35 tests covering entry types, stop-loss, targets, R:R, position sizing, confidence, validation

**Test Count:** 35

**Key Design Decisions:**
- Entry types: breakout (above pattern pivot), pullback (near support), reversal (bottom formation)
- Stop-loss: below pattern pivot or recent swing low, validated to be below entry
- Targets: risk-based (2R, 3R, 5R) from entry minus stop distance
- Position sizing: risk-based (1-2% account risk per trade)
- TradeDecisionTrace tracks reasoning for audit
- Validation flags for data quality issues

---

## Sprint 20 — Risk Management Engine

**Status:** COMPLETE

**Goal:** Transform TradePlan + CompositeResult into a capital-preserving execution plan with per-trade risk limits, portfolio risk grading, and rejection logic.

**Deliverables:**
- `backend/risk/__init__.py` -- Package init
- `backend/risk/models.py` -- RiskManagementResult, ExposureStatus, TradeRiskGrade, PortfolioRiskGrade, RejectionReason, RiskDecisionTrace
- `backend/risk/risk_engine.py` -- RiskEngine with `evaluate(trade_plan, composite) → RiskManagementResult`
- `tests/test_risk_engine.py` -- 30 tests covering risk grades, exposure, position sizing, rejection, portfolio risk

**Test Count:** 30

**Key Design Decisions:**
- `composite.position_size` is authoritative position limit (not trade_plan.position_size)
- Per-trade risk grade: Low (<1%), Medium (1-2%), High (2-3%), Extreme (>3%)
- Portfolio risk grade: Conservative, Moderate, Aggressive, Reckless
- Exposure status: New, Add, Reduce, Exit
- RejectionReason enum for why trades are rejected
- RiskDecisionTrace tracks all risk checks

---

## Sprint 20.1 — Shared Core Package

**Status:** COMPLETE

**Goal:** Extract shared constants, types, and validation helpers into `backend/core/` to eliminate duplication across engines.

**Deliverables:**
- `backend/core/__init__.py` -- Exports MAX_ITEMS, DEFAULT_MAX_RISK, MIN_RR_ACCEPTABLE, DEFAULT_CONFIDENCE, types, validation helpers
- `backend/core/constants.py` -- MAX_ITEMS=15, DEFAULT_MAX_RISK=1.0, MIN_RR_ACCEPTABLE=2.0, DEFAULT_CONFIDENCE=50.0
- `backend/core/types.py` -- Money, Percentage, Confidence, Score type aliases
- `backend/core/validation.py` -- 6 pure bool-returning validation helpers
- `backend/core/enums.py` -- Signal, FactorCategory

**Key Design Decisions:**
- Validation helpers return `bool` not raise exceptions
- All engines updated to use returned bools directly, removing try/except wrappers
- Type aliases for clarity (Money=Decimal, Percentage=float, etc.)
- Single source of truth for shared constants

---

## Sprint 21 — Portfolio Construction Engine

**Status:** COMPLETE

**Goal:** Consume multiple stock analyses and construct a ranked, diversified portfolio with allocation summaries.

**Deliverables:**
- `backend/portfolio/__init__.py` -- Package init
- `backend/portfolio/models.py` -- PortfolioCandidate, PortfolioInput, PortfolioResult, PortfolioPosition, PortfolioSummary, AllocationSummary, PortfolioDecisionTrace
- `backend/portfolio/portfolio_engine.py` -- PortfolioEngine with `evaluate(PortfolioInput) → PortfolioResult`
- `tests/test_portfolio_engine.py` -- 25 tests covering ranking, allocation, summary, traces

**Test Count:** 25

**Key Design Decisions:**
- Input: `PortfolioInput` with `PortfolioCandidate` tuples (symbol + RiskManagementResult)
- Ranking: confidence → risk grade → alphabetical
- Allocation: positions get weight proportional to confidence, capped by risk limits
- PortfolioSummary aggregates total allocation, position count, avg confidence
- PortfolioDecisionTrace tracks ranking and allocation decisions

---

## Sprint 22 — Simulation Engine

**Status:** COMPLETE

**Goal:** Execute backtests, walk-forward tests, paper trading, Monte Carlo simulations, and stress tests against portfolio allocations.

**Deliverables:**
- `backend/simulation/__init__.py` -- Package init
- `backend/simulation/models.py` -- SimulationMode (ABC), SimulationModeType (StrEnum), SimulationConfiguration, SimulationInput, SimulationResult, SimulationSummary, SimulationStatistics, EquityCurvePoint, TradeLogEntry, SimulationDecisionTrace
- `backend/simulation/execution_modes.py` -- BacktestMode, WalkForwardMode, PaperMode, MonteCarloMode, StressTestMode (all inherit SimulationMode ABC)
- `backend/simulation/simulation_engine.py` -- SimulationEngine with `evaluate(SimulationInput) → SimulationResult`
- `backend/simulation/metrics.py` -- 9 metric helpers (sharpe, sortino, calmar, max_dd, profit_factor, expectancy, cagr, win_rate, loss_rate)
- `tests/test_simulation_engine.py` -- 44 tests covering all modes, metrics, configuration, traces

**Test Count:** 44

**Key Design Decisions:**
- `SimulationMode` ABC with `configure()`, `execute()`, `summary()` abstract methods
- `SimulationModeType` StrEnum for mode identifiers (backtest, walk_forward, paper, monte_carlo, stress_test)
- `SimulationConfiguration` dataclass: initial_capital, commission_pct, slippage_pct, risk_per_trade_pct, max_positions, period, interval, start_date, end_date
- `SimulationInput` takes `SimulationConfiguration` + `PortfolioResult`
- `_MODES` registry maps SimulationModeType → SimulationMode instance
- 9 pure metric functions in metrics.py

---

## Sprint 23A — Strategy Infrastructure

**Status:** COMPLETE

**Goal:** Build the strategy abstraction layer that allows different investment strategies to be defined, registered, and evaluated through a common pipeline.

**Deliverables:**
- `backend/strategy/__init__.py` -- Exports `StrategyEngine`
- `backend/strategy/models.py` -- StrategyType, StrategyConfiguration, StrategyInput, EvaluationContext, StrategySummary, StrategyDecisionTrace, StrategyResult
- `backend/strategy/pipeline.py` -- `EvaluationPipeline.run(StrategyInput) → EvaluationContext`
- `backend/strategy/strategies.py` -- Strategy ABC, MomentumStrategy
- `backend/strategy/strategy_registry.py` -- StrategyRegistry (register, resolve, has, registered_types)
- `backend/strategy/strategy_engine.py` -- `StrategyEngine.evaluate(StrategyInput) → StrategyResult`
- `backend/strategy/test_strategy_engine.py` -- 59 tests covering pipeline, registry, engine, momentum strategy

**Test Count:** 59

**Key Design Decisions:**
- Single public API: `StrategyEngine.evaluate(StrategyInput) → StrategyResult`
- `EvaluationPipeline` runs 8 engines in order: Market Regime → RS → Trend → Pattern → Volume → Composite → Trade → Risk
- `Strategy` ABC with `configure()`, `evaluate()`, `summary()` abstract methods
- `StrategyRegistry` singleton: register, resolve, has, registered_types
- `EvaluationContext` frozen dataclass holding all engine results
- `StrategyDecisionTrace` records pipeline results, strategy scoring, and configuration used

---

## Sprint 23B — Strategy Library

**Status:** COMPLETE

**Goal:** Extend the strategy system with 5 additional investment strategies beyond Momentum, and refine the StrategyConfiguration model.

**Deliverables:**
- Extended `StrategyType` enum: MOMENTUM, BREAKOUT, TREND_FOLLOWING, GROWTH, QUALITY, CUSTOM
- `backend/strategy/strategies.py` -- Added BreakoutStrategy, TrendFollowingStrategy, GrowthStrategy, QualityStrategy, CustomStrategy
- Extended `StrategyConfiguration`: 7 new fields (minimum_pattern_score, minimum_volume_score, minimum_trend_score, minimum_rs_score, require_strong_trend, require_strong_pattern, ignore_pattern)
- All 6 strategies registered in engine
- 113 strategy tests (59 original + 54 new)

**Test Count:** 113 (strategy tests), 493 (total project)

**Key Design Decisions:**
- Each strategy has unique scoring formula based on its investment thesis
- BreakoutStrategy: favors volume-confirmed breakouts above resistance
- TrendFollowingStrategy: requires strong trend health, penalizes weak trends
- GrowthStrategy: emphasizes momentum and trend quality
- QualityStrategy: balanced approach requiring healthy trend, strong volume, good pattern
- CustomStrategy: user-configurable thresholds via StrategyConfiguration
- All 6 strategies registered via StrategyRegistry.register()

---

## Sprint 18 — Composite Decision Engine

**Status:** COMPLETE

**Goal:** Combine outputs of all analysis engines (market regime, relative strength, trend quality, pattern recognition, volume intelligence) into a single investment decision with weighted scoring and gating rules.

**Deliverables:**
- `backend/composite/__init__.py` -- Package init
- `backend/composite/models.py` -- CompositeResult, InvestmentGrade, Recommendation dataclasses
- `backend/composite/composite_engine.py` -- CompositeEngine class with `evaluate()` method
- `tests/test_composite_engine.py` -- 22 tests covering weighted scoring, gating rules, grade classification, position sizing, confidence, recommendations, reasons aggregation

**Test Count:** 22

**Key Design Decisions:**
- Engine weights: Market 15%, RS 20%, Trend 25%, Pattern 20%, Volume 20%
- Grades: A+ (95+), A (90+), A- (85+), B+ (80+), B (75+), B- (70+), C (60+), D (50+), F (<50)
- Recommendations: Strong Buy (95+), Buy (85+), Watchlist (75+), Monitor (60+), Avoid (<60)
- Position sizing: 0-25% based on score, capped at 10% for weak RS
- Gating rules: Bear market → Monitor, Broken trend → Monitor, Weak pattern → no Strong Buy
- Confidence calculated from signal agreement (variance penalty) and data completeness
- Reasons/warnings aggregated from all engines with deduplication
- All tests use mock engine results — no internet
