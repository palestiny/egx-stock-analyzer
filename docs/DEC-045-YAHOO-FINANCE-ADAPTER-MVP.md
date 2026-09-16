# DEC-045 — Yahoo Finance Adapter MVP

## Status

Accepted as a development/data-source adapter, not as the final production provider decision.

## Context

M3 needs a real provider adapter behind the provider-neutral `MarketDataProvider` port. Yahoo Finance has documented EGX usage in current open-source projects through symbols such as `COMI.CA`, but coverage is not guaranteed for every EGX symbol. Yahoo/yfinance access is also unofficial and subject to its applicable terms. citeturn1search0turn1search1

## Decision

Implement Yahoo Finance as the first concrete adapter for development and end-to-end integration testing.

The adapter:

- receives the domain `Stock` and date range;
- maps the EGX symbol to the provider symbol using a dedicated symbol-mapping boundary;
- requests daily OHLCV data;
- returns only `RawPriceBarObservation` objects;
- does not create `PriceBar`;
- does not run Data Quality rules;
- does not perform technical/fundamental analysis;
- does not make BUY/SELL decisions.

## Provider Status

Yahoo is explicitly **not** declared the permanent production provider.

Current evidence indicates:

- Yahoo can provide EGX symbols using provider-specific forms such as `COMI.CA`;
- coverage varies by symbol/provider;
- yfinance access is unofficial.

Therefore a later Provider Selection Gate must evaluate coverage, reliability, licensing/terms, historical depth, rate limits, and operational behavior before production adoption.

## Trade-off

Using Yahoo now gives us a concrete provider without coupling the domain to it. Delaying the final provider decision prevents a temporary source from becoming an architectural dependency.

## Deferred

- full EGX symbol coverage verification;
- production provider selection;
- provider failover;
- intraday data;
- provider-specific retry/rate-limit policy;
- corporate-action policy;
- licensing/redistribution decision.
