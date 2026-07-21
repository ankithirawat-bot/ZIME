## Objective
- Implement ZIME, an evidence-driven investment research and decision platform for the Indian stock market, using capability-based sprint workflow.
- Current focus: analytics engines producing explainable `AnalyticsFact` from multiple independent signals without exposing indicator values.

## Important Details
- Project root: `D:\Documents\Business\Development\Projects\ZIME`
- Python 3.12, FastAPI, SQLAlchemy, PostgreSQL, pandas
- Enum naming convention: All enum member names are UPPERCASE; values are human-readable strings (TrendState / MomentumState / VolumeState / RelativeStrengthState / VolatilityState use `StrEnum`)
- pyproject.toml `testpaths = ["tests", "backend"]`; ruff select E,F,I,N,W,UP (no mypy/pyright enforced)
- Storage package pattern: frozen dataclass models → normalizer → validator → repository → service layer
- PowerShell does NOT support heredocs; probe scripts written to `C:\Users\ankit\AppData\Local\Temp\opencode\` and run with `$env:PYTHONPATH="D:\Documents\Business\Development\Projects\ZIME"`
- The 195 `ruff check backend/` errors are pre-existing in unrelated modules (factors/engines) outside sprint scope; per-sprint analytics packages are ruff-clean.
- `AnalyticsContext` extended with optional `benchmark_prices`/`sector_prices`/`industry_prices` (for RS); all engines use `TrendConfig`-subclass configs for shared `AnalyticsContext.config` compatibility.
- Calibration note (Volatility): probe-confirmed sigma→state mapping: 0.0005=Very Low, 0.006=Low, 0.012=Normal, 0.022=High, 0.03=Very High. Persistence signal uses continuous per-window normalized scores (not binary). Minimum bars for full signal availability = 41 (volatility_trend needs 2×20 returns).

## Work State
### Completed
- Sprints 14–23B: factor framework, RS, trend quality, patterns, volume, composite, trade planning, risk, portfolio, simulation, strategy infra+library
- Sprint 24A–24C: data platform, normalization, storage engine ABCs
- Sprint 24D: Upstox provider + retry + auth
- Sprint 24E: PostgreSQL repository refinement (820 tests)
- Sprint 24F: Corporate Actions Platform (55 tests, 875 total)
- Sprint 24G: Fundamentals Platform (45 tests, 920 total)
- Sprint 24H: Data Orchestration Platform — `backend/orchestration/` 41 tests, 961 total
- Sprint 24I: Data Quality & Multi-Provider Validation Platform — `backend/data_quality/` 58 tests, 1019 total
- Sprint 30B: Trend Engine — `backend/analytics/trend/` COMPLETE (27 tests, 1046 total, 100% impl cov)
- Sprint 30C: Momentum Engine — `backend/analytics/momentum/` COMPLETE (30 tests, 1076 total, 100% impl cov)
- Sprint 30D: Volume Engine — `backend/analytics/volume/` COMPLETE (33 tests, 1109 total, 100% impl cov); committed as `cf22bba` "feat(analytics): implement volume engine" (full analytics foundation: Core/Trend/Momentum/Volume + shared integration, 1109 tests)
- Sprint 30E: Relative Strength Engine — `backend/analytics/relative_strength/` COMPLETE (33 tests, 1142 total, 100% impl cov); committed as `208743a` "feat(analytics): implement relative strength engine"
- Sprint 30F: Volatility Engine — `backend/analytics/volatility/` COMPLETE (41 tests, 1183 total, 100% impl cov); NOT yet committed. Public API exposes only `AnalyticsFact(name="Volatility")`; NO ATR / Bollinger / VIX / raw volatility values.

### Active
- (none)

### Blocked
- (none)

## Next Move
1. (Optional) Commit Sprint 30F Volatility Engine — `git add backend/analytics/volatility backend/analytics/__init__.py` then commit (has NOT been done yet; do not commit unless explicitly requested).
2. Consider next analytics capability: e.g. a composite Market-Regime engine combining Trend/Momentum/Volume/RS/Volatility facts, or exposing analytics via the API/service layer.

## Relevant Files
- `backend/analytics/models.py`: `AnalyticsContext` (with `benchmark_prices`/`sector_prices`/`industry_prices`), `AnalyticsFact`, `MarketBar`, `CorporateAction`, `TrendConfig`
- `backend/analytics/__init__.py`: exports all engines (Trend/Momentum/Volume/RS/Volatility) + shared models
- `backend/analytics/volatility/__init__.py`: public exports
- `backend/analytics/volatility/exceptions.py`: `VolatilityError`, `InsufficientDataError`, `SignalError`
- `backend/analytics/volatility/evidence.py`: `Evidence`, `evidence_texts()`
- `backend/analytics/volatility/models.py`: `VolatilityState` (StrEnum), `VolatilityConfig(TrendConfig)`, `SignalOutput`, `EvaluatorResult`, `ScoringResult`
- `backend/analytics/volatility/signals.py`: 4 signals, `SignalRegistry`, `build_default_signal_registry()` — helpers `_closes`/`_returns`/`_stdev`, constants `HV_BASELINE`/`HV_SCALE`/`RANGE_BASELINE`/`RANGE_SCALE`
- `backend/analytics/volatility/evaluators.py`: `WeightedEvaluator.evaluate(outputs, config)` with `_WEIGHT_KEYS`
- `backend/analytics/volatility/scoring.py`: `VolatilityScorer.score(result, completeness)` (staticmethod) → state + confidence; `_state_from_score`, `_downgrade`
- `backend/analytics/volatility/volatility_engine.py`: `VolatilityEngine.analyze(context)` → `AnalyticsFact(name="Volatility")`; `_warnings()`
- `backend/analytics/volatility/test_volatility_engine.py`: 36 tests (all states, conflict, missing/edge data, registry, public-API, scoring, evaluators)
- Prior packages: `backend/analytics/trend/`, `backend/analytics/momentum/`, `backend/analytics/volume/`, `backend/analytics/relative_strength/`, `backend/fundamentals/`, `backend/orchestration/`, `backend/data_quality/`, `backend/storage/postgresql/` (ALL_DDL=30)
