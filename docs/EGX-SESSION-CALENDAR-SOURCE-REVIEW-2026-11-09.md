# EGX Session Calendar — Source Review

**Reviewed:** 2026-11-09  
**Decision status:** Research only; no provider or calendar dataset approved for automatic ingestion.

## Executive conclusion

The available public evidence reviewed here does not establish a verified, authoritative, machine-readable EGX trading-session calendar with complete historical and forward coverage, per-date provenance, and correction history. Several third-party candidates expose calendar-shaped data, but none reviewed here supplies sufficient independently verifiable EGX provenance and exception handling to replace operator confirmation.

Keep the DEC-139 operator-maintained, versioned calendar as the operational source of truth. Do not derive exchange sessions by copying Egyptian national holidays, applying weekday rules, or importing an unverified third-party calendar. The versioned domain model deliberately requires an explicit record for every covered date.

## Sources reviewed

### 1. Egyptian Presidency — National Holidays 2026

URL: https://www.presidency.eg/EN/مصر/العطلات-الرسمية/

The Presidency publishes Egypt's national public-holiday dates for 2026. This is a primary government source for national holidays, but it is not an EGX trading-session calendar. It does not establish exchange-specific closures, shortened sessions, auctions, or exceptional EGX notices. It must not be used alone to generate NON_TRADING records.

### 2. EGX session-hours evidence — conflicting secondary reproductions of exchange notices

- Ramadan schedule: https://en.amwalalghad.com/egx-sets-ramadan-trading-hours/
- Ramadan notice reproduced by Sigma Capital as source EGX: https://www.sigma-cap.com/main/news_page_exact?newsId=45851908&newsType=EGX
- Post-Ramadan return report: https://alborsaanews.com/2026/03/23/1956430
- Reported extension approval: https://arabfinance.com/en/news/newdetails/egx-to-extends-trading-hours-after-eid-el-fitr

The February 17, 2026 report attributes the Ramadan schedule to EGX: discovery at 09:30, main session 10:00–13:30, closing auction beginning 13:15, and closing-price trading through 13:30. Sigma Capital reproduces a notice labelled as sourced from EGX. A March 23 report says the post-Ramadan main session returned to 10:00–14:30. Separately, a February 12 report quotes the EGX chairman as saying an extension to 09:30–15:00 had been approved for after Eid. These reports do not, by themselves, resolve whether 09:30–15:00 describes the full trading-day envelope, an approved change later revised, or another session definition.

This is a material warning against hard-coding one session-close time. The official notice and the exact meaning of the session boundary used for daily-bar completion must be retained before publication.

### 3. Mansa API — third-party calendar candidate

URL: https://mansaapi.com/docs

The public documentation describes GET /api/v1/markets/calendar/{exchange_code} as returning a full exchange trading calendar with session times, timezone, trading days, settlement cycle, and public holidays. The documentation labels the full calendar endpoint Starter tier and above, while an is-open endpoint is described as free. API access uses a Bearer key.

This is a candidate for a controlled source-evaluation exercise, not an approved authority. The reviewed public documentation does not establish, for EGX specifically, the underlying official source per date, the completeness of exceptional/shortened sessions, correction history, or a contractual freshness guarantee. Do not auto-import or activate its calendar without obtaining and independently reconciling an actual EGX response and its provenance.

### 4. Market-Holidays Exchange Calendar — third-party snapshot

URL: https://market-holiday.com/markets/egx

The page identifies EGX and Africa/Cairo, displays a dataset snapshot dated August 4, 2026, and reports a regular continuous session of 10:00–14:15. The page distinguishes its dataset snapshot from the official venue as the authority for current schedules. This is useful as a comparison source, not as the source of truth. Its published hours and holiday list must be reconciled against actual EGX notices before use.

### 5. Secondary reports reproducing EGX holiday notices — conflict examples

These reports are useful leads to the underlying EGX announcements, but they are not the original exchange notices:

- **25 January / Police Day:** a Sigma Securities page dated January 26 reports that EGX moved the exchange holiday to Thursday, January 29 instead of Sunday, January 25. A separate CalendarLabs listing still shows January 25 as the EGX closure. The Presidency's national-holiday page lists January 29. Do not treat a third-party holiday row as sufficient evidence of the actual exchange closure.
  - Sigma Securities: https://www.sigmasecurities.com.eg/main/news_page_exact?newsId=45830271&newsType=EGX
  - CalendarLabs: https://www.calendarlabs.com/egx-market-holidays-2026/
- **Armed Forces Day:** a Sigma Capital page dated October 5 reports that EGX moved the exchange holiday to Thursday, October 8 instead of Tuesday, October 6. The Market-Holidays dataset snapshot lists October 6 as the full closure. This is a concrete freshness/reconciliation failure in the third-party snapshot.
  - Sigma Capital: https://sigmacapital.com.eg/main/news_page_exact?newsId=46118692&newsType=EGX&u_sess=%27
  - Market-Holidays: https://market-holiday.com/markets/egx/holidays/2026
- **Labor Day:** Mubasher reports that Thursday, May 7 was the EGX holiday and trading resumed Sunday, May 10.
  - Mubasher: https://english.mubasher.info/news/4606991/Labor-Day-Holiday-at-EGX/
- **Prophet Mohamed's Birthday:** MondoVisione reproduces an EGX holiday announcement for Thursday, August 27, with trading resuming Sunday, August 30; the Market-Holidays dataset lists August 26.
  - MondoVisione: https://mondovisione.com/media-and-resources/news/prophet-mohameds-birthday-mawled-el-nabi-holiday-at-egx-2026824/

These are secondary reproductions and should be used to locate/cross-check the original EGX notices, not to bypass them. The mismatches show that copying a national holiday list or an undated third-party calendar into production can shift the expected session date and invalidate freshness calculations.

### 5. IsOpenNow open dataset — not an EGX candidate in the reviewed snapshot

URL: https://isopennow.com/data/exchanges.v1.json

The reviewed dataset identifies itself as version 1.8.0, updated 2026-09-05, under CC BY 4.0. Its provenance explicitly states that it is secondary, not authoritative for any date, and compiled partly from `exchange_calendars`. The published 33-exchange snapshot contains no Egypt/EGX entry. It therefore cannot supply the EGX calendar for this project. Its explicit provenance warning is useful: do not build a new calendar from a compilation that may itself derive from another compilation.

## Risks and required evidence

- National public holidays and exchange trading closures are not interchangeable.
- Secondary sources can report different session hours or closure dates. The reviewed material includes a reported 09:30–15:00 post-Ramadan extension, a later report of a 10:00–14:30 main session, and a third-party page showing 10:00–14:15 continuous trading. A mismatch must be resolved from the underlying EGX notice, not by majority vote.
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
- The current legacy operator credential resolves to the shared subject `operator`; the audit actor is not an individually attributable human. Do not treat this as personal operator accountability. Named operator identities with an explicit operator permission are a separate authentication/authorization requirement before operational use.
- Do not activate a calendar through HTTP until the operational coverage horizon is explicitly defined and validated.
- Do not enable lifecycle monitoring until the DEC-139 provider-completion attestation, freshness gate, persistence, and recovery requirements also pass.
