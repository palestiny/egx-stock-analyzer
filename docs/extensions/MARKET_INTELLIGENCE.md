# Market Intelligence Extension

**Project:** EGX Stock Analyzer  
**Status:** Proposed product/capability extension  
**Execution authority:** docs/ROADMAP.md  
**Architecture review:** docs/DEC-133-MARKET-INTELLIGENCE-ARCHITECTURE-REVIEW-GATE.md

## Purpose

This document is the durable product/capability extension for evolving the EGX Stock Analyzer into a market-agnostic Market Intelligence & Decision Support Platform.

It is not a second execution roadmap. Current execution is always determined by docs/ROADMAP.md.

## Product Target

The long-term system should:

1. ingest reliable market, financial, event and contextual data;
2. preserve provenance and point-in-time semantics;
3. understand instrument, market and sector structure;
4. detect liquidity, participation, flow, regime and rotation changes;
5. discover asymmetric opportunities;
6. produce explainable entry, hold, reduce, exit and re-entry plans;
7. validate strategies historically and out-of-sample;
8. support multiple markets through adapters;
9. produce evidence-backed recommendations rather than opaque predictions.

It is decision support, not a guarantee of returns and not an autonomous trading executor.

## Capability Evolution

The existing foundation remains authoritative:

Data → Quality → Technical/Fundamental Analysis → Scoring → Entry Context → Opportunity Classification → Market Ranking → Historical Analysis → Backtesting → Automation/Reporting.

The product evolution is:

Validated Data → Market Structure → Liquidity/Flow → Regime/Breadth/Rotation → Event/Cross-Market Context → Opportunity Intelligence → Dynamic Trade Plan → Validation → Recommendation.

### Capability Status

Each capability is classified as:
- Implemented
- Partial
- Designed
- Planned
- Data Blocked
- Deferred
- Rejected

Code existence alone does not make a capability complete.

## Target Capability Matrix

| Capability | Current position | Target |
|---|---|---|
| Historical market data | M61 acquisition/acceptance in progress | Immutable, provenance-traceable datasets |
| Data quality | Foundation implemented | Point-in-time and market-aware controls |
| Trend | Implemented | Multi-timeframe interpretation |
| Support/resistance | Structural MVP | Zones, strength, retests and reactions |
| Momentum | MVP | Multi-horizon, regime-aware evidence |
| Volume | MVP | Liquidity, turnover and abnormal participation |
| Technical/Fundamental scoring | MVP | Validated versioned models |
| Entry context/quality | MVP | Dynamic entry/exit/re-entry context |
| Opportunity classification | MVP | Multi-layer opportunity intelligence |
| Market ranking | MVP | Multi-factor opportunity ranking |
| Liquidity intelligence | Planned | Dedicated evidence boundary |
| Investor flow | Planned/data dependent | Participant evidence where reliable |
| Market breadth | Planned | Participation/regime evidence |
| Sector rotation | Planned | Relative strength and capital-rotation evidence |
| Market regime | Planned | Risk-on/risk-off/transition states |
| Events/corporate actions | Planned | Point-in-time event and liquidity context |
| Cross-stock context | Planned | Peer/sector/market confirmation |
| Dynamic trade plan | Planned | Entry/add/reduce/exit/re-entry/invalidation |
| Confidence/probability | Planned | Calibrated only when scientifically supported |
| Opportunity scanner | Foundation exists | Continuous market-wide discovery |
| Portfolio intelligence | Planned | Holdings-aware risk and exposure |
| US market | Architecture target | First non-EGX market adapter |
| Automated order execution | Deferred | Separate safety/product gate |

## Architecture Boundary

The system remains a modular monolith initially.

### Data & Provenance
Market data, fundamentals, events, corporate actions, data quality and dataset versioning.

### Intelligence Core
Structure, liquidity, flow, regime, breadth, sector rotation, cross-market context, opportunity engine and trade-plan engine.

### Delivery/Ops
API, dashboard, reports, alerts and automation.

### Validation
Historical datasets, backtesting, walk-forward validation and out-of-sample evaluation.

### Market Adapters
EGX, US and future markets.

The core must not depend on an EGX-specific provider format.

## Intelligence Layers

Layer 0 — Data & Identity  
Provenance, point-in-time semantics, instrument identity, corporate actions, data quality, dataset versioning.

Layer 1 — Market Structure  
Trend, support/resistance, zones, retests/reactions, volatility and momentum.

Layer 2 — Participation & Liquidity  
Volume, turnover, relative volume, abnormal participation, liquidity concentration and participant flow where available.

Layer 3 — Market Context  
Breadth, market regime, sector rotation, peer/cross-stock context, events and justified cross-market context.

Layer 4 — Opportunity Intelligence  
Confluence, pattern/state detection, opportunity ranking, scanner and strategy eligibility.

Layer 5 — Decision & Trade Plan  
Entry, add, reduce, exit, invalidation, re-entry, risk/reward and recommendation state.

Layer 6 — Validation & Portfolio  
Backtesting, costs/slippage, lifecycle simulation, walk-forward, out-of-sample, robustness, portfolio exposure/risk and performance monitoring.

## Decision Lifecycle

The product uses an explicit decision lifecycle:

**Analytical State → Opportunity → Strategy Eligibility → Trade Plan → Recommendation → Human Action**

