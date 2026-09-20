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
- FastAPI analysis/report/alert/market/opportunity/history/workflow endpoints;
- multi-user bearer authentication, credential lifecycle, and ownership authorization;
- management and user-facing audit reporting;
- React + Vite dashboard;
- durable analysis results and historical analysis snapshots with SQLite;
- scheduled workflow state and lifecycle history with SQLite;
- bounded workflow history queries including state/time filters and cross-execution history;
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

## Authentication

`GET /health` remains public. Application endpoints use the current multi-user bearer-authentication boundary.

The current identity/credential architecture includes authenticated internal user UUIDs, durable opaque bearer credentials, user lifecycle state, credential rotation, and ownership-scoped application capabilities. The legacy operator compatibility path remains limited to system/global records.

The frontend establishes its browser session through the authenticated API; the old build-time `VITE_OPERATOR_TOKEN` flow is no longer the current frontend contract.

Raw credentials are not stored in domain entities or returned after provisioning/rotation. See the M39–M41 decisions in `docs/DECISION_LOG.md`.

## Analysis Flow

The dashboard reads stored analysis. It does not trigger a new analysis.

To request analysis through the API:

```powershell
$headers = @{ Authorization = "Bearer $env:EGX_OPERATOR_TOKEN" }
Invoke-RestMethod -Method Post http://localhost:8000/api/v1/analysis/EGAL -Headers $headers
```

Then read the persisted report:

```powershell
Invoke-RestMethod http://localhost:8000/api/v1/reports/EGAL -Headers $headers
```

And the alert candidate projection:

```powershell
Invoke-RestMethod http://localhost:8000/api/v1/alerts/EGAL -Headers $headers
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

Vite proxies `/api` requests to `http://localhost:8000`. The frontend follows the current authenticated session contract and does not own authorization or analytical rules.

## Persistence Contract

SQLite is the first durable persistence implementation.

The MVP stores:

- stock symbol;
- analysis date;
- serialization version;
- complete serialized `StockAnalysisResult`.

Latest-result compatibility remains available while historical analysis snapshots are also persisted through the historical-result boundary.

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

The detailed milestone state is maintained in `docs/ROADMAP.md`.

Current position:

- M47 — Scheduled Workflow History Filtering: complete.
- M48 — Scheduled Workflow History Time Filtering + Cross-Execution History: active.
- M48 time filtering: merged.
- M48 cross-execution history design: accepted.
- M48 cross-execution history implementation: merged through PR #118.
- PR #118 implementation head `babd5935c76a01752e8fb2d32536eb7d42c55769` passed GitHub Actions Run #1959.
- M48 merge commit: `ef387e2570d01653f4d231aea4527a18d3ded80c`.

Do not use older README milestone statements as project state. The roadmap and decision log are authoritative.

