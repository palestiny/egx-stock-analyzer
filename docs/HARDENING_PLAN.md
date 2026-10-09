# Engineering hardening and operations guide

**Policy:** Pause new product capabilities and nonessential infrastructure expansion until M61 has an accepted real historical dataset and a reproducible evaluation. Security and operational defects may still be fixed.

## Current hardening status

- PR #240 — immutable SQLite research-dataset persistence; CI passed before merge.
- PR #241 — indexed SHA-256 lookup for newly issued high-entropy bearer tokens and process-local failed-authentication throttling; CI passed before merge.
- PR #242 — shared SQLite connection configuration with WAL and a 5-second busy timeout; CI passed before merge.
- PR #245 — UTC timestamps for market-data conflict events; CI passed before merge.
- PR #246 — race-safe first-time WAL initialization; concurrency regression tests and CI passed before merge.
- PR #243 — Python 3.12 test coverage, Ruff critical/datetime lint, scoped mypy, 85% unit-test coverage floor, dependency audit, and Cairo market-date helper; CI passed before merge.
- PR #247 — container baseline, explicit CORS configuration, trusted-proxy handling, and financial disclaimer; API/frontend container builds and CI passed before merge.
- PR #269 — optional Caddy HTTPS production overlay with domain/ACME configuration; Caddy validation, Compose validation, and container builds passed.
- PR #270 — expanded mypy to the full `app/api` package; fixed optional-authenticator narrowing and aligned market-analysis API test doubles with the typed application result contract. Ruff, mypy, unit tests, integration tests, frontend checks, dependency audit, and bounded container/Nginx validation passed.
- PR #272 — expanded mypy to all 207 Python source files under `app`; fixed 31 typing findings across persistence, scheduling, authorization, data-quality, signal, backtest, and runtime composition boundaries. Ruff, full-application mypy, unit/integration tests, frontend checks, dependency audit, and container validation passed.
- PR #248 — removal of 47 unused imports and enforcement of Ruff F401; CI passed before merge.
- PR #258 — Nginx security headers, hidden-file denial, request-size/read/send bounds, and upstream timeouts; container CI passed.
- PR #259 — extracted scheduled-workflow history queries from the SQLite persistence store; all CI checks passed.
- PR #261 — extracted user management, credential rotation, and audit endpoints into a dedicated router; all CI checks passed.
- PR #262 — extracted market-intelligence and signal endpoints into a dedicated router; all CI checks passed.
- PR #264 — extracted scheduled-workflow listing, history, and recovery endpoints; all CI checks passed. The API composition module was reduced from roughly 950–980 lines to about 583 lines.
- PR #252 — shared Nginx per-client API throttling, bounded in-process authentication limiter state, SQLite WAL reader/writer regression coverage, and backup/restore smoke test; CI passed before merge.
- PR #253 — enable the full Ruff F-rule family alongside critical E and timezone rules; moved two accidentally misplaced simulator tests out of production code, restored their test discovery, corrected their warmup expectations, and fixed the missing `user_management` runtime exposure; CI passed on Python 3.12, with frontend, integration, container-build, and dependency-audit jobs successful.
- PR #255 — add frontend ESLint and `npm audit --audit-level=high`; upgrade the vulnerable transitive `source-map-js` lock entry from 1.2.1 to patched 1.2.2; remove frontend lint errors around effect-driven loading and unused globals/imports. CI passed on Python 3.12, frontend lint/tests/build, integration tests, container builds, and Python dependency audit; unit suite reported 966 passed, 7 deselected, with 91.06% coverage.
- PR #276 — M61 data validation hardening: corrected the 252-session warm-up range, distinct-session counts, Cairo-local CSV timestamps, fail-closed provider response validation, and canonical OHLCV/financial numeric checks. CI passed: 988 unit tests, 91.07% coverage, integration tests, frontend checks, dependency audit, and container builds.
- PR #277 — M61 acceptance hardening: explicit license attestations for both market and financial sources, supported corporate-action conventions, point-in-time financial availability coverage for each 2021–2025 evaluation year, and duplicate daily-session rejection across timestamp offsets. CI passed.

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

