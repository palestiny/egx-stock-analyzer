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

# Product-Level Roadmap Extension

The project uses **one execution roadmap**. Product capabilities that expand beyond the current milestone are documented as extensions rather than separate roadmaps.

**Market Intelligence Extension:** `docs/extensions/MARKET_INTELLIGENCE.md`

**Architecture Review Gate:** `docs/DEC-131-MARKET-INTELLIGENCE-ARCHITECTURE-REVIEW-GATE.md`

The Market Intelligence extension defines the durable product target: evolve the current EGX analytical foundation into a market-agnostic Market Intelligence & Decision Support Platform covering structure, liquidity, participation, market regime, breadth, sector rotation, events, cross-stock context, opportunity intelligence, dynamic trade plans, validation, portfolio intelligence and multi-market adapters.

The extension is currently **Proposed** and does not authorize implementation. DEC-131 must be accepted before MI implementation begins.

The reviewed execution order after M61 is:

`MI-01 Architecture → MI-02 Dynamic Structure → MI-03 Liquidity → MI-04 Breadth & Regime → MI-05 Sector/Cross-Stock → MI-06 Investor Flow → MI-07 Events/Corporate Actions → MI-08 Opportunity Intelligence → MI-09 Dynamic Trade Plan → MI-10 Decision Validation → MI-11 Scanner/Alerts → MI-12 Portfolio Intelligence → MI-13 US Adapter → MI-14 Multi-Market`

Existing accepted capabilities are not duplicated. Each MI Design Gate must trace the existing decision/document/implementation before introducing a new boundary.

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

UNDERSTAND
→ MAP
→ DESIGN
→ TRADE-OFFS
→ DECIDE
→ DOCUMENT
→ TDD RED
→ GREEN
→ REVIEW / REFACTOR
→ GIT COMMIT
→ GIT PUSH
→ VERIFY
→ NEXT DESIGN GATE

No feature implementation starts before its design gate is accepted when the feature changes architecture, persistence, ownership, lifecycle, or other significant system behavior.

---

# Current Architecture Direction

The project remains a modular monolith with clear boundaries:

API / Dashboard
→ Application Use Cases
→ Domain
→ Infrastructure
→ External Providers / Persistence

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

Completed milestones are historical records, not active work queues.

The active roadmap intentionally contains one current milestone only.

## M58 — Automatic Analysis Retention

**Status:** 🟢 Complete — Implementation Merged and CI Validated

The M58 automatic-retention policy is accepted and implemented. Automatic retention is age-based, starts from logical deletion time, uses a 30-day preservation duration, covers deleted runs/correlated lifecycle data and runless deleted snapshots, is system/operator-owned, bounded, auditable, disabled by default, and fails safe on invalid configuration.

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

The active M61 execution step is **real historical dataset acquisition and validation**.

Use `docs/M61-HISTORICAL-DATASET-ACQUISITION-STATUS.md` as the operational checkpoint. No Strategy v0 performance conclusion is valid until an immutable dataset version passes the DEC-130 acceptance checklist.
