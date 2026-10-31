# EGX Stock Analyzer — Roadmap

**Project:** EGX Stock Analyzer  
**Status:** Active  
**Authority:** This document tracks the current execution target. Historical milestone details are preserved by Git history and the decision log, but are intentionally not repeated here as active roadmap work.

---

# Current Position

## Non-M61 engineering checkpoint — 2026-10-31 (updated after PRs #428–#433)

The latest non-M61 implementation increment merged:
- PR #418: preserve the source price-bar timestamp in analysis/signal output; current code carries it through analysis persistence into `Signal.data_timestamp` and suppresses signal creation when it is missing or timezone-naive.
- PR #428–#430: Telegram recipient atomic claims, operator reconciliation, and operator runbook.
- PR #432: bounded retries for definite Telegram failures under DEC-137.
- PR #433: align the completion register and Telegram concurrency design gate with the merged implementation.
- PR #420: add offline integrity/provenance-structure tests for the canonical EGX daily archive.
- PR #421: append the 2026-10-29 daily session (19 equities and 4 indices) and generalize the archive schema to distinguish equity EGP prices from index points.

The canonical archive currently contains 45 rows (22 EGAL seed rows plus 23 rows for 2026-10-29). Its known data-quality exceptions remain visible: MICH and FAIT OHLC inconsistencies on 2026-10-29, plus an EGAL source-revision conflict for 2026-10-28. These values are not silently repaired or overwritten.

**Verification boundary:** PR #432 post-merge main CI run #41197870758 passed all five jobs. PR #433 exact-head CI run #41198262173 passed all five jobs and was merged at `4733e9237495789ebceba9113567e42b7b6abf6d`; post-merge main CI run #41198751442 remains in progress. PR #422 main CI run #41185546490 also passed all five jobs. This validates the tested code path, not market-data accuracy, full-market coverage, database ingestion, or strategy profitability. The archive validation tests establish structural consistency only, not market-data accuracy, complete EGX coverage, application database ingestion, or strategy profitability. The Yahoo Finance adapter currently requests daily bars only; actual EGX symbol coverage, upstream timestamp/timezone semantics, freshness/delay, corrections, rate limits and reuse terms remain unverified. A completed-session freshness gate is still required before actionable output.

The previous design proposals #342, #344, and #347 are closed unmerged; they are not themselves accepted owner decisions. Their policy areas are now governed by owner-accepted DEC-135. Do not implement automatic Crash Radar alerts, commercial pricing/payment, or broker execution. Automated session report scheduling/distribution may proceed only within DEC-135 and with tested idempotency, correction, retry, and failure visibility. M61 remains paused by explicit owner request.


## M61 — Backtesting & Strategy Validation Design Gate

**Status:** ⏸ Paused by owner request on 2026-10-28 — no M61 implementation or data-acquisition work until explicitly resumed

DEC-126 is accepted. DEC-127 is accepted and implemented. DEC-128 and DEC-129 are accepted and implemented. DEC-130 is now accepted: real historical evidence acquisition must use immutable, provenance-traceable dataset versions with explicit point-in-time, corporate-action, missing-data, symbol-mapping, and survivorship controls.

Design gates:
- `docs/DEC-126-M61-BACKTESTING-DESIGN-GATE.md`
- `docs/DEC-127-M61-HISTORICAL-INPUT-DESIGN-GATE.md`
- `docs/DEC-128-M61-VERSIONED-HISTORICAL-DATASET-DESIGN-GATE.md`

The dataset contract covers daily market observations, point-in-time financial snapshots, immutable dataset/version identity, schema/provenance metadata, and integrity verification. Large historical artifacts remain outside Git. The physical artifact format is intentionally deferred to the implementation design.

### Verified implementation increments — 2026-10-20