Analytical state describes evidence. Opportunity detection identifies a potentially actionable state. Strategy eligibility determines whether a versioned strategy is allowed to act. The trade plan defines the strategy-specific action boundaries. Recommendation is the auditable decision-support output. Human action is outside the recommendation engine and, if automated execution is ever introduced, requires a separate safety/product gate.

No stage may silently fabricate missing upstream evidence. Historical decision records preserve the decision-time evidence snapshot rather than being rewritten by later observations.

## Dynamic Trade Plan

The target behavior is conceptually:

Instrument → State → Dynamic Entry Zone → Invalidation → Dynamic Target/Reduce Zone → Dynamic Re-entry Zone → Strategy Risk/Reward → Evidence.

Example price ranges such as 331–335 or 355–359 are behavioral examples only. They must never become hard-coded EGAL rules.

## Liquidity Intelligence

The capability should eventually cover traded volume, turnover/value traded, relative volume, abnormal participation, liquidity concentration, liquidity expansion/contraction, price-volume confirmation, accumulation/distribution evidence and liquidity around structural levels.

Order-book data is optional and cannot be a hard dependency.

## Investor Flow

Where trustworthy point-in-time data exists, model foreign, local institutional and retail participation, net buying/selling and participation changes.

When reliable classification is unavailable, the system must not fabricate it. Missing flow data reduces evidence availability.

## Market Regime and Breadth

Evaluate index trend, breadth, volatility, liquidity, sector participation and leadership concentration.

Regime is contextual evidence. It does not force BUY/SELL without an explicit strategy rule.

## Sector Rotation and Cross-Stock Context

Evaluate sector relative strength, participation, liquidity changes, leadership, weakening/rotation states and peer confirmation so an instrument is not analyzed in isolation.

## Events and Corporate Actions

Treat IPOs, subscriptions, earnings, dividends, splits, rights, capital raises, suspensions and material announcements as point-in-time contextual evidence.

Temporal proximity is not causal proof.

## Opportunity Intelligence Evolution

1. Current MVP: Stock Quality + Entry Quality.
2. Confluence: structure + trend + momentum + liquidity + fundamentals + market/sector context.
3. Dynamic patterns: accumulation, breakout, pullback, reversal, exhaustion, distribution, failed breakout and re-entry.
4. Strategy-specific trade plans: entry, add, reduce, exit, invalidation, re-entry and risk/reward.

Each strategy owns its rules and version.

## Recommendation Contract

Target states may include BUY, ACCUMULATE, HOLD, WATCH, REDUCE, SELL, EXIT and RE-ENTRY WATCH.

A recommendation must carry strategy version, timestamp, evidence snapshot, market/instrument context, price context, invalidation, confidence/calibration metadata, explanation and data-quality state.

A recommendation without traceable evidence is incomplete.

The Recommendation Engine is not authoritative until the thresholds defined in DEC-133 are satisfied.

## AI Boundary

AI is a replaceable capability, not the source of market truth.

Deterministic market semantics, strategy rules, validation and evidence lineage remain in the core.

AI may assist with explanation, event/news extraction, research, hypothesis generation and analyst interaction. Any AI-derived signal used in production requires an explicit evidence and validation gate.

## Validation Evolution

M61 establishes the initial leakage-safe historical boundary.

The longer-term progression is:

Outcome Evaluation → Trade Simulation → Costs/Slippage → Position Lifecycle → Portfolio Simulation → Walk-Forward → Out-of-Sample → Robustness/Sensitivity → Strategy Acceptance.

A strong result on one historical sample is insufficient.

## Market-Agnostic Expansion

Target architecture:

Core Intelligence → Market Adapter → market-specific semantics → provider adapters.

EGX is the first implementation/validation market. US is the first expansion only after core contracts are stable.

## Planned MI Sequence

M61 remains current. After DEC-133 acceptance, MI-01 may perform architecture/contract work during M61 within the DEC-133 boundary; downstream MI implementation remains gated and future execution begins only when the roadmap authorizes it.


MI-01 — Market Intelligence Architecture & Contract Gate  
MI-02 — Dynamic Structure  
MI-03 — Liquidity Intelligence  
MI-04 — Market Breadth & Regime  
MI-05 — Sector Rotation & Cross-Stock Context  
MI-06 — Participant/Investor Flow  
MI-07 — Event & Corporate-Action Context  
MI-08 — Opportunity Intelligence v2  
MI-09 — Dynamic Trade Plan  
MI-10 — Decision Validation  
MI-11 — Opportunity Scanner & Alerts  
MI-12 — Portfolio Intelligence  
MI-13 — US Market Adapter  
MI-14 — Multi-Market Expansion

Each milestone requires its own Design Gate before implementation.

## Governance

- ROADMAP.md is the only execution roadmap.
- The active execution target is always the single current milestone declared in ROADMAP.md.
- This extension is a product/capability target, not an execution queue.
- Future MI sequence entries are planning targets only until their individual Design Gates are accepted.
- Decision IDs are globally unique and are never reused.
- Architecture-only MI-01 work is permitted during M61 only after DEC-133 acceptance and only within the boundary defined by DEC-133.
- This file is the durable Market Intelligence capability extension.
- Existing accepted decisions remain authoritative.
- New capabilities must identify what already exists before adding code.
- Conversation history is not project authority.
- GitHub is the project source of truth.
