# Operator Subscription Administration

This is a restricted, manual administration surface for the existing subscription and entitlement model. Every route below requires operator authorization. It is **not a checkout, payment processor, or proof-of-payment workflow**.

## Plan versions

Create a versioned plan:

```http
POST /api/v1/owner/subscription-plans
Authorization: Bearer <operator-token>
Content-Type: application/json
```

```json
{
  "plan_id": "telegram-pilot",
  "version": 1,
  "display_name": "Telegram Pilot",
  "active": true,
  "entitlements": [
    {"code": "telegram_opportunities", "enabled": true, "limit": 50}
  ]
}
```

Plan versions are immutable. To change entitlements or activation state, create a new version. Read a specific version with:

```http
GET /api/v1/owner/subscription-plans/{plan_id}/{version}
```

## Provision and transition subscriptions

Create a pending subscription:

```http
POST /api/v1/owner/subscriptions
Authorization: Bearer <operator-token>
Content-Type: application/json
```

```json
{
  "user_id": "00000000-0000-4000-8000-000000000001",
  "plan_id": "telegram-pilot",
  "plan_version": 1,
  "starts_at": "2026-10-28T09:00:00+03:00",
  "expires_at": "2026-11-28T09:00:00+03:00",
  "reason": "Manual pilot provisioning"
}
```

- `starts_at` and `expires_at` must include a timezone.
- A new subscription always starts in `PENDING`. Creating it does not grant access.
- Activation is a separate audited transition: `POST /api/v1/owner/subscriptions/{subscription_id}/transition` with `{"status":"ACTIVE","reason":"..." }`.
- The transition reason and actor are written to the subscription event history.
- Read a subscription with `GET /api/v1/owner/subscriptions/{subscription_id}`.
- Read the latest subscription for a user with `GET /api/v1/owner/subscriptions/by-user/{user_id}/latest`.

The optional `payment_provider` and `payment_reference` fields are administrative references only. They must be supplied together and do not verify payment. Do not activate paid access unless the operator has independently completed the approved verification process. No price, plan packaging, refund policy, payment gateway, or automatic activation rule is defined here.

## Error semantics

- `401/403`: operator authentication or authorization failed.
- `404`: the requested plan version or subscription does not exist.
- `409`: immutable plan version conflict, invalid lifecycle transition, duplicate payment reference, or persistence conflict.
- `422`: malformed IDs, invalid entitlements, naive timestamps, or invalid date ranges.
- `503`: subscription storage is not configured.

## Operational limits

- These endpoints are for a restricted owner/operator pilot.
- Do not expose them through a customer-facing account UI.
- A manual `ACTIVE` transition is an audited operator assertion, not an automated payment reconciliation result.
- Customer self-service, invoices, taxes, billing webhooks, payment reconciliation, pricing, refunds, cancellation UX, and commercial entitlement policy remain out of scope until separately approved.
