# Configurable RSS/Atom news ingestion

This adapter stores normalized event metadata only. It does not persist article bodies, and it does not claim that an RSS feed is an official exchange disclosure unless the feed has been verified as such.

## Configure feeds

Set `EGX_NEWS_RSS_FEEDS` to a JSON array. Each item must have a unique `source_name`, an HTTPS `url`, and a `source_type` from the domain enum:

- `exchange_disclosure`
- `regulator`
- `central_bank`
- `company_announcement`
- `macroeconomic`
- `financial_media`
- `other`

Optional `timeout_seconds` defaults to 8 and is bounded between 0.1 and 60. Feed payloads are limited to 2 MB and at most 500 entries per poll.

PowerShell example (replace the URL only after verifying access terms, source reliability, and redistribution rights):

```powershell
$env:EGX_NEWS_RSS_FEEDS = '[{"source_name":"Verified EGX disclosure feed","url":"https://REPLACE-WITH-VERIFIED-FEED-URL","source_type":"exchange_disclosure","timeout_seconds":8}]'
$env:EGX_NEWS_SYMBOL_ALIASES = '{"EGAL":["Egypt Aluminum","مصر للألومنيوم"],"COMI":["Commercial International Bank","البنك التجاري الدولي"]}'
$env:EGX_ANALYSIS_DATABASE_PATH = "storage/analysis.db"
python -m app.infrastructure.news.ingest_rss_feeds
```

Do not leave the placeholder URL in a production environment. No source is enabled by default because feed availability, attribution, freshness, licensing, and redistribution rights must be verified before the application relies on it.

## Data and safety rules

- RSS and Atom metadata are supported; item title, canonical item URL, publication time, and GUID/ID are used.
- Only timezone-aware publication timestamps qualify for `since` filtering and point-in-time backtests. Undated or timezone-naive entries are retained only when no `since` cutoff is requested; the API's as-of query still excludes unknown publication times.
- `first_seen_at` records the first successful ingestion time. Replays with the same event ID may have a newer retrieval time, but the stored first-seen timestamp remains unchanged; changed event content for an existing ID is rejected.
- Symbol matching uses configured exact-token aliases. It is evidence with confidence, not a claim of verified entity identity.
- Event categories are keyword heuristics and must be treated as preliminary labels, not legal/financial interpretation.
- The fetcher requires HTTPS, uses a bounded timeout, and rejects payloads larger than 2 MB.
- Configure only feeds you are permitted to access and use. Prefer the official EGX disclosure feed where access terms permit; supplement with reputable media and regulator/CBE sources after verifying each feed.

## Operational status

The command is an explicit ingestion job. A scheduler, verified EGX calendar/data-finalization trigger, and operator dashboard for feed health are separate integration work; do not claim automatic background ingestion until those are configured and tested. Live-source integration tests are intentionally not part of deterministic CI.
