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

### Defined deterministic workloads

The repository currently defines these provider-free baseline workloads:

- `api.analysis_read.deterministic` — `GET /api/v1/analysis/COMI`, 10 measured repetitions, 2 warmups.
- `application.analysis_history.deterministic` — `GetAnalysisHistory.execute("COMI")`, 10 measured repetitions, 2 warmups, empty-history path.
- `application.stock_analysis.deterministic` — `StockAnalysisPipeline.analyze`, 16 deterministic daily bars, two financial periods, momentum/volume lookbacks of 5, 10 measured repetitions, 2 warmups.

The analysis-computation workload intentionally excludes provider/network calls and measures the deterministic technical analysis, fundamental analysis, scoring, entry-context, and opportunity-classification path.

These are workload definitions and harnesses; **no measured baseline values are claimed until the script is actually executed in the target repository environment**.

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
