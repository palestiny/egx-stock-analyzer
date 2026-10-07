# DEC-133 — Market Intelligence Product Architecture Review Gate

**Status:** Proposed — Owner Approval Required  
**Date:** 2026-10-07  
**Scope:** Product roadmap architecture and execution governance after M61

## 1. Context

The project is currently executing M61 — Backtesting & Strategy Validation. A product-level Market Intelligence roadmap was added to describe the long-term evolution from the current EGX Stock Analyzer into a market-agnostic Market Intelligence & Decision Support Platform.

This gate reviews that extension against the existing roadmap and establishes the boundaries required before implementation.

## 2. Decision Under Review

The proposed governance is:

- docs/ROADMAP.md = single execution roadmap and current milestone authority.
- docs/extensions/MARKET_INTELLIGENCE.md = durable product/capability extension.
- DEC-133 = acceptance boundary for this architecture extension.
- DECISION_LOG.md = durable decisions and rationale.

The extension does not replace ROADMAP.md. New features do not create new roadmaps. M61 remains the active execution milestone until its own acceptance criteria are complete. DEC-133 acceptance does not authorize downstream feature implementation.

## 3. Review Result — Missing Features

The product roadmap covers the major desired capabilities. The review makes these additional boundaries explicit:

1. Data availability matrix: every capability declares required fields, minimum history, freshness, update frequency, point-in-time requirements, and market/provider availability.
2. Instrument identity and corporate-action semantics: symbol mapping, listing identity, delisting, splits, dividends, rights, suspensions and other corporate actions must be explicit market-adapter concerns.
3. Feature/evidence lineage: derived evidence must be traceable to source observations, calculation version and evaluation timestamp.
4. Strategy registry/versioning: every executable strategy has an explicit identity and version; material rule changes create a new version.
5. Decision lifecycle: recommendations are evidence snapshots at a decision time, not mutable historical labels.
6. Monitoring and drift: production intelligence must eventually detect data-quality drift, feature drift, provider degradation and strategy degradation.
7. Human override/audit boundary: future manual overrides must be explicit, timestamped and distinguishable from system-generated recommendations.

These are architecture boundaries, not immediate implementation tasks.

## 4. Revised Capability Layers

Layer 0 — Data & Identity:
provenance, point-in-time semantics, instrument identity, corporate actions, data quality, dataset versioning.

Layer 1 — Market Structure:
trend, support/resistance, zones, retests/reactions, volatility, momentum.

Layer 2 — Participation & Liquidity:
volume, turnover, relative volume, abnormal participation, liquidity concentration, investor flow where available.

Layer 3 — Market Context:
breadth, market regime, sector rotation, peer/cross-stock context, events, cross-market context where justified.

Layer 4 — Opportunity Intelligence:
confluence, pattern/state detection, opportunity ranking, scanner, strategy eligibility.

Layer 5 — Decision & Trade Plan:
entry, add, reduce, exit, invalidation, re-entry, risk/reward, recommendation state.

Layer 6 — Validation & Portfolio:
backtesting, costs/slippage, lifecycle simulation, walk-forward, out-of-sample, robustness, portfolio exposure/risk, performance monitoring.

This ordering is preferable to treating liquidity, flow, regime and opportunity detection as isolated vertical features because downstream decisions depend on upstream evidence contracts.

## 5. Revised MI Milestone Order

The original MI-01 → MI-14 ordering is adjusted:

### M61 — Backtesting & Strategy Validation
Must remain first and active. M61 establishes the historical evidence boundary needed to judge future decision intelligence.

### MI-01 — Market Intelligence Architecture Gate
Lock cross-cutting contracts for evidence lineage, data availability, instrument identity, point-in-time semantics, strategy versioning, recommendation lifecycle, insufficient-data behavior and market adapters.

### MI-02 — Dynamic Structure
Evolve structural levels into zones, strength, retests and reactions.

### MI-03 — Liquidity Intelligence
Add turnover, relative/abnormal volume, liquidity behavior and price-volume confirmation.

### MI-04 — Market Breadth & Regime
Build market-level context before interpreting individual opportunities as isolated signals.

### MI-05 — Sector Rotation & Cross-Stock Context
Add sector and peer relationships.

### MI-06 — Participant/Investor Flow
Add foreign/institutional/retail participation only where trustworthy data exists.

### MI-07 — Event & Corporate-Action Context
Broaden the event boundary beyond IPOs to earnings, corporate actions, capital raises, suspensions and material announcements.

### MI-08 — Opportunity Intelligence v2
Combine upstream evidence into confluence, opportunity states, ranking and dynamic pattern detection.

