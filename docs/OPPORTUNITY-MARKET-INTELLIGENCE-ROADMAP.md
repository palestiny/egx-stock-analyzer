# EGX Stock Analyzer — Opportunity & Market Intelligence Roadmap

**Status:** Future execution plan — not the active milestone  
**Current active milestone:** M61 — Backtesting & Strategy Validation  
**Authority:** This document defines the approved future direction. It does not override `docs/ROADMAP.md`, `docs/CURRENT_STATE.md`, or an accepted design gate.

---

## 1. Product Direction

The project evolves in controlled stages from an analysis system into a market-wide opportunity and market-intelligence system.

The intended product flow is:

```
EGX Market Data
      ↓
Market Scanner
      ↓
Technical / Fundamental Evidence
      ↓
Opportunity Engine
      ↓
Entry / Invalidation / Targets
      ↓
Monitoring / Outcome Tracking
      ↓
Dashboard / Charts / Alerts / Telegram / AI
```

The system must remain evidence-first. A detected setup is not automatically a validated strategy, and a model score is not a claim of future return.

---

## 2. Execution Order

### M61 — Backtesting & Strategy Validation
**Current and active.**

Objective:
- acquire real historical evidence;
- validate provenance, coverage, corporate-action semantics, missing/suspension periods, and point-in-time financial availability;
- freeze an immutable dataset version;
- execute Strategy v0;
- review trade-level and aggregate results;
- verify reproducibility;
- close the milestone only when the evidence gate passes.

**Current blocker:** real, legally retainable historical evidence for the bounded ten-symbol cohort.

No later opportunity/scanner milestone may be used to manufacture evidence for M61.

---

### M62 — Opportunity Engine
**Activation condition:** M61 closed.

Transform existing analysis outputs into explicit opportunity objects.

Each opportunity should have, as applicable:

- symbol;
- direction;
- setup type;
- evidence;
- trend/context;
- entry zone;
- maximum acceptable entry;
- confirmation condition;
- invalidation;
- stop;
- target 1/2/3;
- risk/reward;
- confidence/evidence score;
- creation time;
- expiry;
- lifecycle status.

Initial lifecycle:

```
DETECTED
  ↓
WATCHING
  ↓
ACTIVATED
  ↓
TARGET_1
  ↓
TARGET_2
  ↓
TARGET_3
  ↓
COMPLETED
```

Alternative terminal states:

```
INVALIDATED
FAILED
EXPIRED
```

**Design requirement:** opportunity semantics must be separated from presentation and notification delivery.

---

### M63 — Market Scanner
**Activation condition:** M62 design gate accepted and implemented.

Expand from single-symbol analysis to bounded market-wide scanning.

Candidate detection should cover evidence already supported by the domain plus explicitly designed new setups, including:

- trend continuation/reversal;
- breakouts/breakdowns;
- retests;
- support/resistance reactions;
- momentum changes;
- volume expansion;
- divergences;
- volatility changes;
- new highs/lows;
- liquidity-aware conditions.

The scanner must be bounded, observable, restart-safe, and independent of the dashboard.

---

### M64 — Pattern Engine
**Activation condition:** scanner boundary is stable.

Add explicit, testable pattern detectors.

Initial classical patterns:

- double top/bottom;
- head and shoulders / inverse;
- triangles;
- flags/pennants;
- channels;
- wedges;
- cup and handle;
- breakout/retest structures.

Advanced families such as harmonic patterns, Fibonacci structures, SMC, Elliott, or Gann remain separate candidates until each has a precise definition, implementation boundary, and validation plan.

**Rule:** no pattern is included merely because another product advertises it.

Every detector needs:
- definition;
- detection rules;
- confidence/evidence semantics;
- invalidation;
- deterministic tests;
- historical validation plan.

---

### M65 — Chart Intelligence
**Activation condition:** M62–M64 contracts are stable.

Provide explainable visual evidence:

