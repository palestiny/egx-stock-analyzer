# DEC-041 — Reporting & Alerts MVP

**Status:** Accepted

## 1. Design Question

How should M11 deliver the analytical results already produced by the core without moving business rules into a report, notification channel, or UI layer?

## 2. Decision

M11 is split into two small domain/application-facing capabilities:

1. **Analysis Report** — an immutable presentation-oriented composition of already-computed analytical results for a stock and analysis period.
2. **Alert Candidate** — an immutable notification candidate derived from an already-computed opportunity classification. It represents *what should be communicated*, not *how or where it is delivered*.

The first MVP targets a single-stock daily report. Batch market reports and ranking are deferred.

## 3. Report Contents

The MVP report contains:

- stock identity
- analysis timestamp/period
- Technical Analysis Result
- Fundamental Analysis Result
- Fundamental Score
- Technical Score
- Stock Quality Score
- Entry Context
- Entry Quality Score
- Opportunity Classification

The report does not recalculate any of these values.

## 4. Alert MVP

An alert candidate is created when the opportunity classification is `BUY`.

The candidate contains enough information to identify the stock and classification and to explain the triggering analytical state. It does not send messages, choose a channel, schedule delivery, or manage deduplication.

Repeated BUY classifications are allowed to produce repeated candidates in this MVP.

## 5. Boundaries

Reporting and alert generation must not own:

- scoring rules
- opportunity thresholds
- technical/fundamental calculations
- ranking
- portfolio allocation
- position sizing
- stop-loss or target logic
- provider integration
- persistence
- UI formatting rules
- email/Telegram/SMS/push delivery
- AI decisions

## 6. Why

The analytical domain remains the source of truth. Reporting composes results; alerting describes a communication candidate. Delivery channels remain replaceable infrastructure/application concerns.

## 7. TDD Acceptance Criteria

### Analysis Report

1. A report preserves the supplied stock identity.
2. A report preserves the supplied analysis period.
3. A report preserves each supplied analytical result and score without recalculation.
4. A report is immutable.
5. Repeated construction with the same inputs is deterministic.

### Alert Candidate

6. BUY classification produces an alert candidate.
7. Non-BUY classifications produce no alert candidate.
8. The alert candidate preserves stock identity and classification.
9. Alert generation does not perform notification delivery.
10. Repeated evaluation with the same inputs is deterministic.

## 8. Deferred Decisions

The following require separate design gates:

- batch reports across all EGX stocks
- ranking/top opportunities
- alert deduplication and state transitions
- alert severity
- alert throttling
- notification channels
- scheduling
- user-specific watchlists
- report persistence
- historical report storage
- dashboard/API presentation
