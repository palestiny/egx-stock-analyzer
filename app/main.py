from contextlib import asynccontextmanager

from fastapi import FastAPI

from app.api.main import create_app
from app.application.analysis.result_store import (
    AnalysisResultStore,
    InMemoryAnalysisResultStore,
)
from app.application.execution.retry import RetryPolicy
from app.application.stocks.catalog import StockCatalog
from app.infrastructure.config import InfrastructureConfig
from app.infrastructure.runtime import (
    InfrastructureRuntime,
    create_infrastructure_runtime,
)


def create_application(runtime: InfrastructureRuntime) -> FastAPI:
    @asynccontextmanager
    async def lifespan(app: FastAPI):
        yield
        runtime.close()

    app = create_app(
        runtime.application_runtime.result_store,
        runtime.application_runtime.run_by_symbol,
    )
    app.router.lifespan_context = lifespan
    return app


def create_application_from_environment(
    stock_catalog: StockCatalog,
    result_store: AnalysisResultStore | None = None,
    retry_policy: RetryPolicy | None = None,
) -> FastAPI:
    config = InfrastructureConfig.from_environment()

    import yfinance as yf

    runtime = create_infrastructure_runtime(
        stock_catalog=stock_catalog,
        yfinance_module=yf,
        config=config,
        result_store=result_store,
        retry_policy=retry_policy,
    )
    return create_application(runtime)


# Temporary safe composition for the API-only development entry point.
# Infrastructure dependencies are intentionally not constructed at import time.
result_store = InMemoryAnalysisResultStore()
app = create_app(result_store)
