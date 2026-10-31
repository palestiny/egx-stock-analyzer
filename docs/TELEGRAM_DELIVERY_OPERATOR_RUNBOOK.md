# Telegram Delivery Operator Runbook

**Status:** Operational procedure for the operator-only reconciliation API  
**Scope:** Investigating and manually resolving Telegram recipient delivery records in `FAILED` or `DELIVERY_UNKNOWN`  
**Out of scope:** Automatic retries, manual resend/requeue, Telegram bot administration, subscription entitlement changes, and trading decisions

## 1. Safety rules

- A delivery is tracked per event, user, and channel. Inspect and resolve the exact recipient record; do not infer that all recipients of an event share the same outcome.
- `FAILED` means the provider returned a definite failure. `DELIVERY_UNKNOWN` means the send crossed the external-send boundary but the application could not establish whether Telegram accepted it.
- Never interpret `DELIVERY_UNKNOWN` as proof of non-delivery. Check Telegram-side evidence and the recipient context before resolving it.
- Do not resend a `DELIVERY_UNKNOWN` message. The system deliberately does not automatically resend it because that could create duplicates.
- A manual outcome is terminal for that delivery record:
  - `CONFIRMED_DELIVERED` records `DELIVERED`.
  - `CONFIRMED_NOT_DELIVERED` records `NOT_DELIVERED`. This is terminal and is not requeued or resent.
- Every resolution requires an authenticated operator identity and a reason. The state transition and audit append are committed atomically.
- These endpoints do not send Telegram messages. There is no manual resend action in this API.
- Do not paste bot tokens, chat IDs, bearer tokens, or raw transport diagnostics into audit reasons.

## 2. Access and endpoints

All endpoints require the existing operator authentication dependency. Send the operator bearer token in the `Authorization` header over HTTPS. Do not use a development API exposed to the public internet.

| Method | Endpoint | Purpose |
| --- | --- | --- |
| GET | `/api/v1/management/telegram-deliveries/unresolved` | List `FAILED` and `DELIVERY_UNKNOWN` recipient records |
| POST | `/api/v1/management/telegram-deliveries/{event_id}/{user_id}/reconcile?channel=telegram` | Record one explicit manual outcome |
| GET | `/api/v1/management/telegram-deliveries/reconciliation-audit` | Read the durable reconciliation audit |

List endpoints accept `limit` (1–200, default 50) and `offset` (default 0). Results are paginated; increment the offset to inspect later pages. Unresolved records are ordered oldest-updated first. Audit records are returned newest first.

The unresolved list exposes event/user identifiers, channel, status, attempt count, and created/updated timestamps. It intentionally omits raw transport error details and chat identifiers.

## 3. List unresolved records (PowerShell)

Set the API URL and obtain the operator token through your approved secret-handling process. Avoid writing the token into a committed script or shell history.

```powershell
$BaseUrl = "https://your-api-host"
$Headers = @{ Authorization = "Bearer $env:EGX_OPERATOR_TOKEN" }
$Unresolved = Invoke-RestMethod -Method Get -Uri "$BaseUrl/api/v1/management/telegram-deliveries/unresolved?limit=50&offset=0" -Headers $Headers
$Unresolved.items | Format-Table event_id, user_id, channel, status, attempts, updated_at
```

For each row, verify the event and recipient using authorized application records and available Telegram-side evidence. The API list is an operational queue, not proof of what happened remotely.

## 4. Resolve one record

Choose an outcome only after investigation:

- Use `CONFIRMED_DELIVERED` only when there is reliable evidence that the recipient received the message.
- Use `CONFIRMED_NOT_DELIVERED` only when there is reliable evidence that it was not received and the operator intentionally accepts the terminal, no-resend result.
- If evidence is inconclusive, leave the record unresolved. Do not guess.

Example request:

```powershell
$EventId = "00000000-0000-0000-0000-000000000000"
$UserId = "00000000-0000-0000-0000-000000000000"
$Body = @{ outcome = "CONFIRMED_DELIVERED"; reason = "Verified recipient delivery against the authorized Telegram conversation record." } | ConvertTo-Json
$Uri = "$BaseUrl/api/v1/management/telegram-deliveries/$EventId/$UserId/reconcile?channel=telegram"
Invoke-RestMethod -Method Post -Uri $Uri -Headers $Headers -ContentType "application/json" -Body $Body
```

The request body requires:
- `outcome`: exactly `CONFIRMED_DELIVERED` or `CONFIRMED_NOT_DELIVERED`.
- `reason`: 3–1000 characters, describing the evidence and operator rationale without secrets or unnecessary personal data.

The channel defaults to `telegram`; pass the channel explicitly when resolving a non-default channel record.

A successful response includes the previous and new status, outcome, authenticated actor subject, reason, and UTC timestamp. Preserve the response/reference in the incident record if your operational process requires it.

## 5. Verify the audit record

After a successful resolution, query the audit endpoint and confirm the event ID, user ID, channel, outcome, actor, reason, and timestamp.

```powershell
$Audit = Invoke-RestMethod -Method Get -Uri "$BaseUrl/api/v1/management/telegram-deliveries/reconciliation-audit?limit=50&offset=0" -Headers $Headers
$Audit.items | Format-Table event_id, user_id, previous_status, new_status, outcome, actor_subject, occurred_at
```

The audit is append-only through this API. A resolved record cannot be reconciled a second time; conflicting or repeated attempts are rejected rather than silently overwriting the first decision.

## 6. Expected API responses

| HTTP status | Meaning | Operator action |
| --- | --- | --- |
| 200 | List, audit read, or reconciliation succeeded | Verify returned identifiers and recorded outcome |
| 400 | Invalid pagination or request values | Correct the request |
| 401 | Missing or invalid operator authentication | Re-authenticate through the approved process |
| 404 | Delivery record does not exist | Re-check event ID, user ID, and channel |
| 409 | Record is not eligible or was already changed/resolved | Refresh unresolved list and audit; do not retry blindly |
| 503 | Reconciliation store is not configured | Escalate as an application configuration/availability incident |

## 7. Operational limitations and escalation

- There is currently no operator UI documented for this workflow; use the authenticated API only.
- There is no retry schedule, backoff, maximum-attempt count, or automatic exhaustion policy approved for definite `FAILED` outcomes. Do not create ad-hoc retries by changing database rows.
- `DELIVERY_UNKNOWN` is intentionally excluded from automatic resend. A manual resolution is an evidence-based record, not a way to force delivery.
- `NOT_DELIVERED` is terminal. If a future business requirement needs a deliberate resend workflow, it requires a separately designed, audited operation and owner approval.
- If an event remains unresolved because one recipient is `FAILED` or `DELIVERY_UNKNOWN`, inspect recipient-level state and audit history. Do not infer that a partially delivered event should be broadcast again.
- Escalate missing records, database errors, unexpected state transitions, or discrepancies between Telegram evidence and the application audit to the application owner. Preserve timestamps and identifiers, but do not include credentials or raw secret-bearing URLs.

## 8. Related decisions

- `docs/TELEGRAM-DELIVERY-CONCURRENCY-DESIGN-GATE.md` — claim ownership, lease recovery, ambiguous delivery, and retry-policy boundaries.
- DEC-136 — ambiguous Telegram delivery outcomes are manually reconciled; no automatic resend.
- Owner-approved lease rule — lease duration is twice the effective configured Telegram transport timeout. This does not authorize retry timing or attempt limits.