- PR #322 merged at `24a8193199f821e0fe4906dfdfcaa603ceb1ae73`: Strategy v0 backtest results now expose profit factor, maximum drawdown on the sequential trade-equity curve, average winning/losing returns, and maximum consecutive win/loss streaks. The drawdown is **trade-sequence drawdown**, not daily or intraday portfolio drawdown.
- PR #325 merged at `1c908b0456f02dccbdc75ab9eeb5206bad30c15d`: added the authenticated `pre-breakout-momentum-volume` watchlist for positive momentum, volume ratio at least 1.5x, and a price 0–5% below resistance. It preserves the existing scanner and uses the latest saved analysis, which may be stale.
- PR #322 CI run #4068 and PR #325 CI run #4113 passed all five reported jobs before merge. This verifies software behavior, **not** market-data validity or strategy profitability. Separate post-merge CI is not claimed here.

Remaining M61 work: acquire and preserve the bounded real historical cohort, validate source provenance and coverage, integrate the accepted dataset version with the production analysis assembler, verify the existing data-quality boundary, execute Strategy v0 against real historical coverage, review aggregate/trade-level results, and complete final leakage/reproducibility validation.

---

## M60 — Production Maintenance Scheduling

**Status:** 🟢 Complete — Deployment Mapping Merged

DEC-124 was accepted and the Windows Task Scheduler deployment mapping was merged through PR #162 at `4fbf799f6262c4179946835ef4eae47cf8ecb6f1`.

The accepted mapping runs the existing M59 maintenance command daily at 03:30 local host time, ignores overlapping invocations, applies a 30-minute task ceiling, and allows up to 3 scheduler restarts at 10-minute intervals. Deployment tooling lives under `deploy/windows/` and contains no retention or physical-deletion logic.

Repository CI passed on implementation head `707b29560bdebf587c9c8fae176b01a4208cfae8` in GitHub Actions Tests Run #2709. The merge commit did not expose a separate workflow run through the available GitHub integration, so no post-merge CI run is claimed.

Windows-host execution/registration verification remains an operational deployment task because this session does not have a Windows production host. The application-side M57/M58/M59 semantics remain unchanged.

---

## Completed Milestones — Historical Reference

Completed milestones are retained below only as historical reference. They are not active work queues.

## M56 — Analysis Run & Snapshot Retention and Deletion

**Status:** 🟢 Complete — Implementation Merged

The current project boundary is the coordinated lifecycle of durable AnalysisRun records and AnalysisResultRecord historical snapshots.

Current design gate:

- `docs/DEC-118-M56-ANALYSIS-LIFECYCLE-RETENTION-DESIGN-GATE.md`

The accepted M56 lifecycle implementation is merged and verified. Physical purge and automatic retention remain out of scope.

## Completed Objective

Implemented the accepted M56 lifecycle boundary using TDD, shared SQLite transaction coordination, consistent read-side visibility, owner-aware authorization, active-run protection, idempotent logical deletion, and mandatory management-audit recording.

---

# Engineering Execution Rule

Every new milestone follows:

```text
UNDERSTAND
   ↓
MAP
   ↓
DESIGN
   ↓
TRADE-OFFS
   ↓
DECIDE
   ↓
DOCUMENT
   ↓
TDD RED
   ↓
GREEN
   ↓
REVIEW / REFACTOR
   ↓
GIT COMMIT
   ↓
GIT PUSH
   ↓
VERIFY
   ↓
NEXT DESIGN GATE
```

No feature implementation starts before its design gate is accepted when the feature changes architecture, persistence, ownership, lifecycle, or other significant system behavior.

---

# Current Architecture Direction

The project remains a modular monolith with clear boundaries:

```text
API / Dashboard
      ↓
Application Use Cases
      ↓
Domain
      ↓
Infrastructure
      ↓
External Providers / Persistence
```

Cross-cutting rules:

- analytical logic stays outside presentation and persistence;
- application capabilities own business orchestration;
- infrastructure owns provider and storage details;
- authorization remains an application boundary;
- persistence must not invent business decisions;
- destructive lifecycle operations require explicit design decisions;
- AI is not the authority for product or architectural decisions.

---

# Milestone Policy

A milestone is considered complete only when its design, tests, implementation, review/refactor, documentation, Git commit, and acceptance criteria are satisfied.

Completed milestones are **historical records**, not active work queues.

The active roadmap intentionally contains **one current milestone only**.

## M58 — Automatic Analysis Retention

**Status:** 🟢 Complete — Implementation Merged and CI Validated

