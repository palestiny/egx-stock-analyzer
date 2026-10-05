# EGXBot Feature Parity Audit

**Date:** 2026-10-05  
**Base:** `main` at `a2bfee4a933a5756f198ab023fafcd9e0d5139d5`  
**Audit branch:** `feature/egxbot-parity-audit`  
**Reference:** Current public EGXBot guide verified by EGXBot on 2026-09-12.

## Purpose

Establish a verified capability gap between the current EGX Stock Analyzer and the current public EGXBot product before implementing parity or the US-market extension.

This is a capability audit, not a UI/source-code clone.

## EGXBot Reference Surfaces

EGXBot currently exposes three product surfaces:

1. Telegram Bot
2. Live EGX Terminal
3. AI Assistant

The public guide lists market discovery, stock research, advanced technical analysis, intraday/order-flow features, signals/alerts, portfolio analysis, strategy research, and AI-assisted research.

## Current Project Position

The repository is a modular monolith and M61 remains the active milestone. The current main branch already contains meaningful foundations for:

- technical analysis;
- support/resistance;
- trend;
- momentum and volume analysis;
- technical scoring;
- fundamental analysis;
- stock quality and entry quality;
- opportunity classification;
- market intelligence;
- movers, sectors, breakouts and Fibonacci scanning;
- canonical signals;
- alerts and notification boundaries;
- portfolio/trade-related application boundaries;
- analysis comparison/history/reporting;
- deterministic backtesting infrastructure;
- historical-data provenance and integrity boundaries.

The repository must not claim production readiness for a capability merely because a calculation or endpoint exists. Data freshness, source coverage, operational behavior, and deterministic evidence remain separate acceptance dimensions.

## Capability Matrix

| Capability family | EGXBot reference | Current analyzer | Gap |
|---|---|---|---|
| Market overview / pulse | Yes | Partial foundation | Market-breadth/live-pulse depth |
| Movers / leaders / laggards | Yes | Present | Validate full live behavior |
| Sectors / rotation | Yes | Present foundation | Rotation depth + live evidence |
| Smart/technical scanners | Yes | Present | Expand scanner contract/coverage |
| Fibonacci opportunity scanner | Yes | Present | Validate data/readiness |
| Breakout scanner | Yes | Present | Validate lifecycle/readiness |
| Whale / large-flow detection | Yes | Missing as verified capability | High |
| Stock technical report | Yes | Present | Broaden report/confluence |
| Financial report | Yes | Present foundation | External data coverage/readiness |
| Fair value | Yes | Present API/domain evidence | Validate model/data provenance |
| Support/resistance | Yes | Present | Deepen multi-source confluence |
| Trend | Yes | Present | Multi-timeframe expansion |
| Risk analysis | Yes | Present foundations | Consolidate risk contract |
| Multi-timeframe | Yes | Partial | High |
| Targets / stop planning | Yes | Partial through entry/signal models | Consolidate canonical plan |
| Scenario analysis | Yes | Partial | High |
| Fibonacci | Yes | Present | Expand opportunity/confluence |
| Divergence | Yes | Missing as verified production capability | High |
| Classical chart patterns | Yes | Missing as verified production capability | High |
| Harmonic | Yes | Missing | High |
| SMC | Yes | Missing | High |
| Elliott | Yes | Missing | Medium/High |
| Gann / time cycles | Yes | Missing | Medium |
| Fractal analysis | Yes | Missing | Medium |
| Volume / order-flow analysis | Yes | Partial | Requires intraday/depth data |
| EGX Sniper-style confluence | Yes | Partial conceptually | High |
| Live market watch | Yes | Partial | Requires verified live feed |
| Order book / depth | Yes | Missing as verified capability | Data-dependent |
| Time & Sales | Yes | Missing | Data-dependent |
| Price-level aggregation | Yes | Missing | Data-dependent |
| Intraday signals | Yes | Partial | Requires intraday feed + lifecycle |
| Liquidity monitoring | Yes | Partial | Real-time evidence needed |
| Structured signals | Yes | Present | Mature contract, expand producers |
| Signal lifecycle | Yes | Partial | Needs full activation/TP/SL lifecycle |
| Price alerts | Yes | Present | Delivery/readiness verification |
| Pattern/Fibonacci alerts | Yes | Missing/partial | High |
| Push/Telegram notifications | Yes | Present boundary | Provider delivery validation |
| Portfolio holdings/P&L | Yes | Partial | Complete portfolio domain needed |
| Concentration / sector exposure | Yes | Partial | Complete portfolio analytics |
| Portfolio health/risk score | Yes | Missing | High |
| Per-position verdict | Yes | Partial | Needs portfolio analysis orchestration |
| EGX30 context | Yes | Partial | Market-context engine |
| What-if analysis | Yes | Missing | Medium/High |
| Daily pre-market briefing | Yes | Missing | Medium |
| Screenshot portfolio import | Yes | Missing | Medium |
| Backtesting | Yes | Present foundation | Real dataset acceptance still blocks conclusions |
| Bounded rule testing | Yes | Present foundation | Expand strategies |
| Tracked ideas | Yes | Partial | Persistence/follow-up workflow |
| Signal track record | Yes | Partial | Needs canonical signal outcome measurement |
| Model portfolio | Yes | Missing | Medium |
| Copy-trading-style notifications | Yes | Partial concept | Keep informational; no broker execution |
| AI stock research | Yes | Missing as product capability | High |
| AI market scans | Yes | Missing as product capability | High |
| AI portfolio questions | Yes | Missing | High |
| Arabic/English intent understanding | Yes | Missing | Medium/High |
| Evidence-aware AI explanations | Yes | Architectural direction | High |
| Persistent AI portfolio context | Yes | Missing | Medium |

