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
| CI | Missing dependency consistency, compile, static correctness gates | High | **Implemented; verified on latest CI** |
| API composition | `app/api/main.py` is oversized | Medium | **In progress: authentication + workflow route adapters extracted** |
| Historical evidence | Real M61 dataset/provenance validation remains the primary evidence gap | Critical | In progress via M61 gates/PRs |
| Backtesting | Real-cohort validation is not yet established | Critical | Blocked on accepted historical evidence |
| Security | Add operational hardening without changing auth semantics | Medium | **Implemented; verification in CI** |
| Performance | No measured latency/throughput baseline | Medium | **Protocol defined; measurement pending** |
| Scalability | Synchronous market-wide execution is the current ceiling | Medium/Future | Planned after measurement |
| Persistence | Mutation + management-audit atomicity was not proven | High | **Implemented; current CI verification pending** |
| Frontend | Backend contracts are more mature than UI operational experience | Medium | Planned |
| Documentation | Architecture/decision records are strong; remediation tracking needed | Medium | **Implemented** |

## Guardrails

1. Preserve the modular-monolith boundary.
2. Do not introduce microservices, queues, Kubernetes, Redis, or PostgreSQL without evidence and a design gate.
3. Do not change production analytical semantics as part of infrastructure hardening.
4. Do not claim Strategy v0 performance validation until the historical dataset passes provenance, point-in-time, integrity, and reproducibility checks.
5. Every destructive/data-affecting change requires deterministic tests and explicit lifecycle semantics.

## Current verification note

The last verified remediation CI run (#3177) passed unit, integration, frontend, and quality gates before the latest persistence-transaction changes. Current-branch CI verification is still required. Observability/security-header and authentication-adapter regression coverage are included in the remediation branch. Performance measurement is still pending; the baseline protocol has been documented but no benchmark result is being treated as evidence yet.

## Next execution order

1. Verify the atomic management mutation + audit transaction boundary in current CI.
2. Complete API composition-root decomposition without changing endpoint contracts.
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

### Authentication fail-closed hardening

- Legacy test composition is now recognized only while pytest is executing (`PYTEST_CURRENT_TEST` is present).
- A production composition with omitted authentication configuration no longer silently authenticates every request as the operator; the HTTP adapter returns `503 Authentication is not configured`.
- Explicit authentication configuration remains unchanged.
- Credential storage tests now verify that issued secrets are not stored as plaintext, old secrets become invalid after rotation, and verifier-only persistence remains intact.
