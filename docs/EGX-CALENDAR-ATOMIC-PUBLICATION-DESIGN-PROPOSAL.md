# EGX Calendar Atomic Publication — Design Proposal

**Status:** Proposed; owner approval required before implementation  
**Date:** 2026-11-09  
**Scope:** Calendar version publication plus immutable per-day evidence persistence only

## 1. Context and verified problem

The calendar-version repository and calendar-evidence repository currently own separate SQLite connection lifecycles. Calendar evidence references an existing calendar version, and evidence insertion validates that the evidence date is explicitly covered by that version. Each repository opens its own connection, so a sequence of API-level calls cannot provide a single atomic commit across the version and its evidence.

A validation pre-check followed by separate writes is insufficient: the calendar version could be committed while evidence insertion fails, or a conflict could be detected only after partial state has been persisted.

## 2. Proposed owner-visible behavior

A publication request succeeds only when the immutable calendar version and its complete required per-day evidence set are persisted together. If any validation or write fails, none of those publication records become visible as committed state.

Publication remains separate from activation. Successful publication does not set the active calendar, create activation/deactivation/rollback events, initialize a lifecycle cursor, or enable monitoring.

## 3. Proposed transaction boundary

Use one calendar-specific SQLite Unit of Work (UoW):

1. Open one connection to the configured calendar database.
2. Start `BEGIN IMMEDIATE` to serialize competing writers before reading mutable publication constraints.
3. Validate actor identity and authorization using the existing individual operator model.
4. Validate request shape and canonicalize payloads before persistence.
5. Insert the immutable calendar version through the UoW connection.
6. Insert immutable evidence records and explicit calendar-day-to-evidence links through the same connection.
7. Evaluate required evidence coverage, accepted evidence kinds, source-policy constraints, supersession rules, and unresolved conflicts using the same transaction state.
8. Commit only after every gate passes; otherwise roll back all writes.

The UoW owns commit/rollback and connection closure. Repositories participating in this use case receive the transaction-scoped connection or a narrow transaction-scoped repository interface. They must not create their own connections inside the publication transaction.

Do not build a generic transaction framework across unrelated domains. Keep the first implementation calendar-specific.

## 4. Evidence linkage and validation

Each explicit calendar-day assertion should link to one or more immutable evidence record IDs. Validation must prove:
- linked evidence belongs to the exact calendar version being published;
- evidence date matches the calendar day;
- evidence kind is accepted for the asserted claim;
- every required day/claim has sufficient evidence;
- superseded evidence is not treated as an active claim;
- unresolved contradictory active claims block publication;
- source category satisfies the approved source policy.

The exact evidence acceptance matrix and source-category policy are not decided here. Until the owner approves them, implementation must not invent universal acceptance rules or silently classify a third-party source as primary evidence.

## 5. Failure and concurrency matrix

| Failure point | Required result |
|---|---|
| Before version insert | No publication rows |
| After version insert | Version rolled back |
| After first or later evidence insert | Version and all evidence rolled back |
| After day-link insertion | Version, evidence, and links rolled back |
| Final coverage/conflict validation | Entire transaction rolled back |
| Concurrent writer | Serialized by SQLite write transaction; deterministic conflict or successful independent publication |
| Process termination before commit | SQLite recovery leaves no partial committed publication |
| Unauthorized/inactive operator | Rejected before persistent writes |

## 6. Required tests

- Unit tests for UoW commit, rollback, connection ownership, and exception propagation.
- Integration tests with a temporary on-disk SQLite database and production repository composition.
- Failure injection after version insert, after evidence writes, after link writes, and during final validation.
- Assert all participating tables contain no partial publication rows after rollback.
- Assert a separate connection cannot observe uncommitted writes and can observe all rows after commit.
- Concurrent publication tests for writer serialization and immutable-version conflicts.
- Negative tests for missing coverage, unsupported evidence kind, conflicting claims, wrong version/date linkage, invalid supersession, and unauthorized actor.
- Regression tests for existing read APIs, evidence hash verification, append-only triggers, and schema upgrade from databases created before the change.

## 7. Compatibility and migration

Prefer reusing existing immutable evidence identifiers and current schema constraints. Add an explicit link table only if the current schema cannot represent the required day-to-evidence relationship unambiguously. Any migration must:
- be additive and deterministic;
- preserve existing rows and hashes;
- avoid fabricating links for historical evidence;
- have upgrade tests against a pre-change database;
- document operational backup and rollback procedure.

Existing evidence without explicit links must remain visibly unlinked and cannot be silently treated as satisfying the new publication gate.

## 8. Security and audit

Only an active individually attributable operator credential may publish. Preserve actor identity and auditability. Never attribute a human action to the system bootstrap identity. Keep audit records in the same transaction when they describe the publication attempt's committed state; separately persisted security-denial telemetry, if desired, must not imply a successful publication.

## 9. Explicit non-goals

This proposal does not:
- decide which source classes are sufficient for each calendar claim;
- decide whether source artifacts must be archived or stable external references plus hashes are sufficient;
- prove authenticity from SHA-256 alone;
- approve activation bootstrap or cursor-derived coverage;
- expose activation/deactivation/rollback HTTP endpoints;
- connect calendar state to lifecycle scheduling;
- enable freshness enforcement, Crash Radar monitoring, or M61.

## 10. Approval gate

Before implementation, the owner must explicitly approve this transaction architecture:

**One calendar-specific SQLite Unit of Work must persist the calendar version, its per-day evidence records and explicit links, and publication validation within one transaction; any failure rolls the entire publication back.**

Until that approval is explicit, this document remains a proposal and no runtime code changes are authorized.