### MI-09 — Dynamic Trade Plan
Convert opportunity state into strategy-versioned entry/add/reduce/exit/invalidation/re-entry plans.

### MI-10 — Decision Validation
Expand M61 into costs/slippage, position lifecycle, walk-forward, out-of-sample and robustness/sensitivity acceptance.

### MI-11 — Opportunity Scanner & Alerts
Operationalize market-wide discovery after evidence and decision contracts are mature.

### MI-12 — Portfolio Intelligence
Add holdings-aware exposure, concentration, correlation/regime risk and portfolio-level opportunity/exit context.

### MI-13 — US Market Adapter
Implement the first non-EGX market adapter only after provider-neutral contracts are proven by EGX.

### MI-14 — Multi-Market Expansion
Add additional markets using the same core/adapter boundary.

## 6. What Must Be Merged With Existing Milestones

The MI roadmap must not duplicate accepted concepts.

Existing capabilities remain authoritative:
- Support/resistance → existing structural-level decisions.
- Technical evidence composition → existing technical-analysis decisions.
- Entry context/entry quality → existing entry-quality decisions.
- Opportunity classification → existing opportunity decisions.
- Market ranking → existing ranking decisions.
- Backtesting/historical input → M61 and DEC-126 through DEC-130.

The extension describes their evolution; it does not recreate them.

Before starting any MI milestone, its Design Gate must contain:
Existing capability → existing decision/doc → current implementation → identified gap → new change.

If no meaningful gap exists, the milestone must not duplicate the existing implementation.

## 7. EGX-Specific vs Market-Agnostic Boundary

Market-agnostic core:
- evidence model;
- provenance;
- point-in-time semantics;
- instrument identity abstraction;
- technical evidence;
- liquidity evidence model;
- opportunity state model;
- strategy versioning;
- trade-plan contract;
- recommendation contract;
- validation framework;
- portfolio intelligence abstractions.

EGX adapter:
- EGX symbol mappings;
- EGX trading calendar/session semantics;
- EGX market/sector taxonomy;
- EGX participant categories where available;
- EGX corporate-action semantics;
- EGX provider integrations;
- EGX-specific liquidity or auction semantics.

The US adapter must explicitly model market differences rather than force EGX assumptions into the core. No US implementation is authorized merely because it appears on the roadmap.

## 8. Data Availability Policy

Every capability must classify its data requirements as:
- Required and available
- Required but provider-dependent
- Optional enhancement
- Unavailable for this market
- Unknown / not yet verified

Rules:
1. Missing data reduces evidence availability.
2. Missing data never becomes fabricated certainty.
3. Provider data retains provenance.
4. Point-in-time constraints apply whenever historical decision validity depends on information timing.
5. Market-specific capabilities may be unavailable without blocking the platform.
6. Recommendations expose material evidence limitations.

## 9. AI Boundary

AI is not the owner of deterministic market semantics.

Deterministic core owns:
- data normalization;
- indicators;
- structural calculations;
- liquidity metrics;
- breadth/regime calculations;
- strategy rules;
- recommendation state transitions;
- backtesting;
- validation;
- evidence lineage.

AI may assist with:
- natural-language explanation;
- research summarization;
- event/news extraction;
- hypothesis generation;
- anomaly investigation;
- analyst interaction;
- question answering over stored evidence;
- optional ranking augmentation only when explicitly validated.

AI must not silently own ground-truth market data, historical truth, strategy semantics, recommendation authority, backtest results or confidence calibration.

Any AI-derived signal used in a production recommendation requires an explicit evidence contract and validation gate.


## 10A. Decision Lifecycle Boundary

The platform distinguishes six lifecycle stages that must not be collapsed into a single recommendation label:

**Analytical State → Opportunity → Strategy Eligibility → Trade Plan → Recommendation → Human Action**

- **Analytical State:** what the evidence says about the instrument/market at decision time.
- **Opportunity:** a detected setup or state with supporting evidence; it is not yet a strategy decision.
- **Strategy Eligibility:** whether a versioned strategy is permitted to act on that opportunity under its declared constraints, data-quality requirements and risk boundary.
- **Trade Plan:** the strategy-specific entry/add/reduce/exit/re-entry/invalidation and risk/reward contract.
- **Recommendation:** the auditable decision-support output produced from the eligible strategy and trade plan.
- **Human Action:** the external user decision or future separately governed execution boundary.

A recommendation is therefore not equivalent to an order, and an opportunity is not automatically a recommendation. Missing evidence or failed strategy eligibility must be able to stop the lifecycle without fabricating a downstream state.

