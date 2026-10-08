# Deployment baseline and production checklist

## Container baseline

The root `Dockerfile` builds the FastAPI API on Python 3.12, runs as a non-root user, and stores SQLite data under `/data`. `frontend/Dockerfile` builds the React application and serves static assets with Nginx. `compose.yaml` connects the frontend to the API on an internal Compose network and publishes only the frontend HTTP port.

From PowerShell, set a strong operator token in the current environment before starting Compose:

```powershell
$env:EGX_OPERATOR_TOKEN = "<replace-with-a-long-random-secret>"
docker compose up --build -d
```

The frontend is available at `http://localhost:8080` by default. The data database persists in the `egx-data` volume. Do not commit real credentials or a populated `.env` file.

## TLS and reverse proxy

This Compose stack serves HTTP only. It is suitable for local validation or for operation behind a trusted TLS-terminating reverse proxy. Do not expose it directly to the public internet without HTTPS, host-level firewall rules, request-size/time limits, access logs, and trusted proxy configuration. The API is not published to the host by default. Compose enables `EGX_TRUST_PROXY_HEADERS=true` because the API is only reachable through the frontend Nginx service, which overwrites `X-Real-IP`. Do not enable this flag if untrusted clients can reach the API directly or if the proxy does not overwrite that header.

The API's failed-authentication limiter is process-local. In multi-worker or multi-instance deployments, add shared rate limiting at the trusted edge. If the API is placed behind a proxy, do not blindly trust forwarded headers; configure the server to trust only the actual proxy addresses.

## CORS

Same-origin frontend/API routing is the default. For a separately hosted frontend, set `EGX_CORS_ALLOWED_ORIGINS` to a comma-separated list of exact origins (scheme + host + optional port), for example `https://dashboard.example.com`. Wildcard origins are rejected because credentials are enabled. CORS is a browser policy, not an authentication or authorization control.

## Operational checks before public use

- Rotate any default/development credentials; use a long, random secret from a secret manager.
- Restrict host and network access and terminate TLS at a trusted proxy.
- Confirm backup/restore for the SQLite volume and periodically test restore.
- Monitor disk capacity, application logs, authentication failures, and dependency alerts.
- Set an explicit origin allowlist if cross-origin browser access is needed.
- Validate data-provider terms and source quality separately; containerization does not certify market data or analytical results.
- Do not treat research scores or backtests as guarantees of returns.

## License decision remains open

No software license has been selected. A public GitHub repository without an explicit license does not automatically grant general reuse rights. The repository owner must choose the intended license before advertising the project for external reuse or distribution.
