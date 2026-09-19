from contextlib import asynccontextmanager

from fastapi import FastAPI

from app.infrastructure.security.bearer_token_authenticator import BearerTokenAuthenticator

from app.api.main import create_app
from app.application.analysis.result_store import (
    AnalysisResultStore,
)
from app.application.execution.retry import RetryPolicy
from app.application.stocks.catalog import StockCatalog
from app.infrastructure.config import InfrastructureConfig
from app.infrastructure.runtime import (
    InfrastructureRuntime,
    create_infrastructure_runtime,
)
from app.infrastructure.stocks.development_catalog import create_development_stock_catalog


def create_application(runtime: InfrastructureRuntime) -> FastAPI:
    @asynccontextmanager
    async def lifespan(app: FastAPI):
        try:
            if runtime.automatic_workflow_recovery is not None:
                runtime.automatic_workflow_recovery.execute()
            yield
        finally:
            runtime.close()

    app = create_app(
        runtime.application_runtime.result_store,
        runtime.application_runtime.run_by_symbol,
        runtime.application_runtime.get_analysis_report,
        runtime.application_runtime.get_alert_candidate,
        runtime.application_runtime.get_market_opportunity_ranking,
        runtime.application_runtime.run_configured_market_analysis,
        runtime.application_runtime.get_analysis_history,
        runtime.application_runtime.compare_analysis_snapshots,
        runtime.application_runtime.calculate_snapshot_performance,
        runtime.deliver_alert_by_symbol,
        runtime.get_scheduled_workflow_executions,
        getattr(runtime, "recover_durable_scheduled_workflow", None),
        operator_token=getattr(runtime, "operator_token", None),
    )
    app.router.lifespan_context = lifespan
    return app


def create_application_from_environment(
    stock_catalog: StockCatalog,
    result_store: AnalysisResultStore | None = None,
    retry_policy: RetryPolicy | None = None,
) -> FastAPI:
    config = InfrastructureConfig.from_environment()
    BearerTokenAuthenticator(config.operator_token or "")

    import yfinance as yf

    runtime = create_infrastructure_runtime(
        stock_catalog=stock_catalog,
        yfinance_module=yf,
        config=config,
        result_store=result_store,
        retry_policy=retry_policy,
    )
    return create_application(runtime)


def create_development_application_from_environment(
    result_store: AnalysisResultStore | None = None,
    retry_policy: RetryPolicy | None = None,
) -> FastAPI:
    stock_catalog = create_development_stock_catalog()
    return create_application_from_environment(
        stock_catalog=stock_catalog,
        result_store=result_store,
        retry_policy=retry_policy,
    )


# Default development entry point uses the full infrastructure composition so local
# API/dashboard runs exercise the same durable SQLite result store as the runtime.
app = create_development_application_from_environment()
