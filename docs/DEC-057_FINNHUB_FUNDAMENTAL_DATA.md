# DEC-057 — Finnhub Fundamental Data Adapter

## Status

Accepted and implemented on `m12-runtime-integration`.

## Context

`AnalysisInputAssembler` now depends on the `FundamentalDataProvider` boundary, but the project did not yet have an infrastructure implementation that could provide the two `FinancialPeriod` values required by `StockAnalysisInput`.

The immediate requirement is not to move financial-analysis rules into infrastructure. The requirement is to acquire and normalize reported financial data into the existing domain representation.

## Source investigation

### Mubasher

Mubasher clearly publishes EGX financial statements and company disclosures. Its financial-statement pages are useful as an Egyptian-market reference and its disclosure pages expose reported net-profit values.

However, the available public page evidence does not establish a stable documented API contract for all fields required by our current `FinancialPeriod`. In particular, the current domain requires revenue, while the Mubasher statement payload approach we investigated cannot be treated as a verified source for that field across companies.

Therefore we do **not** couple the first provider implementation to Mubasher scraping.

### Argaam

Argaam provides a documented Fundamentals API with historical financial statements, but its documented coverage is Saudi/GCC rather than EGX. It is therefore not an appropriate source for this project.

### Finnhub

Finnhub documents a standardized `/stock/financials` endpoint for global companies, with balance sheet (`bs`), income statement (`ic`) and cash flow (`cf`) statements and annual/quarterly frequencies. EGX symbols are represented with the `.CA` suffix, and independent EGX financial-data sites identify Finnhub as a source for EGAL.CA financial data.

This gives us a replaceable, documented adapter boundary without making Finnhub part of the domain.

## Decision

Implement `FinnhubFundamentalDataProvider` in infrastructure.

The adapter:

1. maps an EGX domain symbol such as `EGAL` to `EGAL.CA`;
2. requests standardized annual income statements and balance sheets;
3. selects periods whose end date is not later than `as_of`;
4. joins income and balance-sheet data by period end;
5. requires revenue and net income for a usable period;
6. keeps current assets/current liabilities optional because the domain already models them as optional;
7. returns the latest two usable periods in descending order.

## Explicit non-responsibilities

The adapter does **not**:

- calculate margins;
- calculate growth;
- calculate current ratio;
- score fundamentals;
- decide whether data is economically good or bad;
- persist data;
- perform HTTP/API work inside the domain layer.

## Authentication

Finnhub requires an API key. The runtime adapter reads `FINNHUB_API_KEY` when no explicit key is supplied.

The key must remain server-side and must never be committed to the repository.

## Trade-off

Using Finnhub gives us a documented, replaceable acquisition adapter and keeps the current domain model unchanged.

The trade-off is provider dependency and the need to verify actual EGX coverage and field completeness with Khaled's Finnhub account before making this the production default for all EGX symbols.

## Next step

Run the provider unit tests first. Then run one real EGAL acquisition using a locally configured `FINNHUB_API_KEY`. If EGAL returns the required two annual periods, wire this provider into `AnalysisInputAssembler` and then into the daily runtime.
