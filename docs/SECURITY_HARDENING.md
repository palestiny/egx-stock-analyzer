# Authentication hardening and credential migration

## Indexed credential lookup

New durable bearer credentials are opaque 256-bit tokens. The database stores a SHA-256 verifier and resolves it through an index on `(status, verifier)`, avoiding a PBKDF2 operation for every active credential on every request. SHA-256 is appropriate here because the token is generated with high entropy; this choice must not be reused for human passwords.

## Existing PBKDF2 records

PBKDF2 verifier rows cannot be converted to SHA-256 without the original raw token. The compatibility scan is therefore disabled by default. During a controlled migration only, set `EGX_ALLOW_LEGACY_PBKDF2_CREDENTIALS=true`; each successfully authenticated legacy credential is upgraded to SHA-256. This compatibility mode re-enables an expensive scan for unknown tokens and should be temporary. Disable it after all active credentials have authenticated or been reissued.

If a deployment cannot tolerate existing sessions being rejected, enable the compatibility flag only behind upstream rate limiting and plan credential rotation. Do not expose a deployment with legacy fallback enabled directly to untrusted traffic.

## Failed-authentication throttling

The API temporarily blocks a client after 10 failed authentication attempts within 60 seconds and returns HTTP 429 with `Retry-After`. The limiter is process-local and is a defense-in-depth control, not a distributed lockout. Multi-worker/multi-instance deployments should also enforce limits at a trusted reverse proxy or shared rate-limit service. Do not trust forwarded client-IP headers unless the proxy chain is configured explicitly.

## Operational caveat

The project still needs a deployment-specific HTTPS/reverse-proxy configuration before being exposed to public traffic.
