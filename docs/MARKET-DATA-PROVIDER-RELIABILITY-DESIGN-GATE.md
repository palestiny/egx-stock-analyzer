# Market Data Provider Reliability — Design Gate

**Status:** GAP — lifecycle-domain bar contract exists, but the provider-source adapter, production finality verifier, and freshness proof are not implemented or approved  
**Reviewed:** 2026-11-13  
**Related:** DEC-135, DEC-138, DEC-139, `docs/PROJECT-COMPLETION-GAP-REGISTER.md`  
**Scope:** Eligibility of daily OHLC observations for lifecycle monitoring and downstream EGX opportunity state.

## 1. Executive finding

The accepted DEC-139 policy requires an adapter to attest all of the following before a daily bar can drive lifecycle transitions:

- daily timeframe;
- provider/source identity;
- source timestamp;
- final/complete status.

The generic application port `MarketDataProvider.get_daily_observations(...)` still returns only `RawPriceBarObservation` (stock ID, timeframe, timestamp, OHLC and volume), with no provider identity, finality/completion attestation, provider revision/correction identity, or retrieval timestamp. PR #515 defines `CompletedDailyBarObservation` at the lifecycle domain boundary and a provider-neutral `CompletedDailyBarSource` port plus `ProviderDailyBarEvidence` envelope. Both `EvaluateCompletedDailyBar` and `EvaluateOpportunityLifecycleSessions` now require the complete envelope; bare bars fail closed and the finality-verifier protocol receives the envelope. The envelope is persisted with the lifecycle observation in the same SQLite unit-of-work transaction, including provider ID, contract version, instrument symbol, Cairo session date, source timestamp, and retrieval timestamp. SQLite deserialization reconstructs the typed evidence, while older rows without the field remain readable. Tests verify restart durability and that idempotent re-fetch does not rewrite the original retrieval timestamp. However, no provider-specific adapter implements the new source port, no production verifier is composed in runtime, and no independently verified provider evidence proves the contract fields. The current Yahoo adapter still maps rows into the raw type; requesting `interval="1d"` does not prove finality or commercial rights.

The current `DataQualityAssessor` rejects missing, non-finite/non-positive OHLC, invalid/future timestamps and OHLC inconsistency, and marks duplicate identities as suspect. It does not classify an otherwise valid observation as stale relative to an expected completed EGX session. Therefore the current quality assessment is not the DEC-139 completed-session eligibility gate.

**Conclusion:** do not connect the current generic provider port or Yahoo adapter to automatic lifecycle monitoring. Keep monitoring disabled.

## 2. Verified current implementation boundary

| Concern | Current code evidence | What is not proven |
|---|---|---|
| Daily interval | Yahoo history client requests `interval="1d"`. | A returned row is final, complete, or immune to later correction. |
| Source identity | Yahoo adapter exposes class-level `source_name`; the provider-neutral lifecycle envelope carries provider ID and contract version through evaluation and SQLite observation persistence. | A real provider adapter must establish that the ID/version accurately identify the source contract. |
| Source timestamp | Raw observation has a timestamp; naive Yahoo timestamps are currently assigned UTC. | Provider timezone semantics for EGX daily bars or a reliable session-date mapping. |
| Lifecycle contract | `CompletedDailyBarObservation` plus `ProviderDailyBarEvidence` are wired through both evaluation use cases and the finality-verifier protocol; the complete envelope is durably persisted with each eligible observation. | No adapter bridges `MarketDataProvider` raw rows to the new source port; no production verifier or independent provider evidence exists. |
| Freshness | Data-quality assessor rejects future timestamps. | Expected-session coverage, STALE classification, or chronological cursor reconciliation. |
| Corrections | Acquisition records exist separately. | Stable provider candle identity/revision and append-only correction reconciliation at lifecycle boundary. |
| Commercial rights | Existing gap register records the Yahoo reuse restriction. | Permission for paid/subscriber redistribution or commercial API use. |

## 3. Design requirements

Any provider capable of driving lifecycle transitions must return a typed observation envelope or equivalent contract containing:

1. **Provider identity:** stable provider ID and adapter/contract version. The current lifecycle value carries provider name but not a separately versioned provider contract.
2. **Instrument identity:** EGX instrument/symbol mapping used for the request.
3. **Timeframe:** explicit daily timeframe; intraday observations must not satisfy daily eligibility.
4. **Session identity:** explicit EGX session date in `Africa/Cairo`, derived according to verified provider semantics—not by guessing from a UTC timestamp.
5. **Source timestamp:** original provider timestamp and its documented timezone/meaning.
6. **Retrieved-at timestamp:** timezone-aware timestamp recorded by our system, distinct from the source timestamp. The current `observed_at` field is not yet explicitly named or contractually separated as a retrieval timestamp.
7. **Finality attestation:** explicit provider capability/result indicating whether the bar is final/complete, including the basis and relevant contract/version. Unknown must fail closed. The current domain value requires `is_final=True`, but that assertion is only trustworthy once an approved adapter/verifier validates it against provider evidence.
8. **Revision identity:** stable provider candle key plus revision/correction identifier where the source supports it. The current domain value has a revision string and source reference, but their provider-specific stability/meaning is not established.
9. **OHLCV payload:** finite and positive OHLC, coherent high/low, non-negative volume, with the existing validation retained.
10. **Provenance:** durable linkage from evaluation to provider, provider contract version, source timestamp, retrieval timestamp, session date, calendar version, and observation identity. The provider-neutral lifecycle path now persists these envelope fields; provider-specific semantics and authenticity still require external documentation.

