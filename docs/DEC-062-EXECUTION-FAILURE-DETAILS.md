# DEC-062 — Execution Failure Details

**Status:** Accepted  
**Date:** 2026-09-18

## Context

The execution runner preserves whole-market execution semantics by recording a failed stock and continuing with other stocks. However, the failure boundary previously retained only the failed stock ID. A single-stock analysis could therefore surface only a generic execution failure even when the underlying exception contained useful diagnostic information.

## Decision

Execution records a lightweight failure reason per failed stock as diagnostic context.

The execution runner records the final exception message after retry attempts are exhausted. If a stock later succeeds, its previous failure reason is cleared.

The failure reason is diagnostic context, not a new business rule and not a replacement for structured observability/logging.

## Trade-offs

### Gain

- Failure diagnosis survives the execution boundary.
- Partial-failure behavior remains unchanged.
- Retry semantics remain unchanged.
- The API/application layer can provide a more useful diagnostic message for the current development runtime.

### Cost

- Exception messages are retained in execution state.
- Exception text is not a stable machine-readable error contract.
- Raw exception text must not be treated as a secure audit log or trusted production-facing diagnostic surface.

## Non-Goals

This decision does not introduce:

- logging infrastructure
- tracing
- metrics
- persistence
- provider-specific error categories
- a production error taxonomy

## Revisit Conditions

Revisit during M13 Production Hardening when structured observability and production-safe error handling are designed, or earlier if failures require machine-readable categories rather than human-readable diagnostic text.
