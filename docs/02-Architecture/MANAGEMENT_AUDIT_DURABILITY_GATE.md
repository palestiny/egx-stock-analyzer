# Management Mutation + Audit Durability Gate

## Status

**NOT PROVEN — blocked on persistence transaction capability.**

The current `UserManagementService` performs a durable-looking mutation and then appends the management audit event. The application ports do not currently expose a shared transaction boundary:

- `UserStore.save(...)`
- `CredentialStore.create/replace/revoke(...)`
- `ManagementAuditStore.append(...)`

Therefore the system cannot currently prove atomicity between the business mutation and its audit record.

## Required semantics

For a mutation that changes user/credential state, we need one of these explicitly implemented semantics:

1. **Atomic mutation + audit** — preferred if the concrete stores share one transactional durable backend.
2. **Explicit post-commit audit failure** — acceptable only if the API/application contract makes the successful mutation and audit failure observable separately and retry behavior is idempotent.
3. **Transactional outbox** — only if the existing persistence boundary cannot atomically contain the audit write and operational evidence justifies asynchronous delivery.

We should not introduce a queue/broker merely to hide the current boundary.

## Current risk

For example:

1. `set_status(...)` saves the new user status.
2. `_record(...)` calls `audit_store.append(...)`.
3. If audit append fails, the service raises after the user mutation has already occurred.
4. A client seeing an error can retry, while the audit trail may be incomplete.

This is a real consistency boundary, not a logging concern.

## Verification gate

Before declaring this gate PASS we need:

- concrete implementations of UserStore/CredentialStore/ManagementAuditStore identified;
- their transaction capabilities documented;
- deterministic failure injection at the audit write boundary;
- proof of either atomic rollback or an explicit post-commit failure contract;
- retry/idempotency behavior tested;
- no plaintext credential secret in audit/error/log output.

## Decision

**Do not merge the remediation PR on the basis of the current application-layer tests.**

Next implementation step is to locate/introduce the concrete persistence boundary and choose the smallest transaction design supported by it.
