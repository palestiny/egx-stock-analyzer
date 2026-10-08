# Engineering hardening and operations guide

**Policy:** Pause new product capabilities and nonessential infrastructure expansion until M61 has an accepted real historical dataset and a reproducible evaluation. Security and operational defects may still be fixed.

## Current hardening status

- PR #240 — immutable SQLite research-dataset persistence; CI passed before merge.
- PR #241 — indexed SHA-256 lookup for newly issued high-entropy bearer tokens and process-local failed-authentication throttling; CI passed before merge.
- PR #242 — shared SQLite connection configuration with WAL and a 5-second busy timeout; CI passed before merge.
- PR #245 — UTC timestamps for market-data conflict events; CI passed before merge.
- PR #246 — race-safe first-time WAL initialization; concurrency regression tests and CI passed before merge.
- PR #243 — Python 3.12 and 3.13 test coverage, Ruff critical/datetime lint, scoped mypy, 85% unit-test coverage floor, dependency audit, and Cairo market-date helper; CI passed before merge.
- PR #247 — container baseline, explicit CORS configuration, trusted-proxy handling, and financial disclaimer; API/frontend container builds and CI passed before merge.
- PR #248 — removal of 47 unused imports and enforcement of Ruff F401; CI passed before merge.
- PR #252 — shared Nginx per-client API throttling, bounded in-process authentication limiter state, SQLite WAL reader/writer regression coverage, and backup/restore smoke test; CI passed before merge.
- PR #253 — enable the full Ruff F-rule family alongside critical E and timezone rules; moved two accidentally misplaced simulator tests out of production code, restored their test discovery, corrected their warmup expectations, and fixed the missing `user_management` runtime exposure; CI passed on Python 3.12 and 3.13, with frontend, integration, container-build, and dependency-audit jobs successful.
- PR #255 — add frontend ESLint and `npm audit --audit-level=high`; upgrade the vulnerable transitive `source-map-js` lock entry from 1.2.1 to patched 1.2.2; remove frontend lint errors around effect-driven loading and unused globals/imports. CI passed on Python 3.12 and 3.13, frontend lint/tests/build, integration tests, container builds, and Python dependency audit; unit suite reported 966 passed, 7 deselected, with 91.06% coverage.

## Security and credential migration

### Indexed bearer-token lookup

New durable bearer credentials are opaque 256-bit tokens. The database stores a SHA-256 verifier and resolves it through an index on `(status, verifier)`, avoiding a PBKDF2 operation for every active credential on every request. SHA-256 is appropriate here because the token is generated with high entropy; do not reuse this approach for human passwords.

### Existing PBKDF2 credentials

PBKDF2 verifier rows cannot be converted to SHA-256 without the original raw token. The compatibility scan is disabled by default. During a controlled migration only, set `EGX_ALLOW_LEGACY_PBKDF2_CREDENTIALS=true`; each successfully authenticated legacy credential is upgraded to SHA-256. This compatibility mode restores an expensive scan for unknown tokens and must be temporary. Disable it after all active credentials have authenticated or been reissued.

If existing sessions must be preserved, enable the compatibility flag only behind upstream rate limiting and plan credential rotation. Do not expose a deployment with legacy fallback enabled directly to untrusted traffic.

### Failed-authentication throttling

The API temporarily blocks a client after 10 failed authentication attempts within 60 seconds and returns HTTP 429 with `Retry-After`. The limiter is process-local and is a defense-in-depth control, not a distributed lockout. Multi-worker/multi-instance deployments must also enforce limits at a trusted reverse proxy or shared rate-limit service.

`EGX_TRUST_PROXY_HEADERS=true` enables use of `X-Real-IP` for the limiter. Only enable it when the API is unreachable directly by untrusted clients and the trusted proxy overwrites that header. The provided Compose stack keeps the API internal and uses Nginx to set it.

## SQLite concurrency and operations

All application SQLite stores use the shared connection helper. Connections have a 5-second connection timeout and `PRAGMA busy_timeout=5000`; file-backed databases use WAL journaling to improve reader/writer concurrency.

WAL does not allow simultaneous writers. Keep write transactions short and retry only operations whose idempotency semantics are known. The WAL initialization helper handles concurrent first-time opens, and a regression test covers that race.

The database must live on a filesystem that supports SQLite locking correctly. Do not assume network shares or unsupported synced folders are safe. Before production use, verify backup/restore of the SQLite volume and periodically test restoration.

