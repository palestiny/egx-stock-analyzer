# DEC-115 — M53 Analysis Run Outcome Completeness Design Gate

**Status:** Proposed  
**Date:** 2026-09-20  
**Milestone:** M53 — Analysis Run Outcome Completeness

## Context

M49 introduced durable AnalysisRun identity and correlation of successful stock-analysis snapshots to one logical market-wide run.

M50 exposed one run and its successful correlated snapshots through a read-only detail capability. M51 added run discovery, and M52 added the dashboard discovery surface.

The current read model intentionally exposes successful correlated snapshots, while failed or unknown symbols remain represented only by the aggregate run state and transient execution failure reasons. Those per-symbol failures are not durably associated with the AnalysisRun.

This creates a concrete observability gap:

- a user can discover a failed or partially completed run;
- the run aggregate state can show that it was not fully successful;
- but durable run detail cannot explain which requested symbols failed and why after restart.

M53 is proposed to close that read-side outcome-completeness gap without changing analytical rules, retry ownership, or provider behavior.

## Desired Outcome

Provide a durable, queryable representation of market-wide run outcomes sufficient to answer:

1. which requested symbols were processed;
2. which symbols completed successfully;
3. which symbols failed;
4. why an individual symbol failed, when a safe reason was available;
5. how the aggregate run state relates to those outcomes;
6. whether the outcome survives process restart.

The capability remains a read-side extension of the existing analysis-run model. It must not move analysis decisions into the dashboard or reconstruct failures from transient logs.

## Scope

### In Scope

- durable per-symbol analysis-run outcome semantics;
- correlation of successful and failed symbols to one AnalysisRun;
- explicit outcome status for each requested symbol;
- safe persisted failure reason semantics;
- consistency between aggregate ExecutionState and persisted symbol outcomes;
- application read model for run outcome details;
- API/dashboard exposure only after the application contract is accepted;
- restart persistence tests;
- compatibility with existing successful snapshot correlation.

### Explicitly Out of Scope

- changing technical/fundamental analysis;
- changing opportunity classification;
- changing retry policy;
- provider failover;
- automatic reruns;
- workflow recovery;
- notification behavior;
- ranking;
- trading decisions;
- per-user AnalysisRun ownership;
- real-time streaming;
- distributed execution;
- arbitrary log storage;
- exposing raw exception traces or secrets.

## Problem Boundary

```
Market-Wide Execution
        ↓
    AnalysisRun
        ↓
 Per-Symbol Outcome
   ↙             ↘
Success        Failure
   ↓              ↓
Snapshot      Safe Failure Reason
        ↓
Durable AnalysisRunStore
        ↓
Run Outcome Read Capability
```

The existing successful AnalysisResultStore snapshot path remains authoritative for analytical results. M53 adds outcome metadata; it does not duplicate StockAnalysisResult.

## Alternatives

### A — Reconstruct Failed Symbols from Aggregate Execution State

**Advantages**
- no new persistence model;
- minimal implementation.

**Trade-offs**
- aggregate state cannot identify failed symbols after restart;
- failure reasons are transient;
- impossible to distinguish an unrequested symbol from a requested-but-failed symbol.

**Assessment:** Not sufficient.

### B — Persist Per-Symbol Outcomes as Part of AnalysisRun

**Advantages**
- keeps one logical run as the source of outcome correlation;
- supports partial completion and all-failed runs;
- survives restart;
- naturally supports future run-detail visibility.

**Trade-offs**
- extends the AnalysisRun persistence contract;
- requires migration/serialization decisions;
- requires explicit consistency rules between outcomes and existing snapshots.

**Assessment:** Preferred candidate.

### C — Persist Raw Execution/Exception Logs and Reconstruct Outcomes

**Advantages**
- broad diagnostic information.

**Trade-offs**
- couples domain/application state to logging;
- creates retention/privacy/security concerns;
- makes read semantics dependent on log parsing;
- risks exposing implementation details.

**Assessment:** Not selected.

### D — Add a Separate AnalysisRunOutcomeStore

**Advantages**
- isolates outcome persistence from the existing AnalysisRun model.

**Trade-offs**
- introduces a second source of truth for one run's lifecycle;
- requires cross-store consistency;
- complicates atomicity and restart semantics.

**Assessment:** Deferred unless evidence shows the AnalysisRun aggregate cannot own the outcome metadata.

## Open Questions

These must be resolved before implementation:

1. Outcome identity: normalized stock symbol, Stock UUID, or both?
2. Outcome states: minimal SUCCESS/FAILED, or REQUESTED/RUNNING/SUCCESS/FAILED?
3. Failure reason: what safe, bounded representation should be persisted?
4. Atomicity: should the run record and per-symbol outcomes be persisted atomically in one durable operation?
5. Successful snapshots: should a successful outcome require an existing correlated snapshot?
6. Duplicate protection: should one symbol be allowed only once per AnalysisRun?
7. Read surface: application read semantics first, or API/dashboard in the same milestone?
8. Legacy runs: how should runs created before M53 be represented without outcome data?
9. Retention/history: should outcomes follow existing AnalysisRun retention/history?
10. Error redaction: which exception details are safe to persist without secrets or stack traces?

## Proposed Invariants

1. One requested normalized symbol has at most one persisted outcome within an AnalysisRun.
2. An outcome is correlated to exactly one AnalysisRun.
3. Successful analytical snapshots remain stored through the existing snapshot boundary.
4. A successful symbol outcome does not imply analytical success beyond the existing RunStockAnalysis completion contract.
5. A failed symbol outcome does not erase successful symbols from the same run.
6. Aggregate state is derived consistently from the complete requested-symbol outcome set.
7. Failure reasons are bounded and safe; raw traces are not persisted.
8. Persistence survives process restart.
9. Existing M50/M51/M52 read contracts remain backward-compatible.
10. React code does not calculate aggregate outcome semantics.
11. No retry policy is duplicated in M53.
12. No provider-specific error semantics leak into the domain model.

## TDD Acceptance Shape

- completed runs persist successful symbol outcomes;
- partially completed runs persist both successful and failed symbols;
- all-failed runs persist all failed symbols;
- unknown symbols receive durable failed outcomes;
- failure reasons survive restart in their accepted safe form;
- successful snapshots remain correlated to the same AnalysisRun;
- duplicate symbols cannot create duplicate outcomes;
- aggregate state and persisted outcomes cannot silently disagree;
- legacy runs without outcome records remain readable;
- malformed/corrupt outcome data fails explicitly rather than being silently invented;
- the read capability returns deterministic symbol ordering;
- existing M50 run detail and M51 run discovery behavior remain unchanged.

## Design Gate Decision

**Status: Proposed — implementation is not authorized by this document yet.**

The next controlled step is to resolve the open questions and record the accepted contract before changing durable persistence or adding new read/API/dashboard behavior.