Do not add a boolean `is_final=True` merely because a local clock is later than the expected close. A local delay buffer is scheduling policy, not evidence of provider finality.

## 4. Freshness and lifecycle eligibility

The eligibility decision should be a separate application/domain policy, not folded into generic OHLC validation.

For a requested evaluation:

- Resolve the expected session from the explicitly active calendar version only after the calendar activation gate is approved.
- Require an explicit CLOSED session with timezone-aware `closed_at`.
- Require the evaluation to occur after the configured close buffer.
- Require one eligible daily observation for the same instrument and session date.
- Require source identity, daily timeframe, source timestamp semantics, and finality attestation to pass.
- Validate OHLC before evaluating target/invalidation.
- If the expected session lacks an eligible observation at its scheduled evaluation, persist STALE and suppress market-level transitions.
- Reconcile missing sessions chronologically from a durable cursor. Stop at the first required gap; do not advance the cursor past it.
- Treat later provider corrections as append-only reconciliation records; never silently rewrite an earlier evaluation.
- Make duplicate delivery idempotent using provider + instrument + timeframe + session/candle identity + provider revision (or an explicitly approved fallback identity).

The 60-minute buffer in DEC-139 is an operational scheduling default. It does not replace the provider's completion guarantee.

## 4A. Provider discovery snapshot — 2026-11-13

A provider discovery review is recorded in `docs/EGX-MARKET-DATA-PROVIDER-DISCOVERY-2026-11-13.md`.

Preliminary result:
- **EGID is the priority research candidate (no outreach authorized)**: its official website states it is wholly owned by EGX and the sole authorized EGX market-data provider; its product page lists historical prices, EOD reports, real-time Level 1/2, and a 15-minute delayed feed. Its public API UI lists symbol-history and market-status endpoints.
- This is not provider approval. Public materials do not establish machine-verifiable daily-bar finality, revision/correction semantics, or the exact commercial rights required by this application.
- **ICE Data Services** is the enterprise fallback to request a technical specification and quote for EGX EOD/history and API delivery.
- **DataCedar** is research-only under its published default terms: its API docs say the bars are not a consolidated exchange feed, and its terms restrict redistribution/third-party access absent a separate written agreement.
- **EGXAPI** is not eligible for reliance while its public Terms page labels itself a design draft with placeholder legal text.
- **EGX.news** remains unverified for authority, provenance, finality and redistribution rights.

No credentials were available during this review. No external contact with EGID or any other provider is authorized at this time. Continue provider-neutral contract and fail-closed verification internally. Provider outreach, selection, adapter implementation, and lifecycle activation require separate explicit owner authorization and the evidence checklist in the discovery report.

## 5. Provider selection and commercial boundary

A provider may be technically eligible for private/local analysis yet commercially ineligible for a paid or subscriber-facing product. Keep these as separate gates:

- **Technical gate:** documented EGX coverage, timestamp semantics, finality guarantees, correction behavior, rate limits, and availability.
- **Legal/commercial gate:** explicit contractual permission for the intended commercial API use, storage, caching, display, and redistribution to subscribers.

Yahoo Finance/yfinance remains ineligible for subscriber-facing redistribution absent verified applicable terms and written permission. Do not interpret successful API responses or CI tests as commercial authorization.

## 6. Required verification before provider production approval

- Provider-neutral contract and evaluation tests prove provider identity, contract version, timeframe, source timestamp, retrieved-at, session mapping and finality are present and timezone-correct; SQLite restart tests prove envelope durability.
- Unknown/unsupported finality fails closed.
- A provisional/incomplete bar cannot trigger or invalidate a signal.
- A stale expected session produces STALE and suppresses transitions.
- Missing expected session blocks cursor progression and later-session evaluation.
- A provider correction creates a new reconciliation record without mutating prior evidence.
- Duplicate provider delivery is idempotent; a distinct provider revision is not incorrectly discarded.
- Invalid OHLC is retained as rejected evidence with a reason and cannot drive transitions.
- Same-bar target/invalidation ambiguity follows the already accepted DEC-138 rule.
- Restart recovery processes eligible sessions in chronological order and stops at gaps.
- End-to-end tests cover a real provider adapter contract fixture, calendar version linkage, durable cursor, lifecycle events and alert outbox.

## 7. Decisions still required

This document records requirements and current gaps; it does not select a commercial provider or invent provider guarantees.

1. Select a provider only after obtaining its written technical documentation and commercial terms.
2. Decide whether providers lacking stable correction/revision IDs are rejected or accepted under a weaker, explicitly documented reconciliation policy.
3. Confirm the provider-specific mapping into the already-persisted provider-neutral envelope after the selected provider contract is known; any future schema change requires its own migration review.
4. Approve the calendar activation/coverage policy before connecting session-date eligibility to a live scheduler.

## 8. Current gate result

**GAP — do not enable lifecycle monitoring, Crash Radar freshness enforcement, or automated signal-state transitions using the current generic provider port.** The provider-neutral evidence envelope is now integrated through both lifecycle evaluation use cases and durably persisted in append-only SQLite observations; restart and idempotent-retrieval behavior are tested. The provider-specific adapter, production finality verifier, independently verified provider finality/correction/timestamp semantics, and commercial-use rights remain open. Continue provider-neutral work only; do not fabricate `is_final=True`. M61 remains paused as explicitly requested.
