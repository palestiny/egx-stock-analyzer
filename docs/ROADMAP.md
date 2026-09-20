# EGX Stock Analyzer — Roadmap

**Project:** EGX Stock Analyzer  
**Status:** Active  
**Authority:** This document tracks the current execution target. Historical milestone details are preserved by Git history and the decision log, but are intentionally not repeated here as active roadmap work.

---

# Current Position

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

## M57 — Physical Purge

**Status:** 🟡 Design Accepted — implementation authorized

M57 provides a privileged, synchronous physical-purge capability for logically deleted analysis lifecycle data. It uses explicit selection or deterministic eligibility, a default batch limit of 100 lifecycle units, stable-ID ordering, one SQLite transaction per lifecycle unit, fail-stop semantics, mandatory management audit, and dry-run support. Automatic retention remains disabled.

Current design gate: `docs/DEC-120-M57-PHYSICAL-PURGE-DESIGN-GATE.md`.

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

**M56 complete → open and accept the next design gate → implement only within that accepted boundary.**