The default Compose stack is loopback-bound HTTP for local use. An optional `compose.production.yaml` overlay now provides a Caddy TLS edge with automatic certificate management. Set `EGX_DOMAIN` to a public DNS name pointing to the server and `ACME_EMAIL` to an operator email, then open inbound TCP 80/443 (and UDP 443 for HTTP/3) in the host firewall:

```powershell
$env:EGX_OPERATOR_TOKEN = "<long-random-secret>"
$env:EGX_DOMAIN = "stocks.example.com"
$env:ACME_EMAIL = "ops@example.com"
docker compose --file compose.yaml --file compose.production.yaml up --build -d
```

Caddy terminates HTTPS and redirects HTTP to HTTPS. The API remains internal to Compose. The frontend Nginx trusts `X-Real-IP` only from the Caddy container's fixed address on the production Compose network, so per-client API throttling keeps the originating client IP. The production overlay reserves `172.30.0.0/24`; verify that this subnet does not conflict with the host's existing networks before deployment. CI validates both Compose configurations and the Caddyfile, but cannot verify your DNS, firewall, or certificate issuance.

Do not expose the API container directly to the internet. If using another external TLS proxy instead of the supplied Caddy overlay, follow that proxy's trusted-client-IP configuration and do not enable `EGX_TRUST_PROXY_HEADERS` unless the API can only be reached through a proxy that overwrites `X-Real-IP`.



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
- **Production perimeter:** default local Compose remains HTTP-only and loopback-bound; `compose.production.yaml` adds an optional Caddy HTTPS edge. Public deployment still requires a real domain, correct DNS, reachable ports 80/443, host/firewall restrictions, secret management, and operational monitoring. The Nginx limit is per instance and needs tuning for expected traffic.
- **Operational recovery:** SQLite WAL, timeout, concurrency behavior, and a backup/restore smoke test are covered. A production operator still needs scheduled backups and a tested restore drill on the actual deployment volume.
- **License:** no license was added because choosing the legal reuse terms requires the repository owner's explicit decision.
- **Maintainability:** scheduled-workflow API routes have been split into focused market-intelligence, user-management/audit, and scheduled-workflow router modules; workflow history queries are separated from the main SQLite store. `app/infrastructure/persistence/sqlite_scheduled_workflow_execution_store.py` remains a larger persistence module; defer further decomposition until the M61 evidence gate is closed to avoid diverting effort from dataset acceptance. Sequential decision records are retained for traceability; overlapping hardening guidance was consolidated.
- **Type-check scope:** CI now runs mypy across all of `app` (207 Python source files) with the current incremental strictness options. This catches type errors across the application but is not equivalent to strict mypy mode; stricter configuration can be introduced incrementally after the M61 evidence gate.

## License decision remains open

No software license has been selected. A public GitHub repository without an explicit license does not automatically grant general reuse rights. The repository owner must choose the intended license before advertising the project for external reuse or distribution.

## M61 evidence gate remains open

No production Strategy v0 performance claim is permitted until the required historical market and point-in-time financial artifacts pass source, coverage, provenance, adjustment, missing-data, survivorship, and reproducibility acceptance. Fixture tests and deterministic engine tests do not replace this evidence.

### Historical data acquisition path (candidates, not approvals)

