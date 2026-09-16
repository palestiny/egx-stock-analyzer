from fastapi import FastAPI

from app.api.main import create_app
from app.application.analysis.result_store import InMemoryAnalysisResultStore
from app.infrastructure.runtime import InfrastructureRuntime


def create_application(runtime: InfrastructureRuntime) -> FastAPI:
    return create_app(runtime.application_runtime.result_store)


# Temporary safe composition for the API-only development entry point.
# Infrastructure dependencies are intentionally not constructed at import time.
result_store = InMemoryAnalysisResultStore()
app = create_app(result_store)