Historical records are immutable decision-time evidence snapshots. A later market update may create a new decision; it must not mutate the earlier decision's inputs or label.

## 10. Recommendation Authority

The Recommendation Engine becomes authoritative only after:
1. strategy/version contract is explicit;
2. material inputs have provenance;
3. point-in-time leakage controls are enforced where applicable;
4. insufficient-data behavior is deterministic;
5. recommendation states are reproducible;
6. historical validation is performed on data not used to design/tune the strategy;
7. walk-forward or equivalent temporal validation passes where applicable;
8. costs/slippage assumptions are explicit;
9. robustness/sensitivity testing is acceptable;
10. recommendations include evidence, invalidation and data-quality state;
11. production monitoring exists for data and strategy degradation.

Until these conditions are met, the engine is decision-support evidence, not authoritative trading advice.

## 11. Overfitting and Look-Ahead Prevention

Non-negotiable rules:

- At decision time T, only information available at or before T may influence the decision.
- Features declare observation time and availability time where relevant.
- Historical evaluation pins dataset version and integrity hash.
- Results identify exact strategy version and configuration.
- Out-of-sample evaluation is never reused as a tuning set.
- Adaptive strategies use chronological walk-forward evaluation.
- Adjusted/unadjusted price semantics are explicit and consistent with execution assumptions.
- No forward-fill or current-value substitution where it can introduce future information.
- Historical universes preserve delisted/removed instruments where required.
- Results are reproducible from pinned data, strategy version, configuration, code/version identity and scope.

## 12. Confidence and Probability

A numeric probability is prohibited as a presentation-only confidence score.

Before calibrated probability is exposed, define:
- target event;
- prediction horizon;
- outcome definition;
- calibration dataset;
- calibration method;
- leakage controls;
- calibration metrics;
- discrimination metrics;
- minimum sample size;
- stability requirements;
- recalibration policy.

Until then use evidence/state labels such as Strong confluence, Moderate confluence, Weak evidence and Insufficient evidence.

## 13. Product-Level Definition of Done

The product is not done merely because screens or indicators exist.

Evidence:
- market data and derived evidence have provenance;
- point-in-time semantics are enforced where required;
- data-quality state is visible;
- instrument identity and corporate-action semantics are explicit.

Intelligence:
- structure, liquidity, participation, market regime and sector context work within declared data boundaries;
- opportunity detection is reproducible and explainable;
- market-wide scanning is supported.

Decision support:
- recommendations are strategy-versioned;
- entry/add/reduce/exit/re-entry and invalidation are explicit where supported;
- every recommendation carries its evidence snapshot and limitations;
- unsupported certainty is not presented.

Validation:
- deterministic historical evaluation exists;
- transaction costs/slippage are explicit;
- position lifecycle is tested;
- walk-forward/out-of-sample validation is available where applicable;
- robustness/sensitivity analysis is documented;
- results are reproducible from pinned inputs.

Operations:
- scheduled analysis is observable;
- stale/provider-failure conditions are visible;
- data and strategy degradation monitoring exists for production-critical intelligence;
- alerts are auditable.

Market portability:
- core intelligence is market-agnostic;
- EGX behavior is isolated in adapters;
- at least one additional market can be integrated without rewriting the core.

Governance:
- every major capability has an accepted Design Gate;
- implementation and tests match the accepted contract;
- roadmap status is current;
- GitHub is the source of truth;
- no parallel roadmap is required to understand current execution.

## 14. Acceptance Criteria

DEC-133 may be accepted when the owner confirms:
- single-roadmap + extension governance;
- revised MI ordering;
- capability/data boundaries;
- EGX/core separation;
- AI boundary;
- recommendation-authority threshold;
- anti-overfitting/look-ahead rules;
- product-level Definition of Done.

Until acceptance, MI implementation remains blocked except documentation work required to close this gate.

## 14A. Architecture-Only MI-01 During M61

M61 remains the active execution milestone. However, after DEC-133 acceptance, MI-01 may perform contract/design work that does not implement downstream Market Intelligence features or alter M61 acceptance semantics. This prevents cross-cutting architecture gaps from being discovered only after M61 closes. Feature implementation remains gated by the relevant MI Design Gate.

## 15. Post-Acceptance Execution

After DEC-133 acceptance:

M61
→ MI-01
→ MI-02
→ MI-03
→ MI-04
→ MI-05
→ MI-06
→ MI-07
→ MI-08
→ MI-09
→ MI-10
→ MI-11
→ MI-12
→ MI-13
→ MI-14

No MI milestone skips its own Design Gate.

The branch containing this review remains a proposal until DEC-133 is accepted and verified.
