# M27 — Alert Delivery Trigger & Transport Boundary MVP Completion

**Status:** Complete  
**Date:** 2026-09-19  
**Design Gate:** `docs/DEC-086-M27-ALERT-DELIVERY-TRIGGER-DESIGN-GATE.md`  
**Implementation PR:** #43

## Accepted Outcome

M27 adds an explicit application/API command for delivering an existing alert candidate without triggering fresh analysis.

The accepted command is:

`POST /api/v1/alerts/{symbol}/deliver?channel=telegram`

The command:

- resolves the candidate through `GetAlertCandidate`;
- delegates delivery to the existing M25 `DeliverAlert` capability;
- preserves durable idempotency;
- returns the persisted delivery outcome;
- keeps Telegram-specific behavior behind the existing provider boundary;
- leaves `GET /api/v1/alerts/{symbol}` read-only.

## Transport Semantics

- missing alert candidate → HTTP 404;
- delivery not configured → HTTP 503;
- successful delivery → HTTP 200 with `delivered`;
- persisted provider failure → HTTP 200 with `failed` and safe diagnostic text;
- repeated successful delivery → existing delivered record, with no second provider call.

## Boundary

```
POST /api/v1/alerts/{symbol}/deliver
          ↓
DeliverAlertBySymbol
          ↓
GetAlertCandidate + DeliverAlert
          ↓
NotificationProvider
          ↓
TelegramNotificationProvider
```

No analytical values are recalculated and no analysis execution is triggered.

## Validation

PR #43 was validated by GitHub Actions Run #730 on implementation head `396383e9cd3857459f0f6249f688d279c8cca264`.

- Python unit-tests job: **success**
- Frontend tests job: **success**
- Frontend production build: **success**

The merge commit is `94ca5642ead67a5658ee0f53badd9b3ba69ecf35`. The workflow-run integration does not expose a separate workflow run for the merge commit, so validation is attributed to the tested PR head.

## Explicitly Deferred

- automatic delivery after analysis;
- bulk delivery;
- multiple-channel fan-out;
- failed-delivery retry operation;
- queues/workers;
- scheduled delivery;
- user notification preferences;
- delivery analytics;
- trading execution;
- AI notification decisions.

The next capability requires a separate design gate.
