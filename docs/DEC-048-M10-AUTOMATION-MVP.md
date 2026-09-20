# DEC-048 — M10 Automation MVP

## Status
Accepted

## Purpose
Define the MVP execution and automation model for running the existing daily EGX analysis pipeline.

M10 automates the execution of existing business capabilities. It does not redefine Technical Analysis, Fundamental Analysis, Scoring, Opportunity Classification, Reporting, or Alerts.

## Scope
The MVP supports one daily market-analysis execution with:

- manual trigger
- scheduled trigger
- execution lifecycle
- stock-level partial failure handling
- limited retry for transient failures
- idempotency
- deterministic execution result

The MVP does not introduce distributed workers, queues, Celery/Kubernetes, horizontal scaling, authentication, dashboard concerns, or an advanced workflow engine.

## Decision 1 — Execution Scope

### Decision
Use **one Execution for the complete daily market analysis**.

Conceptually:

```text
Daily Market Analysis Execution
 ├── Stock result: EGAL
 ├── Stock result: IEEC
 ├── Stock result: SVCE
 └── ...
```

The business analysis logic must remain independent from this execution structure so the system can later move to a parent execution with one child execution per stock if a real scaling/orchestration need appears.

### Rationale
This keeps the MVP aligned with the business operation — "analyze the market today" — while avoiding premature orchestration complexity.

## Decision 2 — Partial Failure

### Decision
Use `COMPLETED_WITH_ERRORS` when the daily execution finishes with some successful stock analyses and some failed stock analyses.

```text
All stocks succeed
→ COMPLETED

Some succeed + some fail
→ COMPLETED_WITH_ERRORS

No useful work completes / execution cannot complete its core operation
→ FAILED
```

A failure of one stock must not automatically invalidate successful results for other stocks.

## Decision 3 — Retry

### Decision
Use limited retry for **transient failures**.

Retry is an execution policy, not a responsibility of Technical Analysis, Fundamental Analysis, Scoring, Opportunity Classification, or other business components.

Domain/data failures are not retried merely because they failed.

When the retry limit is exhausted, the affected stock is recorded as failed and the daily execution continues with other stocks when possible.

## Decision 4 — Idempotency

### Decision
Daily automation is idempotent. A duplicate trigger must not create another active/completed execution for the same analysis identity.

The initial idempotency identity is based on:

```text
Analysis Date
+ Analysis Type
+ Strategy Version
+ Configuration
```

The exact representation/hash mechanism is an implementation detail to be defined during TDD/design of the execution model.

## Decision 5 — Recovery and Idempotency

### Decision
Idempotency must not prevent recovery after an execution has finished unsuccessfully or partially successfully.

For the same idempotency identity:

```text
Existing = RUNNING / COMPLETED
→ do not create another execution

Existing = FAILED / COMPLETED_WITH_ERRORS
→ a new recovery execution is allowed
```

This separates duplicate prevention from recovery/retry of a completed execution attempt.

## Decision 6 — Execution Lifecycle

### Decision
Use the following MVP lifecycle:

```text
CREATED
   │
   ▼
RUNNING
   │
   ├──────────────► COMPLETED
   │
   ├──────────────► COMPLETED_WITH_ERRORS
   │
   ├──────────────► FAILED
   │
   └──────────────► CANCELLED
```

`CREATED → RUNNING` occurs when the execution starts. A separate `STARTED` state is intentionally not introduced in the MVP.

### State meanings

- `CREATED`: execution exists but has not started.
- `RUNNING`: execution is in progress.
- `COMPLETED`: the required daily analysis completed successfully.
- `COMPLETED_WITH_ERRORS`: execution completed with one or more stock-level failures.
- `FAILED`: the execution could not complete its core operation.
- `CANCELLED`: execution was explicitly cancelled.

`COMPLETED_WITH_ERRORS` is an outcome state, not a retry state. Retry occurs while execution is running according to the retry policy.

## Architectural Constraint

The automation layer orchestrates existing business capabilities. It must not absorb their domain rules.

```text
Trigger
  ↓
Execution / Orchestration
  ↓
Market Data
  ↓
Data Quality
  ↓
Technical + Fundamental Analysis
  ↓
Scoring
  ↓
Opportunity Classification
  ↓
Reporting
  ↓
Alerts
```

The scheduler determines **when** to run. The orchestrator determines **what** to execute.

## Deferred Decisions

The following remain outside this decision document and must be handled by later design gates when required:

- distributed execution / worker model
- persistent execution storage details
- exact retry count and transient-error taxonomy
- exact idempotency-key encoding/hash implementation
- advanced scheduling rules
- per-stock child execution model
- concurrency and scaling strategy

## TDD Entry Criteria

The Design Gate is complete enough to begin TDD for the M10 execution model.

Next step: define the RED tests for the execution lifecycle, partial failure, retry policy, idempotency, and recovery behavior before implementation.