## Timestamp conventions

- Persisted instants (credential, workflow, acquisition, audit, and conflict-event timestamps) use timezone-aware UTC values.
- EGX trading-session dates are calendar dates in `Africa/Cairo` and must not be inferred from the server's local timezone.
- Use `app.application.clock.egx_today()` for the current EGX calendar date.
- Provider bar timestamps retain their source semantics and are normalized only by an explicit, tested adapter rule.
- Do not use `datetime.now()`, `datetime.utcnow()`, or `date.today()` for production event/session logic without an explicit timezone policy.
- The `tzdata` dependency supplies IANA timezone data on Windows hosts.

## Container deployment

The root `Dockerfile` builds the FastAPI API on Python 3.12 and runs as a non-root user. `frontend/Dockerfile` builds React and serves static assets with Nginx. `compose.yaml` connects the frontend to the API on an internal Compose network and persists SQLite under the `egx-data` volume. CI validates Compose configuration and builds both images.

From PowerShell, set a strong operator token before starting Compose:

```powershell
$env:EGX_OPERATOR_TOKEN = "<replace-with-a-long-random-secret>"
docker compose up --build -d
```

The frontend is available at `http://localhost:8080` by default, bound to loopback. Do not commit real credentials or a populated `.env` file.

### TLS and reverse proxy

This Compose stack serves HTTP only. It is intended for local validation or operation behind a trusted TLS-terminating reverse proxy/load balancer. Do not expose it directly to the public internet without HTTPS, host-level firewall rules, request-size/time limits, access logs, and trusted proxy configuration. The API is not published to the host by default.

### CORS

Same-origin frontend/API routing is the default. For a separately hosted frontend, set `EGX_CORS_ALLOWED_ORIGINS` to a comma-separated list of exact origins (scheme + host + optional port), for example `https://dashboard.example.com`. Wildcard origins are rejected because credentials are enabled. CORS is a browser policy, not an authentication or authorization control.

### Before public use

- Rotate development credentials and use a secret manager.
- Restrict network access and terminate TLS at a trusted proxy.
- Verify backup/restore, disk capacity, application logs, and authentication-failure monitoring.
- Configure explicit CORS origins only if cross-origin browser access is needed.
- Validate provider terms and source quality separately; containerization does not certify market data or analytical results.
- Do not treat research scores or backtests as guarantees of returns.

## Remaining items requiring an owner decision or production environment

- **M61 historical evidence and source acceptance:** intentionally not changed in this hardening pass, per request. The accepted real dataset, official/licensed bulk source or permitted fallback, provenance, point-in-time financial coverage, and reproducible Strategy v0 evaluation remain the main blocker. No profitability or production analytical-value claim is justified.
- **Credential migration:** before deployment, reissue/rotate existing credentials that still use legacy PBKDF2 verification. Keep legacy compatibility disabled unless a controlled migration is protected by upstream throttling.
- **Production perimeter:** the included Compose stack is HTTP-only and loopback-bound. A real deployment still needs a trusted TLS terminator, host/firewall restrictions, secret management, request-size/time limits, and edge rate-limit configuration. The Nginx limit in this repository is per instance and needs tuning for expected traffic.
- **Operational recovery:** SQLite WAL, timeout, concurrency behavior, and a backup/restore smoke test are covered. A production operator still needs scheduled backups and a tested restore drill on the actual deployment volume.
- **License:** no license was added because choosing the legal reuse terms requires the repository owner's explicit decision.
- **Maintainability:** the large API composition module and workflow store were not split during this pass. The repository's sequential decision records are retained for traceability; overlapping hardening guidance was consolidated. Defer broad structural refactors until the M61 evidence gate is closed.
- **Type-check scope:** CI now runs mypy on hardened authentication primitives, not the entire application. Expanding the checked surface remains follow-up work after the current M61 priority.

## License decision remains open

No software license has been selected. A public GitHub repository without an explicit license does not automatically grant general reuse rights. The repository owner must choose the intended license before advertising the project for external reuse or distribution.

## M61 evidence gate remains open

No production Strategy v0 performance claim is permitted until the required historical market and point-in-time financial artifacts pass source, coverage, provenance, adjustment, missing-data, survivorship, and reproducibility acceptance. Fixture tests and deterministic engine tests do not replace this evidence.
