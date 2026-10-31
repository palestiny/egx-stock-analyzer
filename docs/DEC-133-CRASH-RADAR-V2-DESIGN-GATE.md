# DEC-133 — EGX Crash Radar v2 Design Gate

**Status:** Path C and conservative Crash Radar policy baseline accepted in DEC-135 (2026-10-31); implementation and evidence verification remain open  
**Date:** 2026-10-26  
**Milestone relationship:** Candidate capability; does not replace the active M61 historical-evidence milestone.

## 1. Purpose

Evolve the existing Market Breadth & Stress Pulse into a more trustworthy market-risk dashboard that helps a user notice broad deterioration in EGX conditions. It must explain why the score changed, how complete and fresh the evidence is, and what the score cannot establish.

This is a risk-monitoring and research feature, not a crash predictor, guaranteed early-warning system, or buy/sell signal.

## 2. Verified current baseline

The authenticated endpoint `GET /api/v1/market-intelligence/breadth-stress?symbols=...` currently reads the latest saved analysis snapshot for each caller-supplied symbol. It reports requested/analyzed counts, missing symbols, coverage, trend/momentum/volume counts, bullish breadth, bearish pressure, and a 0–100 heuristic stress score.

The current score is:
- 50% downtrend share;
- 40% negative-momentum share;
- 10% negative momentum combined with above-average volume.

The existing implementation labels its data as `LATEST_SAVED_ANALYSIS_SNAPSHOT` and explicitly states it is not a trading signal. Its main limitations are that snapshots can be stale, the caller chooses the universe, the score is heuristic, and it does not independently establish market-wide completeness or validate source quotes.

## 2.1 Implementation status reconciled — 2026-10-28

PR #387 merged explainable component output and per-symbol snapshot-date evidence while preserving the existing 50/40/10 heuristic. It did not change signal ranking or make the score predictive. Treat the current endpoint as a snapshot-based diagnostic, not a validated market-wide crash probability.

The following are still open and must not be silently inferred by implementation:

- **Universe ownership:** fixed EGX30, broader EGX universe, or operator-configured universe, including treatment of suspended/newly listed symbols.
- **Freshness policy:** warning-only versus blocking stale snapshots, the threshold and clock source, and treatment of unknown snapshot dates.
- **Minimum evidence:** minimum symbol count/coverage and whether to suppress the composite score when the gate fails.
- **Persistence/retention:** whether daily score history is required, its immutable input snapshot, retention, and correction behavior.
- **Notifications:** whether stress changes trigger alerts, the threshold/hysteresis, recipient scope, frequency limits, and suppression/recovery semantics.

Until these decisions are accepted, keep the current score formula and response semantics stable, expose evidence/limitations, and do not create a new score-suppression threshold or automated alert policy.

## 3. Problem to solve

A single stress number can create false confidence if:
- the symbol universe is incomplete or changes between runs;
- saved analyses are old or use different observation dates;
- some symbols have missing or rejected price bars;
- multiple inputs measure nearly the same underlying weakness;
- the score changes without a traceable explanation;
- a heuristic score is interpreted as a statistically validated probability of a crash.

## 4. Candidate scope

### In scope for a first increment
1. **Evidence freshness:** report snapshot date/freshness per symbol where the persisted contract supports it; distinguish unknown date from current data.
2. **Universe coverage:** preserve the requested universe and show analyzed, missing, stale, and excluded counts separately.
3. **Explainability:** return component values and the exact methodology/version used, not only a composite score.
4. **Insufficient-evidence state:** suppress the composite score or label it insufficient when explicit coverage/freshness gates are not met.
5. **Historical comparison:** design a reproducible daily history for score/components only after a persistence and retention boundary is accepted.
6. **UI presentation:** show stress level, direction of change, coverage/freshness, component contribution, and limitations without presenting a trading recommendation.

### Later research candidates — not accepted for implementation yet
- EGX30/index drawdown and realized volatility;
- cross-sectional daily returns and breadth from a validated market-wide daily dataset;
- volatility expansion and downside-tail measures;
- volume/liquidity stress where source semantics are verified;
- market/sector concentration and correlation changes;
- historical threshold calibration and false-positive/false-negative analysis.

These require reliable, provenance-traceable data and must not be synthesized from unavailable inputs. M61 remains the acceptance gate for real historical strategy evidence; no calibrated predictive claim may be made without separate out-of-sample validation.

## 5. Design options

### Option A — Harden the existing snapshot heuristic
Add freshness/coverage semantics and explainable component output to the current endpoint. Keep its score formula and legacy response fields stable.

**Advantages:** smallest change, backward-compatible path, makes current limitations visible.  
**Trade-offs:** remains a saved-snapshot heuristic; does not establish true market-wide conditions.

### Option B — Build a new data-backed Crash Radar
Create a separate application capability that consumes validated daily market/index observations and computes breadth, drawdown, volatility, and stress components.

**Advantages:** clearer evidence boundary and stronger long-term foundation.  
**Trade-offs:** depends on accepted data provenance, persistence, freshness, and universe contracts; larger design and verification effort.

### Option C — Two-stage path (recommended)
First harden the existing endpoint with explicit freshness, coverage, and explainability. In parallel, keep the data-backed score as a separate future design gate that cannot claim readiness until its source/data acceptance criteria pass.

