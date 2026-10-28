# Release Readiness Checklist

**Status:** Checklist template; not a declaration that production deployment is ready.  
**Applies to:** EGX Stock Analyzer API, frontend, Telegram delivery, and persistent SQLite-backed capabilities.

## 1. Environment and secrets

- [ ] Enumerate required environment variables from the current configuration model and deployment files.
- [ ] Confirm production secrets are supplied by the deployment secret store, never committed or placed in frontend build-time variables.
- [ ] Rotate any credentials exposed in logs, local examples, CI output, or repository history.
- [ ] Verify operator authentication is configured and no production endpoint falls back to a development token or permissive mode.
- [ ] Confirm Telegram bot token and webhook secret configuration, webhook authenticity checks, and safe failure behavior.

## 2. Persistence and migrations

- [ ] Identify every SQLite database path and every persistent store enabled in the selected deployment profile.
- [ ] Verify directories, file permissions, volume mounts, backup/restore procedures, and disk-capacity monitoring.
- [ ] Test startup against an existing database and a fresh database.
- [ ] Verify schema initialization is safe across repeated restarts and concurrent application starts.
- [ ] Document migration/rollback steps for schema changes; confirm restore from backup before production release.

## 3. Authentication and authorization

- [ ] Run API smoke tests as unauthenticated, regular user, expired subscription, active entitled user, and operator.
- [ ] Verify owner/operator endpoints reject non-operators on the server, not only in the frontend.
- [ ] Verify subscription entitlement checks apply to every protected API and Telegram delivery path.
- [ ] Confirm authentication errors and audit events do not leak tokens, personal data, or provider request details.

## 4. Market data and analytical safety

- [ ] Record provider, licensing/terms, rate limits, timestamp semantics, and known coverage gaps for every enabled data source.
- [ ] Test stale, missing, duplicate, delayed, malformed, and corrected market observations.
- [ ] Verify all user-facing prices and signals expose data timestamps and uncertainty where relevant.
- [ ] Keep the Crash Radar heuristic labeled as an unvalidated stress score, not a calibrated crash probability.
- [ ] Verify hypothetical signal outcomes are not presented as actual user portfolio executions or P&L.

## 5. Alerts and session reports

- [ ] Verify durable outbox behavior, idempotent publication, duplicate dispatch, retry recovery, and operator-visible failures.
- [ ] Verify no-recipient and no-entitled-recipient suppression states are visible and do not claim successful delivery.
- [ ] Confirm an approved durable scheduler triggers end-of-session reports using the Cairo exchange timezone.
- [ ] Verify report generation and Telegram delivery behavior for duplicate triggers, late/corrected data, missing data, and transport failures.
- [ ] Until durable scheduling and delivery are proven in integration tests, describe session reports as manually/API generated rather than automatic.

## 6. Operations and recovery

- [ ] Confirm structured logs, health/readiness checks, error monitoring, and useful correlation IDs.
- [ ] Verify logs redact credentials and sensitive Telegram/provider payloads.
- [ ] Test process restart, database unavailable, provider timeout, Telegram timeout, and disk-full scenarios.
- [ ] Document backup retention, recovery point objective, recovery time objective, and responsible operator.
- [ ] Verify rollback instructions for API image, frontend image, and database changes.

## 7. Final evidence

- [ ] All required CI jobs pass on the exact release commit.
- [ ] API/UI smoke-test matrix passes against the release candidate.
- [ ] Dependency audit and container/configuration validation pass.
- [ ] Open P0/P1 items are closed or explicitly accepted with owner, impact, and mitigation.
- [ ] M61/backtesting remains paused unless explicitly resumed by the project owner.
- [ ] Release notes identify implemented behavior, known limitations, external dependencies, and any manual operational steps.

A checked box requires evidence from the exact release candidate or deployment environment. Do not infer production readiness from unit tests alone.
