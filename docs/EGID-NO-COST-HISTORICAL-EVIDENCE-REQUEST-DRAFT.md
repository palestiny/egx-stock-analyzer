# EGID No-Cost Historical Evidence Request — Draft

**Status:** Internal preparation only — not sent, not an acquisition commitment, and not source acceptance  
**Prepared:** 2026-11-11  
**Decision gate:** DEC-130  
**Preferred route:** EGX-owned distribution entity (EGID), subject to confirmation of the correct legal/contact channel  
**Project:** EGX Stock Analyzer  
**Canonical archive:** `data/market_history/egx_daily_history.csv`

## 1. Purpose and strict boundaries

Prepare a narrowly scoped inquiry to determine whether EGID can provide a small, authorized, no-cost sample of official EGX daily market data and explain the terms under which it may be evaluated.

This document does **not** authorize:
- sending this inquiry or contacting EGID;
- selecting a provider, subscribing, paying, or accepting a commercial offer;
- requesting or issuing credentials, API keys, tokens, or authenticated access;
- downloading, scraping, ingesting, or retaining a production dataset;
- creating a production adapter or changing source metadata;
- changing canonical CSV values or row dispositions;
- promoting source authenticity or analysis eligibility;
- unblocking or activating M61/backtesting.

Any external contact, access request, agreement, or next step requiring credentials or payment needs explicit user approval first. If no free and sufficiently documented route exists, stop without incurring cost.

## 2. Suggested inquiry (copy/edit only after approval)

**Subject:** Request for a small no-cost sample and technical documentation for EGX daily historical market data

Dear EGID Team,

We are evaluating whether an officially authorized EGX market-data source can support a reproducible research project focused on daily historical market observations.

Before considering any integration or commercial arrangement, could you please clarify whether EGID can provide a small **no-cost, non-production sample** of daily market data, together with the documentation needed to interpret and verify it?

If possible, the sample should include a small number of named instruments and sessions, including 4 and 5 November 2026 where available, plus unaffected control sessions. We are investigating historical OHLC discrepancies and do not want to infer or substitute values without authoritative evidence.

We would appreciate information on:

1. **Source identity and authority**
   - EGID's legal identity and relationship to EGX.
   - Whether the supplied records are official exchange records, an authorized distribution of those records, or another representation.
   - The authoritative reference (such as an official daily report or exchange publication) against which a sample can be independently checked.

2. **Sample and coverage**
   - Whether a small sample can be supplied without charge and without creating an account or issuing credentials.
   - Available dates, instruments, equities/index coverage, and symbol identifiers.
   - Whether the sample can include the 4–5 November 2026 sessions and a few control sessions, subject to availability.
   - Whether the sample is raw/as-published, corrected, adjusted, delayed, or otherwise transformed.

3. **Raw format and field definitions**
   - A machine-readable sample (CSV, JSON, or another documented format), preserving the original supplied values.
   - Field dictionary, instrument identifiers, units, currency, decimal precision, and null/missing-value conventions.
   - EGX trading-session timezone and the meaning of session date.
   - Definitions and units for volume, traded value, number of executions, and any index-specific fields.

4. **Timestamps, corrections, and revisions**
   - Distinction between market/session timestamp, publication timestamp, retrieval timestamp, and any update timestamp.
   - Whether records carry revision identifiers or version history.
   - How corrections, cancellations, restatements, and late updates are announced and represented.
   - Whether an earlier as-published version can be distinguished from a later corrected version.

5. **Price adjustment policy**
   - Whether prices are unadjusted/as-traded or adjusted.
   - Treatment of splits, dividends, rights issues, capital changes, and other corporate actions.
   - Whether adjusted and unadjusted series are separately available and clearly labelled.

6. **Rights and permitted use**
   - Whether the sample may be retained locally for internal research, audit, reproducibility, and comparison with official publications.
   - Whether derived calculations and non-redistributable research outputs are permitted.
   - Any restrictions on retention duration, copying, publication, redistribution, or commercial use.
   - The applicable written terms or license before any data is retained or used beyond initial inspection.

7. **Cost and access requirements**
   - Confirmation of whether the sample and documentation are available at zero cost.
   - Any fees, minimum commitments, recurring charges, or usage limits for broader access, stated separately from the sample.
   - Whether any account, authentication, API key, contract, or personal/business information is required.

At this stage, we are only requesting information and, if available, a small no-cost sample. We are not authorizing a paid subscription, credentials, production access, redistribution, or any ongoing commitment.

Thank you for your time.

Kind regards,  
EGX Stock Analyzer project

## 3. Minimum sample acceptance checklist

