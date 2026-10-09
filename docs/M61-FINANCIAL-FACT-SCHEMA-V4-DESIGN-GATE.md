# M61 Financial Fact Schema v4 — Design Gate

**Status:** Proposed — awaiting owner approval before implementation  
**Date:** 2026-10-09  
**Scope:** Historical financial evidence in the M61 research dataset

## Problem

The current schema-v3 `financial_snapshots.csv` stores generic columns such as `revenue`, `net_income`, `current_assets`, and `current_liabilities`. It records the provider and a revision string, but it cannot preserve the accounting identity of each individual value: source metric label, consolidated/standalone scope, currency, reporting unit, or the exact source document.

That is not sufficient for the existing `FinancialMetric` domain contract, which explicitly requires metric code, source label, statement scope, currency, unit, and value. It is especially unsafe for banks: COMI reports banking-specific metrics such as net operating income and net interest income. The current Strategy v0 selector does not permit silently treating those as generic revenue.

**Consequences:** a source CSV can pass structural intake while still being semantically ineligible for Strategy v0. Do not accept a COMI financial artifact or publish Strategy v0 results until this mismatch is resolved.

## Recommended decision

Adopt schema v4 with a normalized, long-form `financial_facts.csv`: one row per stock, reporting period, availability event, and metric.

Proposed required columns:

```text
stock_id,period_end,available_at,metric_code,source_label,statement_scope,currency,unit,value,source,source_document_reference,source_document_sha256,revision
```

- `metric_code` is a controlled domain code; `source_label` preserves the provider's original accounting label.
- `statement_scope` is explicit (`consolidated` or `standalone`).
- `currency` and `unit` are mandatory; no implicit scaling or currency conversion.
- `available_at` remains a date unless an exact publication timestamp is proven. Date-only evidence stays eligible from the following calendar date.
- `source_document_reference` and `source_document_sha256` bind each normalized fact to its source evidence where retention is permitted. If raw documents cannot legally be stored, the manifest must record the permitted evidence reference and retention restriction instead of pretending the raw file is preserved.
- Duplicate metric facts for the same stock/period/availability/scope/revision are rejected unless a documented revision ordering rule resolves them.
- The source artifact and every transformation remain checksum-addressed and immutable.

## Alternatives considered

### A. Keep schema v3 and add per-column metadata

Add separate source label/scope/currency/unit columns for every numeric field.

**Pros:** smaller migration; still a single row per reporting period.  
**Cons:** rigid and repetitive; adding metrics changes the schema repeatedly; awkward for bank-specific metrics; easy to leave one field's metadata blank or misaligned with its value.

### B. Store a JSON metadata blob beside schema-v3 numeric columns

**Pros:** less CSV width and a smaller code change.  
**Cons:** weak column-level validation; difficult to query/review; metadata can drift from values; does not give each fact a first-class identity.

### C. Recommended — normalized long-form facts (schema v4)

**Pros:** each value carries its own accounting identity and provenance; supports bank/non-bank metrics without semantic substitution; explicit units/scope; easier to audit and extend.  
**Cons:** more rows; loader and provider adapter must group facts into periods; requires a schema migration and updated fixtures/tests.

## Compatibility and migration

- Schema v4 is required for M61 acceptance.
- Existing schema-v3 fixtures may remain loadable for legacy deterministic tests, but must be reported as `LEGACY_NOT_M61_ACCEPTABLE` by the acceptance gate. They must never be promoted to accepted real evidence.
- The candidate builder must emit v4 only after source CSV metadata is supplied and validated; it must not infer a metric code from a display label without an explicit reviewed mapping.
- The point-in-time provider may map only explicitly approved metric codes into the legacy `FinancialPeriod` contract. Unsupported metrics remain preserved in the dataset but are ineligible for Strategy v0.
- Strategy v0 must fail closed if required metrics are missing, unsupported, mixed across statement scope/currency/unit, or not available by the decision date.
- No existing raw artifact is rewritten in place. New normalized packages receive a new immutable dataset version.

## Acceptance criteria

1. Schema-v4 manifest and `financial_facts.csv` have strict exact headers, canonical values, deterministic ordering, row counts, and SHA-256 verification.
2. Each fact preserves metric code, original label, scope, currency, unit, source document reference/hash (subject to documented legal retention restrictions), availability date, and revision.
3. Tests reject unsupported metric codes, missing metadata, invalid/non-finite values, invalid availability dates, ambiguous duplicates, mixed scope/currency/unit, and source-document checksum mismatches.
4. Point-in-time selection cannot use a fact on or before a date-only `available_at`; it becomes eligible from the following calendar date.
5. The Strategy v0 adapter selects only explicitly accepted comparable metrics; it never substitutes net operating income/net interest income/net profit for generic revenue.
6. Schema-v3 fixture packages cannot pass M61 real-data acceptance.
7. A real COMI source artifact can be packaged, validated, and reported as `CANDIDATE_ONLY` without falsely claiming licensing or strategy validity.

## Owner decisions requested

Approve or reject the recommended schema-v4 long-form design before implementation.

If approved, implementation should proceed in this order:
1. domain fact model + v4 manifest/loader contract;
2. RED tests for semantic metadata and point-in-time selection;
3. candidate builder and COMI acceptance gate migration;
4. application adapter and Strategy v0 fail-closed behavior;
5. fixtures, docs, full CI;
6. only then ingest real COMI evidence and evaluate source-specific comparability.

## Explicit non-goals

This gate does not select a vendor, assert any source license, acquire data, approve a generic bank-revenue mapping, change Strategy v0's economic rules, or authorize performance claims.