## Important Findings

### 1. We are not starting from zero

The existing analyzer already has enough domain/application structure to become the target platform without a rewrite.

### 2. The largest missing layer is not another indicator

The largest gaps are:

- advanced-analysis engines;
- intraday/microstructure data;
- portfolio intelligence;
- signal lifecycle/track record;
- AI research interface;
- real operational data readiness.

### 3. EGXBot parity and US support should share the same core

The parity work should define market-neutral contracts for:

- market snapshots;
- scanners;
- signals;
- risk;
- portfolio analytics;
- alerts;
- analysis evidence.

EGX and US-specific data acquisition must remain adapters.

### 4. Real-time claims require real-time data

Daily OHLCV cannot legitimately mark order book, Time & Sales, liquidity pulse, or intraday microstructure capabilities as production-ready.

### 5. M61 remains a dependency

The current M61 historical-dataset blocker is independent of parity. We should not claim backtest performance until the accepted real dataset is frozen and verified.

## Priority Order

### P0 — Platform contracts

- capability readiness metadata;
- canonical Signal;
- market snapshot;
- scanner query/result;
- risk/trade-plan contract;
- alert lifecycle;
- portfolio analytics contract.

### P1 — High-value EGX parity

- market overview;
- full stock report;
- scanner expansion;
- Fibonacci opportunity scanning;
- structured signal lifecycle;
- portfolio/P&L;
- comparison;
- financial/fair-value evidence.

### P2 — Advanced analysis

- divergence;
- classical patterns;
- Harmonic;
- SMC;
- Elliott;
- Gann;
- fractals;
- multi-timeframe confluence.

### P3 — Intraday

- live market watch;
- order book;
- Time & Sales;
- price aggregation;
- liquidity pulse;
- intraday opportunity lifecycle.

### P4 — Intelligence

- AI assistant;
- portfolio intelligence;
- daily briefing;
- what-if analysis;
- evidence-aware research;
- news/context;
- global markets.

### P5 — US market extension

Reuse the P0 contracts and add US-specific adapters for:

- real-time market data;
- US universe;
- US scanners;
- VWAP/ORB/momentum setups;
- broker execution only behind a future explicit execution gate.

## Decision

Do **not** merge the old `feature/egxbot-feature-parity-foundation` branch directly into current `main`. It is 7 commits ahead but 8 commits behind and contains an earlier parity slice.

The correct path is to continue from current `main`, preserving only the useful capability/signal foundations and updating the parity design against today's M61 state.

## Acceptance Boundary

This audit is complete as a mapping artifact.

Implementation of the next parity capability requires its own design gate and TDD slice. No production-readiness claim is made for external-data-dependent capabilities until the required source and operational behavior are verified.