Do not treat a sample as usable evidence until all applicable items below are answered and recorded.

| Area | Minimum evidence required | Failure disposition |
|---|---|---|
| Provider identity | Verifiable legal entity and documented relationship/authority | Do not authenticate source |
| Provenance | Clear statement of whether values originate from EGX official records | Source authenticity remains unverified |
| Instrument identity | Stable identifiers and symbol mapping, including equity/index distinction | Do not compare ambiguous instruments |
| Session semantics | EGX session date and timezone definition | Mark not comparable |
| Raw payload | Original machine-readable bytes or file, with receipt metadata and locally computed checksum | Diagnostic only; preserve limitations |
| OHLC | Open, high, low, close, units, precision, null rules | No field-level confirmation if undefined |
| Other measures | Explicit definitions/units for volume, value, executions | Keep unavailable fields missing |
| Adjustment | Explicit adjusted/unadjusted convention and corporate-action policy | Do not combine incompatible series |
| Publication/retrieval | Separate source publication/update and local retrieval timestamps where available | Do not claim point-in-time availability |
| Revisions | Correction policy, revision identifiers/history, cancellation behavior | Historical point-in-time integrity unproven |
| Coverage | Exact dates, instruments, gaps, and exclusions | No extrapolation beyond supplied sample |
| Rights | Written permission for intended retention, internal research, audit, and derived outputs | Do not retain/use beyond permitted inspection |
| Cost | Explicit zero-cost confirmation for the proposed sample and documentation | Stop; no paid route assumed |
| Access | No credentials or authenticated access without explicit approval | Do not request or create credentials |

## 4. Targeted diagnostic sample

If EGID agrees and the sample is free and permitted, request a deliberately small set rather than a bulk export:

- A subset of the 30 OHLC geometry exceptions recorded for 2026-11-04 and 2026-11-05.
- Include both equity and index examples where the provider's field definitions support comparison.
- Include unaffected control rows from the same sessions and a small number of adjacent sessions.
- Include the exact exchange instrument identifiers and any official daily-report references.
- Ask for the complete original response/file and its publication or revision metadata, not a manually retyped table or screenshot alone.

The sample must be compared field-by-field under `docs/EGX-DAILY-HISTORY-RECONCILIATION-PROTOCOL.md`. A matching close or geometrically valid OHLC tuple is not enough to authenticate the other fields.

## 5. Evidence preservation if a sample is later approved

Only after written terms permit receipt and local retention:

1. Preserve the original received bytes unchanged.
2. Record who supplied it, the channel, date/time received, stated publication time, and any declared version.
3. Compute and record a SHA-256 digest; never replace the original artifact with a normalized copy.
4. Store parsed/normalized comparisons separately from the original.
5. Record symbol/session mapping, units, timezone, adjustment convention, and all missing fields.
6. Compare the sample to the canonical archive without editing the archive.
7. Assign per-row dispositions using the existing reconciliation protocol; keep unresolved cases unresolved.
8. Obtain explicit review before proposing any canonical-data correction or source/eligibility change.

## 6. Decision outcomes

- **STOP — no free route:** no no-cost sample/documentation is available; do not subscribe or seek paid access.
- **STOP — authority unclear:** EGID identity, provenance, or exchange relationship cannot be verified.
- **STOP — rights unclear:** intended retention/research use is not explicitly permitted in writing.
- **DIAGNOSTIC ONLY:** sample is useful for investigating selected rows but coverage, revisions, or rights are insufficient for historical backtesting.
- **ELIGIBLE FOR DEC-130 REVIEW:** all source, provenance, coverage, revision, point-in-time, and rights evidence is available for a separate formal review. This is not automatic acceptance.

## 7. Current project constraints

- The canonical archive remains unchanged and must remain unchanged during this inquiry.
- The known 51 OHLC geometry exceptions and 19 source/revision conflicts remain unresolved.
- Localized Investing.com pages are one provider family and do not constitute independent corroboration.
- DataCedar remains a candidate only; it is not accepted as an authoritative historical source.
- DEC-130 remains the mandatory gate; M61/backtesting remains paused.
- PR #321 remains Draft/unmerged.
- No provider selection, paid plan, credentials, ingestion, production adapter, eligibility promotion, or M61 activation is authorized.

## 8. Approval record

| Decision | State |
|---|---|
| Prepare this internal draft | Completed |
| Approve external contact | Not approved |
| Send inquiry | Not sent |
| Receive or retain sample | Not authorized |
| Request credentials/authenticated access | Not authorized |
| Accept provider or dataset | Not approved |
| Activate M61 | Blocked by DEC-130 |

**Next action:** user review and explicit approval are required before any external contact.