# Engineering hardening plan

**Policy:** Pause new product capabilities and nonessential infrastructure expansion until M61 has an accepted real historical dataset and a reproducible evaluation. Security and operational defects may still be fixed.

## Completed on main

- PR #240 — immutable SQLite research-dataset persistence; CI passed before merge.
- PR #241 — indexed SHA-256 lookup for newly issued high-entropy bearer tokens and process-local failed-authentication throttling; CI passed before merge.
- PR #242 — shared SQLite connection configuration with WAL and a 5-second busy timeout; CI passed before merge.
- PR #245 — UTC timestamps for market-data conflict events; CI passed before merge.
- PR #246 — race-safe first-time WAL initialization; regression tests and CI passed before merge.

## In review

- PR #243 — Python 3.12 compatibility, CI lint/type/coverage/dependency-audit gates, and Cairo calendar-date handling. CI must pass before merge.
- PR #244 — Docker/Compose baseline, explicit CORS allowlist, and user-facing financial disclaimer. The stack must be built and tested in CI before merge.


## Remaining hardening work

1. **Credential rollout:** inventory existing PBKDF2 credentials and reissue/rotate them before deploying with legacy fallback disabled. The compatibility flag is temporary and must not be exposed to untrusted traffic without upstream throttling.
2. **Shared rate limiting:** configure reverse-proxy or shared-service throttling for multi-worker/multi-instance deployments. The current in-process limiter is defense-in-depth only.
3. **Timestamp audit:** complete the DTZ lint cleanup. Persisted instants use aware UTC; EGX trading dates use `Africa/Cairo`; provider timestamps retain explicit source semantics.
4. **SQLite operations:** add backup/restore checks and a realistic concurrent reader/writer test; WAL does not allow simultaneous writers.
5. **Lint backlog:** expand Ruff rules incrementally. Do not perform a repository-wide auto-fix without reviewing behavior and the existing test baseline.
6. **Type/coverage gates:** widen mypy scope and set a coverage threshold after the initial baseline is measured.
7. **Dependency security:** resolve any future pip-audit findings as part of normal dependency updates.
8. **Code structure:** split `app/api/main.py` and the workflow store only in small behavior-preserving refactors with contract tests. Avoid refactoring solely to reduce line count.
9. **Deployment:** validate both container builds, persistent-volume backup/restore, proxy/TLS configuration, host restrictions, and secret rotation before public exposure.
10. **License:** owner decision required; do not add a license without an explicit choice.

## M61 evidence gate remains open

No production Strategy v0 performance claim is permitted until the required historical market and point-in-time financial artifacts pass the source, coverage, provenance, adjustment, missing-data, survivorship, and reproducibility acceptance gate. Fixture tests and deterministic engine tests do not replace this evidence.
