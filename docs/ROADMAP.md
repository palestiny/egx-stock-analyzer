# EGX Stock Analyzer — Roadmap

**Project:** EGX Stock Analyzer  
**Status:** Active  
**Authority:** This document tracks the current execution target. Historical milestone details are preserved by Git history and the decision log, but are intentionally not repeated here as active roadmap work.

---

# Current Position

## M61 — Backtesting & Strategy Validation Design Gate

**Status:** 🟡 In Progress — Historical Dataset Acquisition Boundary Accepted; Real Historical Evaluation Pending

DEC-126 is accepted. DEC-127 is accepted and implemented. DEC-128 and DEC-129 are accepted and implemented. DEC-130 is now accepted: real historical evidence acquisition must use immutable, provenance-traceable dataset versions with explicit point-in-time, corporate-action, missing-data, symbol-mapping, and survivorship controls.

Design gates:
- `docs/DEC-126-M61-BACKTESTING-DESIGN-GATE.md`
- `docs/DEC-127-M61-HISTORICAL-INPUT-DESIGN-GATE.md`
- `docs/DEC-128-M61-VERSIONED-HISTORICAL-DATASET-DESIGN-GATE.md`

The dataset contract covers daily market observations, point-in-time financial snapshots, immutable dataset/version identity, schema/provenance metadata, and integrity verification. Large historical artifacts remain outside Git. The physical artifact format is intentionally deferred to the implementation design.

Remaining M61 work: acquire and preserve the bounded real historical cohort, validate source provenance and coverage, integrate the accepted dataset version with the production analysis assembler, verify the existing data-quality boundary, execute Strategy v0 against real historical coverage, review aggregate/trade-level results, and complete final leakage/reproducibility validation.

---

# Future Product Direction

The future Opportunity & Market Intelligence sequence is documented separately so it does not accidentally become an active implementation queue:

**`docs/OPPORTUNITY-MARKET-INTELLIGENCE-ROADMAP.md`**

The sequence is:

```
M61 Validation
   ↓
M62 Opportunity Engine
   ↓
M63 Market Scanner
   ↓
M64 Pattern Engine
   ↓
M65 Chart Intelligence
   ↓
M66 Alerts & Monitoring
   ↓
M67 Market Intelligence / Crash Radar
   ↓
M68 Opportunity Scoring
   ↓
M69 Outcome Intelligence
   ↓
M70 Telegram / AI Assistant
```

Only one milestone is active at a time. Therefore **M61 remains the only active milestone** until its acceptance gate is closed.

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

```
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

```
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

The active M61 execution step is **real historical dataset acquisition and validation**.

Use `docs/M61-HISTORICAL-DATASET-ACQUISITION-STATUS.md` as the operational checkpoint. No Strategy v0 performance conclusion is valid until an immutable dataset version passes the DEC-130 acceptance checklist.
