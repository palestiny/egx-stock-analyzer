# Market Intelligence Product Roadmap

**Project:** EGX Stock Analyzer  
**Status:** Proposed product/architecture roadmap  
**Branch:** architecture/market-intelligence-roadmap

## Purpose

Define the durable path from the current M61 analytical foundation to a market-agnostic Market Intelligence & Decision Support Platform. This document is the product-level target; individual capabilities still require their own Design Gates before implementation.

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

## Relationship to the Existing Roadmap

The existing foundation remains valid:

Data → Quality → Technical/Fundamental Analysis → Scoring → Entry Context → Opportunity Classification → Market Ranking → Historical Analysis → Backtesting → Automation/Reporting.

This roadmap adds the missing product-level intelligence path:

Validated Data → Market Structure → Liquidity/Flow → Regime/Breadth/Rotation → Event/Cross-Market Context → Opportunity Intelligence → Dynamic Trade Plan → Validation → Recommendation.

M61 remains the current execution milestone.

## Capability Status Model

Every capability must be marked as Implemented, Partial, Designed, Planned, Data Blocked, Deferred or Rejected. A capability is not complete merely because code exists; its contract, tests, documentation and validation must satisfy its Design Gate.

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
| Investor flow | Planned/data dependent | Institutional/foreign/retail evidence where reliable |
| Market breadth | Planned | Participation/regime evidence |
| Sector rotation | Planned | Relative strength and capital-rotation evidence |
| Market regime | Planned | Bull/bear/risk-on/risk-off/transition states |
| Events/IPO context | Planned | Point-in-time event and liquidity context |
| Cross-stock context | Planned | Peer/sector/market confirmation |
| Dynamic trade plan | Planned | Entry/add/reduce/exit/re-entry/invalidation |
| Confidence/probability | Planned | Calibrated, leakage-controlled confidence |
| Opportunity scanner | Foundation exists | Continuous market-wide discovery |
| Portfolio intelligence | Planned | Holdings-aware risk and exposure |
| US market | Architecture target | First non-EGX market adapter |
| Automated order execution | Deferred | Separate safety/product gate |

## Target Architecture

The system remains a modular monolith initially.

Data & Provenance:
- Market data
- Fundamentals
- Events
- Corporate actions
- Data quality
- Dataset versioning

Intelligence Core:
- Structure
- Liquidity
- Flow
- Regime
- Breadth
- Sector rotation
- Cross-market context
- Opportunity engine
- Trade-plan engine

Delivery/Ops:
- API
- Dashboard
- Reports
- Alerts
- Automation

Validation:
- Historical datasets
- Backtesting
- Walk-forward validation
- Out-of-sample evaluation

Market-specific adapters:
- EGX
- US
- future markets

The core must not depend on an EGX-specific provider format.

## Intelligence Pipeline

Raw observations
→ normalization and identity mapping
→ provenance and point-in-time controls
→ data quality
→ instrument structure
→ technical evidence
→ fundamental evidence
→ liquidity/flow evidence
→ market/sector regime
→ event/cross-market context
→ evidence composition
→ opportunity detection
→ trade plan
→ recommendation
→ validation.

Downstream layers must not silently rewrite upstream evidence.

## Dynamic Trade Plan Target

The final product should be capable of producing a result conceptually like:

Instrument: EGAL  
State: ACCUMULATE / WATCH / REDUCE / EXIT / RE-ENTRY  
Entry Zone: dynamically derived  
Invalidation: explicit structural condition  
Target/Reduce Zone: dynamically derived  
Re-entry Zone: dynamically recalculated  
Risk/Reward: strategy-derived  
Confidence: calibrated when supported  
Evidence: structure, liquidity, flow, momentum, market regime, sector regime, fundamentals and events.

The numbers 331–335 and 355–359 are examples of the desired behavior, not hard-coded EGAL rules.

## Support/Resistance Evolution

Structural levels already exist as an evidence layer.

Future evolution should be incremental:

Swing Levels → clustering/tolerance → zones → strength → retests/reactions → volume/liquidity confirmation → contextual decision levels.

A support level never becomes a BUY signal by itself.

## Liquidity Intelligence

Create a dedicated capability for:
- traded volume;
- turnover/value traded;
- relative volume;
- abnormal participation;
- liquidity concentration;
- liquidity expansion/contraction;
- price-volume confirmation;
- accumulation/distribution evidence;
- liquidity around structural levels.

Raw evidence and derived evidence must remain explainable. Order-book data is optional and cannot become a hard dependency of the core.

## Investor Flow

