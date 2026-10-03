# Management Mutation + Audit Durability Gate

## Status

**IMPLEMENTED — verification pending current CI run.**

The concrete SQLite persistence boundary is now explicit. User/credential/audit mutations use SQLiteManagementMutationTransaction, which opens one SQLite connection and commits or rolls back the complete mutation as one unit.

## Transaction boundary

The application mutation port is:

- ManagementMutationTransaction.create_user(...)
- ManagementMutationTransaction.set_user_status(...)
- ManagementMutationTransaction.rotate_credential(...)

The infrastructure implementation is SQLiteManagementMutationTransaction.

Each operation contains the business-state write and its management-audit write inside the same SQLite transaction.

Credential issuance/rotation is prepared in the application layer without persisting first. The transaction then persists the prepared verifier and state together with the audit event. Plaintext credential secrets remain in the one-time IssuedCredential result only.

## Failure semantics

A deterministic audit_failure_hook is available on the SQLite transaction implementation for infrastructure tests. When it raises during audit append, SQLite rolls the entire transaction back.

Coverage added for:

- create user + credential + audit rollback;
- status mutation + audit rollback;
- credential rotation + audit rollback;
- post-failure inspection of users, credentials, and audit rows.

This is failure injection for verification only; production composition does not configure the hook.

## Required final verification

Before declaring this gate PASS:

- run the full unit/integration/quality CI suite on the current branch;
- verify all management mutation tests pass;
- verify the failure-injection tests pass;
- verify credential rotation still invalidates the old secret;
- verify no plaintext credential secret is persisted or emitted by audit/error paths.

## Decision

**Use atomic mutation + audit. Do not introduce an outbox, queue, or broker for this boundary.**

The current SQLite same-file architecture provides the smallest transaction boundary needed by the domain. Revisit this decision only if measured workload or a future persistence migration invalidates the assumption.
