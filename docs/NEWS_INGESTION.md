# News ingestion and point-in-time event API

The news feature stores normalized metadata in SQLite and exposes authenticated event queries. The RSS/Atom adapter is provider-neutral; **it does not assume a feed is an official EGX disclosure just because an operator labels it that way**.

## Configure one approved feed

Set these environment variables for the API process:

- `EGX_NEWS_RSS_URL`: absolute HTTPS URL for a feed whose access and reuse terms have been verified.
- `EGX_NEWS_RSS_SOURCE_NAME`: human-readable source name (default: `Configured EGX News Feed`).
- `EGX_NEWS_RSS_SOURCE_TYPE`: one of `exchange_disclosure`, `regulator`, `central_bank`, `company_announcement`, `macroeconomic`, `financial_media`, or `other`. Default: `exchange_disclosure`.
- `EGX_ANALYSIS_DATABASE_PATH`: persistent SQLite database path (default: `storage/analysis.db`).

PowerShell example (replace the URL only after verifying feed availability, source attribution, licensing, and redistribution rights):

```powershell
$env:EGX_NEWS_RSS_URL = "https://REPLACE-WITH-VERIFIED-FEED-URL"
$env:EGX_NEWS_RSS_SOURCE_NAME = "Verified EGX disclosure feed"
$env:EGX_NEWS_RSS_SOURCE_TYPE = "exchange_disclosure"
$env:EGX_ANALYSIS_DATABASE_PATH = "storage/analysis.db"
```

Do not leave the placeholder URL in production. No source is enabled by default. The application uses the configured stock catalog's symbol/name mapping; matching is a heuristic and its confidence must not be treated as proof of entity identity.

## Ingest and query

Ingestion is an authenticated operator action:

```powershell
$headers = @{ Authorization = "Bearer $env:EGX_OPERATOR_TOKEN" }
Invoke-RestMethod -Method Post -Uri "http://localhost:8000/api/v1/news/ingest" -Headers $headers
```

An optional timezone-aware `since` query parameter limits ingestion to items published at or after that time. Example:

```powershell
Invoke-RestMethod -Method Post -Uri "http://localhost:8000/api/v1/news/ingest?since=2026-10-25T00:00:00Z" -Headers $headers
Invoke-RestMethod -Method Get -Uri "http://localhost:8000/api/v1/news/events?symbol=EGAL&limit=50" -Headers $headers
```

The GET endpoint supports symbol, timezone-aware `as_of`, minimum entity-match confidence, and bounded result count. It returns source/provenance timestamps and the original story URL, not the full article body.

## Data and safety rules

- RSS and Atom metadata are supported. The adapter uses bounded HTTPS retrieval, a timeout, a 2 MB response limit, and rejects DTD/entity declarations.
- Item title and summary/description may be inspected transiently for symbol matching and keyword category heuristics; the event store persists only the normalized title and metadata, not the body.
- Only timezone-aware publication timestamps qualify for point-in-time queries. Undated or timezone-naive entries are excluded when a `since` cutoff is requested and remain ineligible for as-of queries.
- Event IDs and content fingerprints are stable across re-polls. A replay with a newer retrieval time preserves the original `first_seen_at`; changed content for an existing event ID is rejected.
- Keyword categories and ticker/name matches are heuristics, not authoritative financial interpretation.
- Use only feeds you are permitted to access and use. Prefer the official EGX disclosure feed where access terms permit; supplement with reputable media, regulator, and CBE sources only after verifying each feed.

## Operational limits

The adapter enforces a 2 MB payload limit, a 0.1–60 second timeout bound, rejects DTD/entity declarations across the full payload, and processes at most 500 entries per poll. The current implementation supports explicit operator-triggered ingestion and authenticated querying. Automatic polling/scheduling, a verified EGX session calendar/data-finalization trigger, a market-wide post-session report, and Telegram delivery of that report are separate features and must not be represented as complete until implemented and tested. Live-source tests are intentionally excluded from deterministic CI.