1. **Request a direct EGX data-service quotation and license.** The official EGX website exposes market-watch and index information, but the public pages alone do not establish a bulk historical export right or a redistribution license. Ask EGX for daily OHLCV and corporate-action-adjusted history, the point-in-time universe/listing status, point-in-time financial statements and disclosures, delivery format, historical depth, price, and permitted research/product use. Do not scrape the public website as a substitute for a written data agreement.
2. **Commercial fallback: ICE Data Services.** ICE's EGX catalog advertises daily historical data from February 2012 and end-of-day/historical delivery through its data products. Coverage, corporate actions, point-in-time fundamentals, pricing, and redistribution rights must be confirmed in a written quote before acceptance.
3. **Secondary commercial candidate: EGX.news.** Its public data page advertises daily historical OHLCV for EGX listings and minute-level CSV data. It is not the exchange itself. Treat it only as a candidate until vendor identity, sample quality, provenance, coverage, correction policy, and explicit contractual rights for research, storage, backtesting, and any intended product use are verified.
4. **Yahoo/yfinance remains development-only.** It is not an accepted source for the evidence gate or a redistribution fallback unless current terms and the intended use are explicitly confirmed to permit it.

Reference pages reviewed on 2026-10-09:
- Official EGX market watch: https://beta.egx.com.eg/en/market/market-watch
- ICE EGX data catalog: https://developer.ice.com/fixed-income-data-services/catalog/egyptian-exchange-egx
- EGX.news advertised data offering: https://www.egx.news/en/our-data

### Automated M61 acceptance report semantics

The COMI intake gate counts unique Cairo-local trading dates, requires at least 252 distinct sessions before 2021, and checks the 2021–2025 evaluation window. The acquisition probe requests history from 2019-01-01 so the warm-up requirement is achievable; 2020-01-01 remains the latest acceptable first-coverage date.

The loader rejects non-finite values, non-positive prices, inconsistent OHLC, negative volume, and duplicate daily sessions even when timestamps use different offsets. Timestamp-aware vendor CSVs are normalized to the Cairo session date; timezone-naive timestamps are rejected.

For the automated licensing attestation, each market and financial source's `licensing_notes` must explicitly follow this semicolon-separated form:

```text
status=verified; evidence_reference=<contract-or-terms-reference>; permitted_uses=local_storage,historical_research,backtesting; redistribution=allowed
```

Use `redistribution=prohibited` when raw-data redistribution is not permitted. The reference records the owner-reviewed terms; the code cannot independently determine legal permission from prose. Commercial display/product rights must be reviewed separately before product use. Corporate-action convention must be one of `raw-as-published`, `unadjusted`, `split-adjusted`, `split-and-dividend-adjusted`, `total-return-adjusted`, or `vendor-adjusted`.

Point-in-time financial evidence must include snapshots with `available_at` in each evaluation year 2021–2025. A period-end date alone is not proof that the information was publicly available then. This year-level check is a minimum gate, not a guarantee that every daily decision has a fresh financial snapshot.

### Minimum acceptance checklist

- Obtain a written license/terms record covering local storage, historical research, derived outputs, and whether raw data may be redistributed or displayed to end users.
- Reconcile a stratified sample against an authoritative source across liquid/illiquid names, corporate actions, suspensions, symbol changes, delisted names, and abnormal sessions.
- Record provider, acquisition time, source timestamp semantics, original file hashes, dataset version, symbol mapping, coverage gaps, adjustment policy, and every correction/re-import.
- Check OHLCV validity, duplicate/out-of-order bars, missing sessions, timezone/session boundaries, splits/dividends, and survivorship/look-ahead risks. Preserve unknowns as explicit quality states rather than silently repairing them.
- Specify the point-in-time fundamentals/disclosure source separately; today's financial snapshots must not be backdated into historical strategy tests.
- Run the frozen Strategy v0 with next-open execution, fees/slippage, an appropriate benchmark, no-lookahead tests, out-of-sample/rolling periods, and a reproducible report. Publish no profitability claim until this review passes.

**Status:** no vendor has been approved, no licensed dataset has been accepted, and no Strategy v0 performance claim is authorized. The next operational action is a vendor quotation/sample request; this cannot be completed truthfully by code changes alone.


## Python runtime baseline

The project targets Python 3.12 only for now (`requires-python >=3.12,<3.13`), matching the production container and the validated CI baseline. Python 3.13 support can be restored later as an explicit compatibility decision with its own CI matrix; it is not claimed today.
