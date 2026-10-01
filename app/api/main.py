from __future__ import annotations

import logging
import os

from fastapi import Depends, FastAPI, HTTPException

from app.api.observability import RequestObservabilityMiddleware

from app.api.alert_routes import register_alert_routes
from app.api.market_analysis_routes import register_market_analysis_routes
from app.application.analysis.get_market_opportunity_ranking import GetMarketOpportunityRanking
from app.application.analysis.result_store import AnalysisResultStore
from app.api.authentication import ApiAuthentication
from app.api.workflow_routes import register_workflow_routes
from app.api.analysis_routes import register_analysis_routes
from app.application.analysis.get_analysis_result import GetAnalysisResult
from app.application.analysis.run_stock_analysis_by_symbol import RunStockAnalysisBySymbol
from app.application.reporting.get_analysis_history import GetAnalysisHistory
from app.application.reporting.get_analysis_report import GetAnalysisReport
from app.api.analysis_report_response import AnalysisReportResponse
from app.api.analysis_lifecycle_routes import register_analysis_lifecycle_routes
from app.application.analysis.get_analysis_run import GetAnalysisRun
from app.application.analysis.list_analysis_runs import ListAnalysisRuns
from app.application.analysis.delete_analysis_run import DeleteAnalysisRun
from app.application.analysis.delete_analysis_snapshot import DeleteAnalysisSnapshot
from app.api.management_routes import register_management_routes
from app.api.comparison_routes import register_comparison_routes
from app.application.security.authentication import Authenticator
from app.application.security.identity import AuthenticatedIdentity, Permission
from app.application.analysis.run_configured_market_analysis import RunConfiguredMarketAnalysis
from app.application.reporting.get_alert_candidate import GetAlertCandidate
from app.application.notifications.deliver_alert_by_symbol import (
    AlertCandidateNotFoundError,
    DeliverAlertBySymbol,
)

logger = logging.getLogger(__name__)


class _OperatorTokenNotProvided:
    pass


_OPERATOR_TOKEN_NOT_PROVIDED = _OperatorTokenNotProvided()


def create_app(
    result_store: AnalysisResultStore,
    run_stock_analysis_by_symbol: RunStockAnalysisBySymbol | None = None,
    get_analysis_report: GetAnalysisReport | None = None,
    get_alert_candidate: GetAlertCandidate | None = None,
    get_market_opportunity_ranking: GetMarketOpportunityRanking | None = None,
    run_configured_market_analysis: RunConfiguredMarketAnalysis | None = None,
    get_analysis_history: GetAnalysisHistory | None = None,
    compare_analysis_snapshots: CompareAnalysisSnapshots | None = None,
    calculate_snapshot_performance: CalculateSnapshotPerformance | None = None,
    deliver_alert_by_symbol: DeliverAlertBySymbol | None = None,
    get_scheduled_workflow_executions: GetScheduledWorkflowExecutions | None = None,
    get_scheduled_workflow_execution_history: GetScheduledWorkflowExecutionHistory | None = None,
    get_scheduled_workflow_history: GetScheduledWorkflowHistory | None = None,
    recover_durable_scheduled_workflow: RecoverDurableScheduledWorkflow | None = None,
    user_management: UserManagementService | None = None,
    get_management_audit: GetManagementAudit | None = None,
    operator_token: str | None | _OperatorTokenNotProvided = _OPERATOR_TOKEN_NOT_PROVIDED,
    authenticator: Authenticator | None = None,
    get_user_audit_history: GetUserAuditHistory | None = None,
    get_analysis_run: GetAnalysisRun | None = None,
    list_analysis_runs: ListAnalysisRuns | None = None,
    delete_analysis_run: DeleteAnalysisRun | None = None,
    delete_analysis_snapshot: DeleteAnalysisSnapshot | None = None,
) -> FastAPI:
    app = FastAPI(title="EGX Stock Analyzer API")
    app.add_middleware(RequestObservabilityMiddleware)
    get_analysis_result = GetAnalysisResult(result_store)
    legacy_test_composition = isinstance(operator_token, _OperatorTokenNotProvided) and authenticator is None
    configured_token = (
        None
        if isinstance(operator_token, _OperatorTokenNotProvided)
        else operator_token if operator_token is not None else os.getenv("EGX_OPERATOR_TOKEN")
    )
    api_authentication = ApiAuthentication(
        operator_token=configured_token,
        authenticator=authenticator,
        legacy_test_composition=legacy_test_composition,
    )
    register_analysis_routes(
        app,
        api_authentication=api_authentication,
        get_analysis_result=get_analysis_result,
        run_stock_analysis_by_symbol=run_stock_analysis_by_symbol,
        get_analysis_history=get_analysis_history,
        get_analysis_report=get_analysis_report,
    )
    register_analysis_lifecycle_routes(
        app,
        api_authentication=api_authentication,
        get_analysis_run=get_analysis_run,
        list_analysis_runs=list_analysis_runs,
        delete_analysis_run=delete_analysis_run,
        delete_analysis_snapshot=delete_analysis_snapshot,
    )

    @app.get("/health")
    def health() -> dict[str, str]:
        return {"status": "ok"}

    @app.get("/api/v1/auth/me")
    def get_authenticated_identity(
        identity: AuthenticatedIdentity = Depends(api_authentication.require_authenticated),
    ) -> dict[str, object]:
        return {
            "subject": identity.subject,
            "user_id": str(identity.user_id) if identity.user_id is not None else None,
            "status": identity.user_status.value if identity.user_status is not None else None,
        }

    register_market_analysis_routes(
        app,
        api_authentication=api_authentication,
        run_configured_market_analysis=run_configured_market_analysis,
        get_market_opportunity_ranking=get_market_opportunity_ranking,
    )

    register_comparison_routes(
        app,
        api_authentication=api_authentication,
        compare_analysis_snapshots=compare_analysis_snapshots,
        calculate_snapshot_performance=calculate_snapshot_performance,
    )

    register_management_routes(
        app,
        api_authentication=api_authentication,
        user_management=user_management,
        get_management_audit=get_management_audit,
        get_user_audit_history=get_user_audit_history,
    )

    register_workflow_routes(
        app,
        api_authentication=api_authentication,
        authenticator=authenticator,
        get_scheduled_workflow_executions=get_scheduled_workflow_executions,
        get_scheduled_workflow_execution_history=get_scheduled_workflow_execution_history,
        get_scheduled_workflow_history=get_scheduled_workflow_history,
        recover_durable_scheduled_workflow=recover_durable_scheduled_workflow,
    )

    register_alert_routes(
        app,
        api_authentication=api_authentication,
        deliver_alert_by_symbol=deliver_alert_by_symbol,
        get_alert_candidate=get_alert_candidate,
    )

    return app