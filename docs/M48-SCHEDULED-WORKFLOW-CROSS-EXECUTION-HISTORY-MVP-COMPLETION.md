# M48 — Scheduled Workflow Cross-Execution History MVP Completion

**Milestone:** M48  
**Design:** DEC-110  
**Implementation PR:** #118  
**Status:** Complete  
**Date:** 2026-09-20

## Outcome

M48 extends the durable scheduled-workflow lifecycle-history read boundary from one execution to a bounded cross-execution query.

The capability is read-only and preserves the existing ownership boundary.

## Delivered

- dedicated `GetScheduledWorkflowHistory` application capability;
- ownership-scoped cross-execution SQLite querying;
- reuse of typed `from_state` / `to_state` filters;
- UTC `occurred_from` / `occurred_to` filtering;
- deterministic newest-first ordering by `occurred_at DESC, execution_id DESC, sequence DESC`;
- bounded default page size 50 and maximum 100;
- opaque composite continuation cursors bound to the effective query shape;
- API endpoint `GET /api/v1/workflows/history`;
- restart-consistent reads from durable lifecycle history;
- representative SQLite query-plan evidence;
- application, SQLite, and API test coverage;
- preservation of the existing single-execution history contract.

## Boundary

```
HTTP
  ↓
GetScheduledWorkflowHistory
  ↓
ScheduledWorkflowExecutionStore
  ↓
SQLite lifecycle history
```

The capability does not mutate workflow state or history, replay events, change retention, introduce new authorization semantics, or add a dashboard-wide history surface.

## Validation

PR #118 was merged into `main` at merge commit:

```
ef387e2570d01653f4d231aea4527a18d3ded80c
```

Implementation head:

```
babd5935c76a01752e8fb2d32536eb7d42c55769
```

GitHub Actions Run #1959 completed successfully for the implementation head before merge.

The merge also incorporated the current foundational documentation state without changing the M48 implementation code.

## Deferred

- dashboard-wide cross-execution history presentation;
- free-text reason search;
- aggregation/analytics;
- retention/deletion;
- event replay;
- arbitrary client-controlled ordering;
- distributed search infrastructure;
- new authentication mechanisms;
- mandatory secondary indexing without performance evidence.

## Completion Decision

M48 is complete for the accepted DEC-110 MVP scope.

Any new workflow-history capability beyond this boundary requires a new explicit design gate.