The M58 automatic-retention policy is accepted and implemented. Automatic retention is age-based, starts from logical deletion time, uses a **30-day preservation duration**, covers deleted runs/correlated lifecycle data and runless deleted snapshots, is system/operator-owned, bounded, auditable, disabled by default, and fails safe on invalid configuration.

Design gate: `docs/DEC-122-M58-AUTOMATIC-RETENTION-DESIGN-GATE.md` — Accepted.

Implementation: PR #157, merged into `main` at `f2294c34a10c994545e24175c956ee8524170142`.

The implementation was validated by the successful M58 CI run #2637 on the implementation head before merge. Post-merge workflow association for the merge commit is empty in GitHub's commit-workflow query, so no separate merge-commit CI run is claimed here.

## M57 — Physical Purge

**Status:** 🟢 Complete — Implementation Merged and CI Validated

M57 provides a privileged, synchronous physical-purge capability for logically deleted analysis lifecycle data. It uses explicit selection or deterministic eligibility, a default batch limit of 100 lifecycle units, stable-ID ordering, one SQLite transaction per lifecycle unit, fail-stop semantics, mandatory management audit, and dry-run support. Automatic retention remains disabled.

Design gate: `docs/DEC-120-M57-PHYSICAL-PURGE-DESIGN-GATE.md` — Accepted.

Implementation: PR #151, merged into `main` at `3b20199581e2a6f313e3f83ca4c65780d5a9dbba`.

GitHub Actions Run #2537 completed successfully for implementation merge `3b20199581e2a6f313e3f83ca4c65780d5a9dbba`. A subsequent documentation closeout Run #2543 also completed successfully.

This prevents milestone accumulation from becoming architecture drift or a second source of truth.

---

# Source of Truth

For current project state use this order:

1. GitHub `main`
2. Open pull requests
3. This roadmap
4. `docs/CURRENT_STATE.md`
5. Current design-gate document
6. `docs/DECISION_LOG.md`
7. Git history for historical context

Old milestone names, old branches, and conversation history must not be treated as current execution state.

---

# Next

**Current priority: non-M61 engineering and product gaps. M61 is paused by explicit owner request dated 2026-10-28.** Do not resume historical-data acquisition, backtest evaluation, or performance claims until the owner explicitly resumes M61.

The next non-M61 work is limited to closing verified release gaps without inventing product policy:

1. Keep the current-state inventory aligned with the latest main commit and its completed CI results; do not mark a merge verified until its main workflow finishes successfully.
2. Resolve the owner decision gates in PR #342 (Crash Radar policy), PR #344 (opportunity/Telegram/session-report/commercial policy), and PR #347 (approved news provenance and remaining technical/news acceptance).
3. Only after source and usage rights are approved, enable a supported news provider and schedule polling.
4. Only after the exchange-session finalization policy is approved, automate final reports and distribution.
5. Only after a payment provider, plans, pricing, refunds, and entitlement rules are approved, implement live billing.

M61 remains paused by explicit owner request. When M61 resumes, use `docs/M61-HISTORICAL-DATASET-ACQUISITION-STATUS.md` as the operational checkpoint. No Strategy v0 performance conclusion is valid until an immutable dataset version passes the DEC-130 acceptance checklist.

## M61 exploratory-data checkpoint (historical; paused by owner as of 2026-10-28)

This is a historical diagnostic result, not an instruction to resume M61. The owner explicitly paused M61 on 2026-10-28; no new acquisition, backtesting, or performance claims are authorized until that pause is lifted.

The public multi-symbol diagnostic workflow ran successfully against ten EGX symbols over 2021-10-25 through 2026-10-19 with no source-fetch failures. The pre-breakout proxy did not outperform the all-session baseline on mean gross returns at 5 or 10 sessions. Preserve the run and detailed metrics in [M61 public multi-symbol results](M61-PUBLIC-MULTI-SYMBOL-RESULTS-2026-10-20.md). This is exploratory only; do not change production opportunity ranking from this sample.

The private archive has a separate 181,203-row validated CSV across 195 symbols, but the attempted private-repository workflow failed before producing a report. No results are inferred for that dataset; see [archive technical diagnostic instructions](M61-ARCHIVE-TECHNICAL-DIAGNOSTIC.md).