Where trustworthy point-in-time data exists, model foreign, local institutional and retail participation, net buying/selling and participation changes.

If a market does not expose reliable participant classification, the system must not fabricate it. Missing flow data reduces evidence availability rather than creating synthetic certainty.

## Market Regime

Eventually evaluate index trend, breadth, volatility, liquidity, sector participation and leadership concentration to classify market states such as risk-on, risk-off and transition.

Regime is contextual evidence. It must not force BUY/SELL without an explicit strategy rule.

## Sector Rotation

Detect sector relative strength, participation, liquidity changes, leadership and weakening/rotation states so that a stock is evaluated in sector context rather than isolation.

## Events and IPOs

Treat IPOs, subscriptions, capital raises, corporate actions, earnings and material announcements as point-in-time contextual evidence.

The system may test relationships between events and market behavior but must not assume causality merely from temporal proximity.

## Opportunity Intelligence Evolution

Stage 1: current MVP — Stock Quality + Entry Quality → BUY/WATCH/HOLD/AVOID.

Stage 2: confluence — combine structure, trend, momentum, volume/liquidity, fundamentals and market/sector context.

Stage 3: dynamic patterns — accumulation, breakout, pullback, reversal, exhaustion, distribution, failed breakout and re-entry.

Stage 4: strategy-specific trade plans — entry, add, reduce, exit, invalidation, re-entry and risk/reward.

Each strategy owns its own rules and version.

## Recommendation Contract

The target recommendation vocabulary may include:
BUY, ACCUMULATE, HOLD, WATCH, REDUCE, SELL, EXIT and RE-ENTRY WATCH.

Every recommendation should carry:
- strategy version;
- timestamp;
- evidence snapshot;
- market/instrument context;
- price context;
- invalidation;
- confidence/calibration metadata;
- explanation;
- data-quality state.

A recommendation without traceable evidence is incomplete.

## Confidence

Confidence must not be a decorative percentage. Before calibrated probabilities are exposed, define the target outcome, horizon, calibration dataset, leakage controls, calibration method, evaluation metrics and minimum sample requirements. Until then, prefer deterministic evidence/state labels.

## Backtesting Evolution

M61 validates the existing Strategy v0 foundation.

Future progression:
Outcome Evaluation → Trade Simulation → Costs/Slippage → Position Lifecycle → Portfolio Simulation → Walk-Forward → Out-of-Sample → Robustness/Sensitivity → Strategy Acceptance.

A strategy cannot become the production recommendation authority merely because it performs well on one historical sample.

## Market-Agnostic Expansion

Target architecture:

Core Intelligence → Market Adapter → market-specific semantics → provider adapters.

EGX is the first implementation/validation market. The US market becomes the first expansion once core contracts are stable. Market-specific semantic differences must be explicit rather than forced into an incorrect universal model.

## Roadmap After M61

M61 — Backtesting & Strategy Validation: close real historical evidence acquisition and establish the reproducible Strategy v0 baseline.

MI-01 — Market Intelligence Architecture Gate: define and accept contracts for liquidity, flow, regime, breadth, sector context, events and opportunity confluence.

MI-02 — Dynamic Structure: zones, strength, retests and reaction evidence.

MI-03 — Liquidity Intelligence.

MI-04 — Market Breadth & Regime.

MI-05 — Sector Rotation & Cross-Stock Context.

MI-06 — Participant/Investor Flow where reliable data exists.

MI-07 — Event & Liquidity Context.

MI-08 — Opportunity Intelligence v2.

MI-09 — Dynamic Trade Plan.

MI-10 — Full Strategy Backtesting and validation.

MI-11 — Opportunity Scanner & Alerts.

MI-12 — Portfolio Intelligence.

MI-13 — US Market Adapter.

MI-14 — Multi-Market Expansion.

## Design-Gate Rule

Every MI milestone must define:
1. domain meaning;
2. input/output contract;
3. ownership and non-responsibilities;
4. data requirements and point-in-time semantics;
5. deterministic and insufficient-data behavior;
6. alternatives and trade-offs;
7. validation plan;
8. acceptance criteria.

## Definition of Done

A decision feature is complete only when its Design Gate is accepted, tests define behavior, implementation passes, integration is verified, historical validation exists when applicable, documentation and roadmap status are updated, and GitHub reflects the resulting state.

## Success Definition

The product succeeds when it can answer reproducibly and explainably:

Which instruments currently present the strongest opportunities, why, where the favorable entry/exit/re-entry structure is, what market/sector/liquidity/flow context supports the decision, what invalidates it, what changed since the previous analysis, and how the exact strategy behaved historically under leakage-controlled validation.

