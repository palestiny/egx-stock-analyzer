# Individual Operator Access Control

## Decision

Privileged operator access is granted to an individual active application user, not to a shared bearer-token subject. A privileged request must authenticate with an active durable credential belonging to a user with an active operator grant. The authenticated identity retains both the user ID and credential ID.

The legacy shared operator token remains available to unrelated legacy operator routes during migration, but it is not accepted by the operator grant-management service and must not authorize session-calendar administration after the calendar API migration is complete.

## Persistence and audit

- `operator_access_current` is the current authorization projection.
- `operator_access_events` is append-only and records BOOTSTRAP, GRANT, and REVOKE actions.
- Individual grant/revoke events include actor user ID, actor credential ID, target user ID, reason, and UTC timestamp.
- The first operator is bootstrapped only when no active operator exists, from a trusted local administrative environment, for an active user with an active durable credential.
- The bootstrap event is explicitly marked `SYSTEM_BOOTSTRAP`; it is not misrepresented as an individual actor.
- A grant or revoke requires an active operator identity and the exact active durable credential used for the request.
- The last active operator cannot be revoked or disabled.
- Disabling an operator removes their effective authority immediately; the grant history is preserved.

## Operational bootstrap

Run from a trusted host with access to the application SQLite database:

```powershell
python -m app.infrastructure.operator_access_bootstrap --database-path "PATH_TO_ANALYSIS_DB" --user-id "USER_UUID" --reason "Initial operator bootstrap"
```

The target user must already exist and have at least one active durable credential. The command is one-time: it fails if an active operator already exists. Do not put credentials or bearer secrets in command arguments.

## API management

After bootstrap, an individually authenticated operator can:
- `POST /api/v1/operators/{user_id}/grant` with a reason.
- `POST /api/v1/operators/{user_id}/revoke` with a reason.
- `GET /api/v1/operators/access-events` to inspect the immutable audit history.

The service rejects the legacy synthetic operator identity even if it passes a generic legacy operator dependency.

## Remaining integration gates

- Update the session-calendar admin router to require an individually attributable operator identity, including a durable credential ID.
- Add route-level tests proving the legacy shared token is denied and an individually granted operator is accepted.
- Confirm exact-head CI and review migration behavior against an existing production SQLite database.
- Do not activate any calendar or lifecycle scheduler as part of this access-control change.
