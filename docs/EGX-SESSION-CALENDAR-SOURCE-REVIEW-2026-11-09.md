# EGX Session Calendar — Source Review

**Reviewed:** 2026-11-09  
**Decision status:** Research only; no provider or calendar dataset approved for automatic ingestion.

## Executive conclusion

The available public evidence reviewed here does not establish a verified, authoritative, machine-readable EGX trading-session calendar with complete historical and forward coverage, per-date provenance, and correction history.

Keep the DEC-139 operator-maintained, versioned calendar as the operational source of truth. Do not derive exchange sessions by copying Egyptian national holidays, applying weekday rules, or importing an unverified third-party calendar. The versioned domain model deliberately requires an explicit record for every covered date.

## Sources reviewed

### 1. Egyptian Presidency — National Holidays 2026

URL: https://www.presidency.eg/EN/مصر/العطلات-الرسمية/

The Presidency publishes Egypt's national public-holiday dates for 2026. This is a primary government source for national holidays, but it is not an EGX trading-session calendar. It does not establish exchange-specific closures, shortened sessions, auctions, or exceptional EGX notices. It must not be used alone to generate NON_TRADING records.

### 2. Ramadan 2026 EGX hours — secondary reporting

URL: https://en.amwalalghad.com/egx-sets-ramadan-trading-hours/

A February 17, 2026 report attributes a Ramadan schedule announcement to EGX and describes a 09:30 discovery session and a 10:00–13:30 main trading session, plus auction and adjustment periods. This demonstrates why session hours must be date-specific and why a single annual default is unsafe. The report is secondary evidence; the underlying official EGX notice must be captured before an operator publishes those hours as authoritative.

### 3. Mansa API — third-party calendar candidate

URL: https://mansaapi.com/docs

The public documentation describes GET /api/v1/markets/calendar/{exchange_code} as returning a full exchange trading calendar with session times, timezone, trading days, settlement cycle, and public holidays. The documentation labels the full calendar endpoint Starter tier and above, while an is-open endpoint is described as free. API access uses a Bearer key.

This is a candidate for a controlled source-evaluation exercise, not an approved authority. The reviewed public documentation does not establish, for EGX specifically, the underlying official source per date, the completeness of exceptional/shortened sessions, correction history, or a contractual freshness guarantee. Do not auto-import or activate its calendar without obtaining and independently reconciling an actual EGX response and its provenance.

### 4. Market-Holidays Exchange Calendar — third-party snapshot

URL: https://market-holiday.com/markets/egx

The page identifies EGX and Africa/Cairo, displays a dataset snapshot dated August 4, 2026, and reports a regular continuous session of 10:00–14:15. The page distinguishes its dataset snapshot from the official venue as the authority for current schedules. This is useful as a comparison source, not as the source of truth. Its published hours and holiday list must be reconciled against actual EGX notices before use.

## Risks and required evidence

- National public holidays and exchange trading closures are not interchangeable.
- Secondary sources can report different session hours or closure dates; a mismatch must be resolved from the underlying EGX notice, not by majority vote.
- Normal, Ramadan, shortened, auction, and exceptional sessions must not be collapsed into one daily open/close pair unless the calendar contract explicitly represents the session relevant to daily-bar completion.
- A third-party endpoint is not authoritative merely because it exposes an EGX code or says it covers the exchange.
- Provider retrieval time, source-bar timestamp, scheduled close, and explicit confirmation that the exchange session is closed are separate facts.

Before approving an automated calendar source, require:
1. A real EGX calendar response covering a known historical period and a forward period.
2. Per-date timezone, open/close times, status, and source notice/reference.
3. Evidence of how shortened sessions and emergency closures are represented and corrected.
4. Data publication/update timestamps and a documented correction/revision policy.
5. Licensing and commercial-use terms suitable for this application.
6. Independent reconciliation against official EGX notices for a representative set of normal, Ramadan, holiday, and exceptional dates.

## Operational disposition

- Continue using the authenticated operator publication API for immutable calendar versions.
- Treat each published calendar as operator-asserted data with a calendar-level source reference; per-day provenance remains an open schema enhancement.
- Do not activate a calendar through HTTP until the operational coverage horizon is explicitly defined and validated.
- Do not enable lifecycle monitoring until the DEC-139 provider-completion attestation, freshness gate, persistence, and recovery requirements also pass.