**Advantages:** improves current transparency without pretending historical data is already trustworthy; protects compatibility and separates heuristic from evidence-backed analytics.  
**Trade-offs:** two increments and temporary coexistence of the legacy and future methodology.

## 6. Recommended boundaries

- Keep calculations in the application/domain layer, not React components or API route handlers.
- Keep source acquisition and persistence behind existing provider/store contracts.
- Version the methodology and preserve the current score formula unless a separately reviewed version intentionally changes it.
- Do not call the score a probability of a crash.
- Do not silently treat missing or stale symbols as healthy.
- Do not use future data or revised data unavailable at the historical decision date in any validation.
- Expose data status, as-of date, coverage, and limitations alongside the score.
- Do not change existing opportunity rankings or trading signals as a side effect.
- Do not add automated alerts or notifications until alert thresholds, deduplication, delivery, and user controls have their own design gate.

## 7. Owner decisions required

1. **Path — DECIDED:** Option C approved by the owner on 2026-10-26. Harden the existing snapshot heuristic first, while keeping the future data-backed model behind a separate evidence gate.
2. **Universe:** fixed EGX30, a versioned broad EGX universe, or caller-supplied universe? Recommendation: support a versioned configured universe and label caller-supplied results as partial/custom.
3. **Freshness policy:** what is the maximum acceptable age of a saved daily analysis? Recommendation: propose one full EGX trading session as the initial warning boundary, then validate against the actual scheduler and data cadence before enforcing it.
4. **Minimum coverage:** what fraction of the configured universe must be present before a composite score is shown? Recommendation: make it configurable and return `insufficient_data` below the accepted threshold; do not choose a threshold without reviewing real coverage.
5. **Persistence:** should daily score history be persisted for charts/alerts? Recommendation: yes, but only after defining a bounded, versioned history and retention policy.
6. **Alerts:** should v1 only display risk, or also deliver notifications? Recommendation: display-only in the first increment.

## 8. Acceptance criteria before implementation

- Owner decisions above are recorded.
- Existing endpoint compatibility and current consumers are mapped.
- Freshness source is explicit; unknown timestamps are not guessed.
- Coverage and stale-data behavior are deterministic and tested.
- Score components reconcile exactly to the published methodology.
- Empty, partial, stale, duplicate, and invalid-data cases have explicit outcomes.
- API contract and UI states are specified before implementation.
- No crash-probability or profitability claim is made.
- Implementation has domain/application/API/frontend tests and full CI validation.
- Historical predictive evaluation, if later proposed, uses immutable provenance-traceable data and a documented out-of-sample methodology.

## 9. Current disposition

Option C is approved. The remaining decisions (universe, freshness warning/enforcement, minimum coverage, persistence/retention, and alerts) are not yet approved. Therefore this document authorizes the staged direction but does not authorize silently choosing those policy values or changing the scoring formula. The first implementation increment may add transparent evidence metadata without inventing missing timestamps or treating unknown/stale inputs as healthy. Any behavior that suppresses or changes the score based on policy thresholds must wait until those thresholds and the universe contract are accepted. M61 is paused by owner request as of 2026-10-28; its historical-data acceptance gate remains unchanged.


## 10. Status reconciliation — 2026-10-28

The owner has explicitly paused M61 and requested that non-M61 engineering/product gaps be completed first. This does not authorize a data-backed Crash Radar model or change M61 acceptance criteria. The safe first increment is explainability of the existing 50/40/10 heuristic; component explainability is merged through PR #387; per-symbol snapshot-age metadata is proposed in PR #392 and must pass CI before merge. Existing per-symbol analysis-date metadata remains evidence metadata only: it does not prove current prices, define a freshness threshold, or enforce a minimum-coverage policy.

Still open: configured universe/versioning, freshness policy, minimum coverage, score suppression behavior, persistence/retention of daily score history, and whether notifications are allowed. No new thresholds or score changes are authorized by this status refresh.


## 11. Owner policy acceptance — 2026-10-31 (DEC-135)

The owner has accepted the following policy baseline, superseding the unresolved policy questions recorded in the historical 2026-10-28 status sections above:

- The monitored universe is operator-configurable and versioned. A caller-supplied/custom universe must be identified as such; it must not be presented as a complete market-wide universe.
- Freshness is evaluated against completed EGX sessions. After one full completed session without an updated observation, affected evidence is marked stale. Unknown timestamps remain unknown and are never inferred.
- Missing, stale, or insufficient coverage is explicitly disclosed. Coverage limitations must not be represented as healthy evidence or as a complete market-wide score.
- Preserve historical observations and score inputs with provenance and correction visibility. Do not silently overwrite corrected source history.
- Crash Radar remains display-only in this baseline: no automatic alerts or notification thresholds are enabled.
- Preserve the existing 50/40/10 heuristic. DEC-135 does not authorize changing weights, introducing predictive claims, or treating the score as a crash probability or trading signal.

**Implementation remains open:** configured universe/version persistence, completed-session freshness evaluation, stale/missing coverage behavior, history/correction handling, API/UI contract tests, and end-to-end CI must be implemented and verified. The one-session freshness boundary must be evaluated using the actual EGX calendar/session completion source; do not approximate a completed session using elapsed wall-clock time. M61 remains paused.
