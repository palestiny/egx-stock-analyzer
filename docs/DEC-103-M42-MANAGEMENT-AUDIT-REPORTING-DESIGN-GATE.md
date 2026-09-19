# DEC-103 — M42 Management Audit Reporting Design Gate

**Status:** Proposed  
**Date:** 2026-09-19  
**Milestone:** M42

## 1. Purpose

M41 introduced a durable management-audit boundary for security-sensitive user lifecycle and credential administration events.

The next product gap is read-side visibility into those events. Operators need a controlled way to inspect management activity without exposing raw credentials, credential hashes, internal persistence details, or turning the audit store into an application-wide security policy engine.

M42 therefore defines a read-only management-audit reporting capability before implementation.

## 2. Problem

The system currently records management events, but M41 deliberately deferred audit querying/reporting.

Without a read capability, the audit boundary can preserve evidence but cannot support routine operational investigation such as:

- what management action occurred;
- when it occurred;
- which authenticated identity performed it;
- which user was targeted;
- whether the command succeeded or failed;
- which action category was involved.

The capability must remain read-only and must not change identity, credential, ownership, or lifecycle semantics.

## 3. In Scope

- read-only application capability for management audit records;
- audit read-model boundary;
- deterministic ordering;
- explicit filtering semantics;
- safe representation of audit metadata;
- operator authorization;
- API transport boundary;
- dashboard presentation boundary;
- pagination/retention decision for the MVP;
- deterministic tests.

## 4. Explicitly Out of Scope

- changing audit events or audit-write behavior;
- credential issuance, rotation, revocation, or lifecycle changes;
- user lifecycle mutation;
- public audit access;
- user self-service audit history;
- organizations/delegated administration;
- SIEM integration;
- external log shipping;
- real-time streaming;
- alerting on audit events;
- automatic retention deletion;
- analytics over audit behavior;
- role-management expansion.

## 5. Current Boundary

The intended read-side direction is:

```
React Dashboard
      ↓
HTTP API
      ↓
GetManagementAudit
      ↓
ManagementAuditStore
      ↓
SQLite
```

The application capability owns filtering, authorization input, ordering, and read-model semantics.

FastAPI owns HTTP transport only.

React owns presentation only.

Raw credentials and credential hashes remain outside the read model.

## 6. Candidate Alternatives

### A — Expose the Persistence Model Directly

Return database rows through the API.

**Trade-offs**
- smallest implementation;
- tightly couples API semantics to SQLite schema;
- risks exposing storage details;
- makes future storage changes harder.

### B — Dedicated Application Read Capability

Introduce `GetManagementAudit` with an explicit read model over `ManagementAuditStore`.

**Trade-offs**
- clear application ownership;
- keeps persistence replaceable;
- requires a small mapping/read-model layer;
- preserves the project's application/API/domain separation.

### C — Reuse Generic Operational Workflow Visibility

Extend the existing scheduled-workflow operational read capability to include management audit events.

**Trade-offs**
- superficially reduces the number of read services;
- mixes unrelated operational concepts;
- creates an unclear ownership boundary between workflow execution and security-management evidence.

## 7. Open Decisions

The following questions must be resolved before implementation:

1. **Visibility:** Is M42 operator-only, or should an authenticated user be able to see only events concerning their own identity?
2. **Actor/target semantics:** Which actor and target identifiers are exposed, and should deleted identities remain represented by UUID only?
3. **Filters:** Which filters belong in the MVP — actor user ID, target user ID, action type, outcome, and time range?
4. **Ordering:** What deterministic ordering should be authoritative when timestamps collide?
5. **Pagination:** Should M42 introduce bounded pagination now, or expose a deliberately small unpaged MVP?
6. **Limits:** What maximum page size/default size is appropriate if pagination is selected?
7. **Retention:** Should M42 only read existing records and leave retention unchanged?
8. **API shape:** Should the endpoint return an `items` envelope consistent with existing operational read APIs?
9. **Dashboard:** Should the first dashboard slice be operator-only and read-only?
10. **Authorization timing:** Does the existing operator authorization boundary remain sufficient for M42?

## 8. Proposed Invariants

1. Audit reporting is strictly read-only.
2. Audit reporting never returns raw credentials or credential hashes.
3. Audit reporting does not recalculate or reinterpret historical management outcomes.
4. Stored audit timestamps and identities remain authoritative.
5. Ordering is deterministic.
6. API transport does not own filtering or authorization policy.
7. Dashboard code does not implement authorization rules.
8. Existing M41 audit-write semantics remain unchanged.
9. No analytical domain module depends on management audit reporting.
10. Retention/deletion of audit evidence is not introduced accidentally by a read capability.

## 9. TDD Acceptance Shape

After the design is accepted, tests should cover at least:

- empty audit result;
- deterministic ordering;
- actor filtering;
- target filtering;
- action filtering;
- outcome filtering;
- time-range filtering if accepted;
- pagination semantics if accepted;
- no credential/hash leakage;
- operator authorization;
- read-only behavior;
- API transport mapping;
- dashboard presentation states if dashboard exposure is accepted.

## 10. Design Gate Decision

**Status: Proposed — implementation is not authorized by this document yet.**

M42 implementation must wait until the open decisions above are resolved and recorded as accepted.

## 11. Revisit Conditions

Revisit this gate if:

- audit requirements become compliance-driven;
- external SIEM/log shipping becomes required;
- retention/legal requirements emerge;
- user-facing audit history becomes a product requirement;
- richer roles or organizations change audit visibility semantics;
- real-time security-event monitoring becomes necessary.
