# Engineering Review Remediation Plan

**Baseline:** main @ cc0083c224b7cf40877aac3ba67cf5ae8d20ba5f  
**Remediation branch:** hardening/full-review-remediation  
**Review date:** 2026-10-01

## Objective

Convert the senior architecture review into an executable hardening backlog without rewriting the current modular-monolith architecture or changing analytical semantics without a design gate.

## Remediation status

| Area | Finding | Priority | Status |
| --- | --- | --- | --- |
| Observability | No first-class HTTP correlation/timing contract | High | **Implemented** |
| CI | Missing dependency consistency, compile, static correctness gates | High | **Implemented; latest run pending** |
| API composition | `app/api/main.py` is oversized | Medium | **In progress: authentication + workflow route adapters extracted** |
| Historical evidence | Real M61 dataset/provenance validation remains the primary evidence gap | Critical | In progress via M61 gates/PRs |
| Backtesting | Real-cohort validation is not yet established | Critical | Blocked on accepted historical evidence |
| Security | Add operational hardening without changing auth semantics | Medium | Planned |
| Performance | No measured latency/throughput baseline | Medium | Planned |
| Scalability | Synchronous market-wide execution is the current ceiling | Medium/Future | Planned after measurement |
| Persistence | SQLite is appropriate for current scale; PostgreSQL migration deferred | Medium/Future | Decision: defer |
| Frontend | Backend contracts are more mature than UI operational experience | Medium | Planned |
| Documentation | Architecture/decision records are strong; remediation tracking needed | Medium | **Implemented** |

## Guardrails

1. Preserve the modular-monolith boundary.
2. Do not introduce microservices, queues, Kubernetes, Redis, or PostgreSQL without evidence and a design gate.
3. Do not change production analytical semantics as part of infrastructure hardening.
4. Do not claim Strategy v0 performance validation until the historical dataset passes provenance, point-in-time, integrity, and reproducibility checks.
5. Every destructive/data-affecting change requires deterministic tests and explicit lifecycle semantics.

## Current verification note

The latest observed GitHub Actions run passed unit tests, dependency consistency, compilation, deterministic integration, and frontend checks; the quality job failed only on Ruff F821 findings in the existing backtesting test code. Those leaked tests were moved into a dedicated test module and a warmup regression test was added; the latest head has not yet produced a new PR-triggered Actions run. Code inspection identified missing `AuthorizationError`/`Permission` imports in `main.py` after the authentication extraction; those imports were restored and dedicated authentication-adapter regression tests were added. A new Actions run has not yet been observed for the latest commit, so the branch is not marked green.

## Next execution order

1. Complete API composition-root decomposition without changing endpoint contracts.
2. Add operational security hardening and regression coverage.
3. Establish latency/throughput benchmarks for analysis and market-wide execution.
4. Complete M61 historical dataset acquisition/validation and evidence manifest.
5. Run deterministic Strategy v0 backtests and leakage/reproducibility checks.
6. Reassess persistence and worker architecture only from measured workload evidence.
7. Re-score production readiness after validation.

## Explicit non-goals

- Microservices rewrite
- Distributed infrastructure before measured need
- Adding indicators solely to increase feature count
- Optimizing strategy parameters before a fixed validation protocol exists
- Treating provider smoke tests as historical evidence