## Verified market-intelligence increments — 2026-10-20

The following product capabilities were merged into `main` after the M61 acquisition checkpoint was written. They do not change the active M61 acceptance boundary or establish strategy profitability:

- PR #324: breakout-evidence quality scoring; see https://github.com/palestiny/egx-stock-analyzer/pull/324.
- PR #326: market breadth and heuristic stress pulse derived from latest saved analysis snapshots; see https://github.com/palestiny/egx-stock-analyzer/pull/326.
- PR #327: per-symbol trend regime and historical risk profile (requires sufficient daily observations); see https://github.com/palestiny/egx-stock-analyzer/pull/327.
- PR #328: dashboard presentation for the regime/risk diagnostics; see https://github.com/palestiny/egx-stock-analyzer/pull/328.
- PR #329: per-opportunity regime/risk context, without silently changing existing opportunity ranking; see https://github.com/palestiny/egx-stock-analyzer/pull/329.
- PR #330: dashboard Market Breadth & Stress Pulse panel; all five CI jobs passed before merge. It shows coverage and missing symbols and explicitly labels its snapshot-based heuristic as neither live intraday data nor a crash prediction; see https://github.com/palestiny/egx-stock-analyzer/pull/330.

**M61 is paused by explicit owner request on 2026-10-28. Do not start or continue M61 data acquisition, backtest evaluation, or performance claims until the owner resumes it.**

**Temporary execution focus (outside M61):** close engineering/product gaps in existing capabilities. Work in this order: (1) verify and harden current Crash Radar / Market Breadth & Stress Pulse freshness, coverage, and explainability without changing its scoring formula; (2) finish the technical-analysis/news evidence stack already represented by merged implementation PRs and identify genuinely missing integration; (3) review and close the owner decisions in the trading-opportunity/Telegram/session-report/owner-dashboard design gate before any payment or subscription implementation; (4) complete repository quality, security, dependency, and operational documentation checks. Keep the M61 historical dataset isolated and unchanged during this pause. The public COMI/multi-symbol diagnostics in draft PR #321 are exploratory only and do not satisfy DEC-130 acceptance. Do not use them to claim a validated trading edge. The owner has no paid-data budget; any accepted source must have verifiable storage/research-use rights, point-in-time financial evidence, and an immutable manifest before Strategy v0 evaluation.


## Owner-approved non-M61 policy baseline — 2026-10-31 (DEC-135)

The owner accepted the conservative policy baseline for Crash Radar, EGXBot/Telegram opportunity lifecycle, session reports, manual subscription entitlements, official-news provenance, and stale/invalid market-data suppression. The detailed binding decision is recorded in `docs/DECISION_LOG.md` under DEC-135. This resolves policy approval only; it does not declare the related engineering work complete.

Verified repository checkpoint: PR #422 merged at `fa5d16a9b8a47e3cdcb9467d1e31ffd4ee6bed64`; main CI run #41185546490 passed all five jobs. PR #321 remains open Draft and M61 remains paused.

**Latest verified non-M61 progress — 2026-10-31:** PR #428 merged atomic Telegram recipient claims and ambiguous-outcome handling; PR #429 merged operator-only audited reconciliation; PR #430 merged the operator runbook. PR #429 main CI run #41191307763 passed all five jobs. PR #430 branch CI run #41191550843 passed all five jobs; post-merge main CI for the new main commit still requires verification.

**Next execution priority:** continue from the updated gap register. The Telegram retry policy for definite failures is the immediate owner decision gate: attempt budget, delay/backoff, and exhaustion behavior remain unapproved. In parallel, close the Cairo-session report scheduling/correction/delivery composition, Crash Radar configurable-universe/freshness/coverage implementation without changing 50/40/10, official-news source-rights/provenance verification, and entitlement enforcement across API and Telegram. Keep payment collection/pricing/refunds deferred; do not enable automatic trading or Crash Radar alerts. PRs #342/#344/#347 are historical proposals superseded by the accepted DEC-135 policy baseline, not active owner-decision gates.
