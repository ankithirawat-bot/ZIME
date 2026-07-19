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
- [ ] RSI (momentum)
- [ ] MACD (momentum)
- [ ] Bollinger Bands (price)
- [ ] ATR (risk)
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
