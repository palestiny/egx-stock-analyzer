# EGX Stock Analyzer

Python system for explainable analysis of Egyptian Exchange (EGX) stocks.

## Current Scope

The system currently supports:

- market and annual fundamental data acquisition through replaceable infrastructure providers;
- technical and fundamental analysis;
- technical/fundamental scoring;
- stock quality and entry quality;
- opportunity classification;
- automated analysis execution;
- analysis reports and alert-candidate projections;
- FastAPI analysis/report/alert endpoints;
- React + Vite dashboard;
- durable latest-analysis persistence with SQLite;
- a read-only SQLite inspection tool;
- CI for Python tests, frontend tests, and frontend production build.

## Architecture

The project is a domain-first modular monolith:

```text
React + Vite
    ↓ HTTP
FastAPI
    ↓
Application
    ↓
Domain
    ↓
Infrastructure
    ├── Yahoo Finance adapters
    └── SQLite analysis-result store
```

Persistence remains behind the application-facing `AnalysisResultStore` contract.

## Local Python Setup

From the repository root:

```powershell
python -m venv .venv
.\.venv\Scripts\Activate.ps1
python -m pip install --upgrade pip
pip install -e ".[dev]"
```

## Run the API

The default application composition uses the full infrastructure runtime and SQLite:

```powershell
uvicorn app.main:app --reload
```

The default analysis database is:

```text
storage/analysis.db
```

Override it with:

```powershell
$env:EGX_ANALYSIS_DATABASE_PATH="storage/custom-analysis.db"
```

## Analysis Flow

The dashboard reads stored analysis. It does not trigger a new analysis.

To request analysis through the API:

```powershell
Invoke-RestMethod -Method Post http://localhost:8000/api/v1/analysis/EGAL
```

Then read the persisted report:

```powershell
Invoke-RestMethod http://localhost:8000/api/v1/reports/EGAL
```

And the alert candidate projection:

```powershell
Invoke-RestMethod http://localhost:8000/api/v1/alerts/EGAL
```

A successful analysis is persisted to SQLite before the read-side report/alert projections use it.

## Inspect SQLite

The development inspector is read-only:

```powershell
python -m app.infrastructure.persistence.inspect_database
python -m app.infrastructure.persistence.inspect_database --symbol EGAL
```

It is a diagnostics tool, not part of the application/API boundary.

## Run Tests

Python unit/non-integration tests:

```powershell
pytest -m "not integration"
```

Frontend tests:

```powershell
cd frontend
npm ci
npm run test:run
npm run build
```

## Frontend Development

Start the API first, then:

```powershell
cd frontend
npm install
npm run dev
```

Vite proxies `/api` requests to `http://localhost:8000`.

## Persistence Contract

SQLite is the first durable persistence implementation.

The MVP stores:

- stock symbol;
- analysis date;
- serialization version;
- complete serialized `StockAnalysisResult`.

The latest completed result is kept per symbol. Historical result browsing is intentionally deferred.

The serializer is explicit and versioned; Python pickle is not used.

See:

- `docs/DEC-071-M13-DURABLE-ANALYSIS-STATE-BOUNDARY.md`
- `docs/DEC-072-M13-SQLITE-ANALYSIS-RESULT-PERSISTENCE-MVP.md`

## Engineering Rules

Major architecture and domain decisions are recorded in `docs/DECISION_LOG.md`.

The project follows:

```text
Understand
  ↓
Map
  ↓
Design
  ↓
Trade-offs
  ↓
Decide
  ↓
Document
  ↓
TDD RED → GREEN
  ↓
Review / Refactor
  ↓
Git Commit
  ↓
CI
```

New dashboard, persistence, scheduling, alert-delivery, ranking, authentication, or other major capabilities require an explicit design gate before implementation.

## Current Milestone State

- M12 — First API/dashboard slice: complete and frozen.
- M13 — Operational runtime baseline: complete.
- M13 — SQLite persistence MVP: complete and CI-validated.
- M30 — Durable scheduled workflow: complete and CI-validated through the recurring-scheduler integration.

M30 now persists scheduled workflow lifecycle state independently from analytical-result and alert-delivery persistence. Persisted RUNNING executions are detectable and recoverable as INTERRUPTED; they are not automatically replayed.

The next feature is not selected automatically. A new capability should begin with its own design gate rather than expanding an existing capability opportunistically.
