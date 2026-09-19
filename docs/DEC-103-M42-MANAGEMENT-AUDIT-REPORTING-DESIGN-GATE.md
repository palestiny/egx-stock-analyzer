# DEC-103 — M42 Management Audit Reporting Design Gate

**Status:** Accepted  
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

## 7. Accepted Decisions

1. **Visibility — operator-only.** M42 is an operational/security-management read capability, not a user-facing personal history surface. It is protected by the existing operator authorization boundary. This keeps the first audit reader aligned with the M41 management commands and avoids prematurely defining user-visible audit semantics.

2. **Actor/target semantics — UUID only.** The read model exposes `actor_user_id` and `target_user_id` as immutable UUIDs, plus the stored action, outcome, and timestamp. Deleted users remain represented by their historical UUID; no name/profile lookup is required. This preserves historical attribution without coupling audit history to mutable user presentation data.

3. **Filters — all five are accepted.** MVP filtering supports actor user ID, target user ID, action, outcome, and UTC time range (`from` inclusive, `to` exclusive). Filters are optional and combined with AND semantics. No free-text search is introduced.

4. **Ordering — newest first with immutable row identity as tie-breaker.** The authoritative order is `occurred_at DESC, audit_id DESC`. The current write store already has an SQLite `id`; M42 must expose that identity internally to the read adapter/read model as needed for deterministic ordering but must not expose storage implementation details through the API.

5. **Pagination — bounded pagination is required in the MVP.** Audit data is potentially security-sensitive and unbounded growth makes an unpaged API unsafe operationally. The application capability returns a page plus a continuation cursor/offset contract rather than loading the complete table.

6. **Limits — bounded page size.** Default page size is 50 and maximum page size is 100. Invalid non-positive or over-maximum requested sizes are rejected at the application boundary. The API must not allow an arbitrary unbounded limit.

7. **Retention — read-only; no retention mutation.** M42 reads existing records and introduces no deletion, compaction, archival, or automatic retention policy. Retention remains a separate future decision.

8. **API shape — `items` envelope with explicit pagination metadata.** The endpoint returns an `items` collection plus pagination metadata, consistent with the existing operational read APIs. Transport maps the application read model and does not query SQLite directly.

9. **Dashboard — operator-only, read-only first slice.** The dashboard presents the audit list and accepted filters/pagination state. It does not implement authorization, filtering semantics, ordering, or data access rules locally.

10. **Authorization timing — reuse the existing operator authorization boundary now.** No new permission is introduced in M42. A future richer role model may split audit-read permission from general operator permission under a separate design gate.

### Design trade-offs

The accepted design deliberately favors a dedicated read capability with bounded pagination and immutable UUID attribution over the smallest possible database-to-HTTP path. This adds a read model and pagination contract, but keeps storage replaceable, prevents unbounded reads, preserves historical identity, and leaves authorization policy in the application boundary.

The MVP also deliberately does not add user self-service audit history, retention policy, real-time streaming, analytics, SIEM export, or a new permission model.

## 8. Accepted Invariants

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
- time-range filtering;
- pagination semantics;
- no credential/hash leakage;
- operator authorization;
- read-only behavior;
- API transport mapping;
- dashboard presentation states;

## 10. Design Gate Decision

**Status: Accepted — implementation is authorized for the M42 MVP defined here.**

The implementation boundary is:

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

The application read capability owns filtering, bounded pagination, deterministic ordering, and read-model semantics. API transport owns HTTP mapping only. The dashboard owns presentation only. Existing M41 audit-write behavior remains unchanged.

## 11. Revisit Conditions

Revisit this gate if:

- audit requirements become compliance-driven;
- external SIEM/log shipping becomes required;
- retention/legal requirements emerge;
- user-facing audit history becomes a product requirement;
- richer roles or organizations change audit visibility semantics;
- real-time security-event monitoring becomes necessary.
