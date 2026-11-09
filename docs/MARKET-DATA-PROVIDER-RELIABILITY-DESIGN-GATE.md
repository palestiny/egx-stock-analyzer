# Market Data Provider Reliability — Design Gate

**Status:** GAP — provider finality and freshness contract is not implemented or approved at code level  
**Reviewed:** 2026-11-09  
**Related:** DEC-135, DEC-138, DEC-139, `docs/PROJECT-COMPLETION-GAP-REGISTER.md`  
**Scope:** Eligibility of daily OHLC observations for lifecycle monitoring and downstream EGX opportunity state.

## 1. Executive finding

The accepted DEC-139 policy requires an adapter to attest all of the following before a daily bar can drive lifecycle transitions:

- daily timeframe;
- provider/source identity;
- source timestamp;
- final/complete status.

The current application port `MarketDataProvider.get_daily_observations(...)` returns only `RawPriceBarObservation`. That value carries stock ID, timeframe, timestamp, OHLC and volume, but no provider identity, finality/completion attestation, provider revision/correction identity, or retrieval timestamp. The current Yahoo adapter requests `interval="1d"` and maps rows into this structure; this code behavior does not prove a bar is final or commercially redistributable.

The current `DataQualityAssessor` rejects missing, non-finite/non-positive OHLC, invalid/future timestamps and OHLC inconsistency, and marks duplicate identities as suspect. It does not classify an otherwise valid observation as stale relative to an expected completed EGX session. Therefore the current quality assessment is not the DEC-139 completed-session eligibility gate.

**Conclusion:** do not connect the current generic provider port or Yahoo adapter to automatic lifecycle monitoring. Keep monitoring disabled.

## 2. Verified current implementation boundary

| Concern | Current code evidence | What is not proven |
|---|---|---|
| Daily interval | Yahoo history client requests `interval="1d"`. | A returned row is final, complete, or immune to later correction. |
| Source identity | Yahoo adapter exposes class-level `source_name`. | Identity is carried with each persisted observation/evaluation. |
| Source timestamp | Raw observation has a timestamp; naive Yahoo timestamps are currently assigned UTC. | Provider timezone semantics for EGX daily bars or a reliable session-date mapping. |
| Finality | No final/completed flag or attestation appears in `MarketDataProvider` or `RawPriceBarObservation`. | Provider guarantees a bar is complete after EGX close + 60 minutes. |
| Freshness | Data-quality assessor rejects future timestamps. | Expected-session coverage, STALE classification, or chronological cursor reconciliation. |
| Corrections | Acquisition records exist separately. | Stable provider candle identity/revision and append-only correction reconciliation at lifecycle boundary. |
| Commercial rights | Existing gap register records the Yahoo reuse restriction. | Permission for paid/subscriber redistribution or commercial API use. |

## 3. Design requirements

Any provider capable of driving lifecycle transitions must return a typed observation envelope or equivalent contract containing:

1. **Provider identity:** stable provider ID and adapter/contract version.
2. **Instrument identity:** EGX instrument/symbol mapping used for the request.
3. **Timeframe:** explicit daily timeframe; intraday observations must not satisfy daily eligibility.
4. **Session identity:** explicit EGX session date in `Africa/Cairo`, derived according to verified provider semantics—not by guessing from a UTC timestamp.
5. **Source timestamp:** original provider timestamp and its documented timezone/meaning.
6. **Retrieved-at timestamp:** timezone-aware timestamp recorded by our system, distinct from the source timestamp.
7. **Finality attestation:** explicit provider capability/result indicating whether the bar is final/complete, including the basis and relevant contract/version. Unknown must fail closed.
8. **Revision identity:** stable provider candle key plus revision/correction identifier where the source supports it. If unavailable, document the limitation and do not claim correction-safe replay.
9. **OHLCV payload:** finite and positive OHLC, coherent high/low, non-negative volume, with the existing validation retained.
10. **Provenance:** durable linkage from evaluation to provider, source timestamp, session date, calendar version, and observation identity.

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

## 5. Provider selection and commercial boundary

A provider may be technically eligible for private/local analysis yet commercially ineligible for a paid or subscriber-facing product. Keep these as separate gates:

- **Technical gate:** documented EGX coverage, timestamp semantics, finality guarantees, correction behavior, rate limits, and availability.
- **Legal/commercial gate:** explicit contractual permission for the intended commercial API use, storage, caching, display, and redistribution to subscribers.

Yahoo Finance/yfinance remains ineligible for subscriber-facing redistribution absent verified applicable terms and written permission. Do not interpret successful API responses or CI tests as commercial authorization.

## 6. Required verification before lifecycle integration

- Contract tests prove provider identity, timeframe, source timestamp, retrieved-at, session mapping and finality are present and timezone-correct.
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
3. Approve the exact persisted observation envelope and schema migration after the selected provider contract is known.
4. Approve the calendar activation/coverage policy before connecting session-date eligibility to a live scheduler.

## 8. Current gate result

**GAP — do not enable lifecycle monitoring, Crash Radar freshness enforcement, or automated signal-state transitions using the current provider port.** Continue provider-neutral contract/design work and test fixtures only. M61 remains paused as explicitly requested.
