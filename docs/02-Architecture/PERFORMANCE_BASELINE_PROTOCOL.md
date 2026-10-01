# Performance Baseline Protocol

**Status:** Design/measurement protocol — no optimization decision implied.

## Purpose

Establish reproducible evidence for the current modular monolith before changing persistence, execution, caching, worker, or deployment architecture.

## Required workloads

1. Single-symbol analysis: `GET /api/v1/analysis/{symbol}`
2. Single-symbol analysis execution: `POST /api/v1/analysis/{symbol}`
3. Market-wide configured analysis: `POST /api/v1/market-analysis`
4. Historical/read-heavy endpoints: analysis history, runs, reports, and opportunities
5. Backtest execution once an accepted historical dataset exists

## Metrics

Record at minimum:

- p50, p95, p99 latency
- requests/operations per second where applicable
- CPU utilization
- memory usage
- provider/network wait time when externally dependent
- error rate and timeout rate

Do not treat one cold run as a baseline. Warm up the application and dependencies first. For deterministic local workloads, use at least five measured repetitions and preserve the raw timings.

## Reproducibility

Every baseline record must include:

- repository commit SHA
- Python/runtime version
- dependency lock/state used for the run
- dataset and dataset version
- symbol cohort and date range
- endpoint/workload configuration
- machine/runtime environment
- measurement method
- raw timings and calculated percentiles
- whether external network/provider latency is included

Separate local computation time from external-provider time whenever the instrumentation allows it.

## Interpretation guardrails

A performance result is evidence about the measured workload, not a general capacity claim.

Do not introduce Redis, queues/workers, PostgreSQL, microservices, Kubernetes, or other distributed infrastructure solely because a workload feels slow. First identify the measured bottleneck, quantify its impact, and pass an architecture/design gate for the proposed change.

## Acceptance

The baseline is considered usable when another engineer can reproduce the same workload from the recorded commit, configuration, dataset, and method, with expected environmental variance explicitly documented.

No strategy-performance claim may use an unversioned or non-reproducible dataset.
