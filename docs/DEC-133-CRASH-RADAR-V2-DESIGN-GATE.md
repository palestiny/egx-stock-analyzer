# DEC-133 — EGX Crash Radar v2 Design Gate

**Status:** Path C approved; M61 paused by owner request (2026-10-28); remaining Crash Radar policy decisions pending  
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