```
Candles
+ Trend
+ Support/Resistance
+ Pattern
+ Entry Zone
+ Invalidation/Stop
+ Targets
+ Volume
+ Evidence
```

The chart is a projection of analytical state, not a second analytical engine.

---

### M66 — Alert & Monitoring Engine
**Activation condition:** opportunity lifecycle is production-stable.

Monitor opportunity state transitions and market events.

Potential events:

- new opportunity;
- entry approaching;
- confirmation;
- activation;
- target reached;
- stop/invalidation;
- expiry;
- breakout/retest;
- unusual volume;
- market stress.

Delivery channels are separate from detection semantics.

---

### M67 — Market Intelligence / Crash Radar
**Activation condition:** market scanner and outcome tracking provide sufficient evidence.

Add market-level context:

- market regime;
- breadth;
- sector strength/weakness;
- sector rotation;
- volatility regime;
- liquidity context;
- leaders/laggards;
- market stress score;
- crash/stress radar.

These are analytical measurements, not deterministic predictions.

---

### M68 — Opportunity Scoring / Selection
**Activation condition:** sufficient historical outcomes exist.

Combine evidence into a transparent model score.

Candidate evidence families:

- trend;
- structure;
- momentum;
- volume;
- technical confirmation;
- market/sector context;
- risk/reward.

Weights must be empirically evaluated rather than assumed to be optimal.

---

### M69 — Outcome Intelligence
**Activation condition:** opportunities have a durable lifecycle.

Record what happened after each detected opportunity:

- maximum favorable excursion;
- maximum adverse excursion;
- target reached;
- invalidation/stop;
- time to event;
- realized outcome under defined simulation rules.

Use this data to measure setup behavior and calibrate the system.

No outcome metric should be presented without its population, period, setup definition, and evaluation rules.

---

### M70 — Telegram / AI Assistant
**Activation condition:** opportunity and outcome semantics are stable.

Expose the system through conversational interfaces.

Example request:

```
"Show current EGX opportunities"
```

The assistant should retrieve structured opportunity/evidence state rather than inventing signals.

AI remains a presentation/query layer and does not become the authority for analytical or architectural decisions.

---

## 3. Cross-Milestone Rules

1. **M61 remains the gatekeeper for strategy claims.**
2. No live scanner is treated as proof of profitability.
3. No signal is described as historically successful without measured evidence.
4. Detection, scoring, monitoring, notification, and presentation remain separate concerns.
5. Every major architectural/persistence/lifecycle boundary requires a design gate.
6. Historical datasets must preserve provenance and permitted-use boundaries.
7. New advanced indicators/pattern families enter through explicit backlog/design work, not opportunistic implementation.
8. Backtesting and outcome measurement must prevent look-ahead and survivorship leakage.
9. The dashboard must not contain independent business/analytical rules.
10. The repository remains the source of truth; conversation statements never override GitHub state.

---

## 4. Definition of Done

A milestone is complete only when:

```
UNDERSTAND
→ MAP
→ DESIGN
→ TRADE-OFFS
→ DECIDE
→ DOCUMENT
→ TDD RED
→ GREEN
→ REVIEW / REFACTOR
→ COMMIT
→ PUSH
→ CI / VERIFICATION
→ ACCEPTANCE GATE
```

For analytical milestones, acceptance also requires explicit evidence of:
- input/data validity;
- deterministic behavior where applicable;
- leakage controls;
- outcome measurement;
- reproducibility;
- known limitations.

---

## 5. Explicit Non-Goals of This Roadmap

This roadmap does not authorize:

- automatic trading;
- unvalidated profit guarantees;
- blind copying of competitor features;
- arbitrary addition of indicators;
- silent changes to M61 semantics;
- bypassing data-provider licensing;
- treating AI-generated explanations as market evidence.

---

## 6. Activation Rule

Only one milestone is active at a time.

Therefore:

**Current:** M61

**Next after M61 acceptance:** M62

M62 must receive its own design gate before implementation. M63+ remain planned future milestones until their predecessors and gates are complete.
