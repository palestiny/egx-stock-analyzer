import logging
import os
from dataclasses import asdict
from datetime import date, datetime
from uuid import UUID

from fastapi import Depends, FastAPI, Header, HTTPException

from app.api.alert_candidate_response import AlertCandidateResponse
from app.api.analysis_comparison_response import AnalysisComparisonResponse
from app.api.analysis_history_response import AnalysisHistoryResponse
from app.api.analysis_run_response import AnalysisRunResponse
from app.api.analysis_run_list_response import AnalysisRunListResponse
from app.api.analysis_snapshot_performance_response import AnalysisSnapshotPerformanceResponse
from app.api.alert_delivery_response import AlertDeliveryResponse
from app.api.analysis_report_response import AnalysisReportResponse
from app.api.analysis_response import AnalysisResultResponse
from app.api.market_analysis_execution_response import MarketAnalysisExecutionResponse
from app.api.management_audit_response import ManagementAuditResponse
from app.api.user_audit_history_response import UserAuditHistoryResponse
from app.api.market_opportunity_view_response import MarketOpportunityViewResponse
from app.api.scheduled_workflow_execution_history_response import ScheduledWorkflowExecutionHistoryResponse
from app.api.scheduled_workflow_history_response import ScheduledWorkflowHistoryResponse
from app.api.scheduled_workflow_execution_response import (
    ScheduledWorkflowExecutionResponse,
    ScheduledWorkflowExecutionsResponse,
)
from app.application.reporting.get_analysis_history import GetAnalysisHistory
from app.application.reporting.calculate_snapshot_performance import (
    AnalysisSnapshotPerformanceNotFoundError,
    CalculateSnapshotPerformance,
    InvalidSnapshotPerformanceError,
)
from app.application.reporting.compare_analysis_snapshots import (
    AnalysisSnapshotNotFoundError,
    CompareAnalysisSnapshots,
    InvalidSnapshotComparisonError,
)
from app.application.analysis.get_analysis_result import GetAnalysisResult
from app.application.analysis.list_analysis_runs import (
    InvalidAnalysisRunListQueryError,
    ListAnalysisRuns,
)
from app.application.analysis.get_analysis_run import (
    AnalysisRunNotFoundError,
    GetAnalysisRun,
    InvalidAnalysisRunQueryError,
)
from app.application.analysis.get_market_opportunity_ranking import GetMarketOpportunityRanking
from app.application.analysis.result_store import AnalysisResultStore
from app.application.security.authentication import (
    AuthenticationError,
    BearerTokenAuthenticator,
    ConfiguredBearerTokenAuthenticator,
    Authenticator,
)
from app.application.security.authorization import AuthorizationError, OperatorAuthorizer
from app.application.security.identity import AuthenticatedIdentity, Permission
from app.application.identity.get_management_audit import GetManagementAudit, InvalidManagementAuditPageSizeError
from app.application.identity.get_user_audit_history import (
    GetUserAuditHistory,
    InvalidUserAuditActionError,
    InvalidUserAuditPageSizeError,
)
from app.application.identity.user_management import UserManagementError, UserManagementService
from app.domain.identity.user import UserStatus
from app.domain.execution import ExecutionState
from app.application.analysis.run_configured_market_analysis import RunConfiguredMarketAnalysis
from app.application.execution.get_scheduled_workflow_history import (
    GetScheduledWorkflowHistory,
    InvalidScheduledWorkflowHistoryQueryError,
)
from app.application.execution.get_scheduled_workflow_execution_history import (
    GetScheduledWorkflowExecutionHistory,
    ScheduledWorkflowExecutionHistoryNotFoundError,
    InvalidScheduledWorkflowExecutionHistoryQueryError,
)
from app.application.execution.get_scheduled_workflow_executions import GetScheduledWorkflowExecutions
from app.application.execution.recover_durable_scheduled_workflow import (
    RecoverDurableScheduledWorkflow,
    WorkflowExecutionNotFoundError,
    WorkflowExecutionNotRecoverableError,
)
from app.application.analysis.run_stock_analysis_by_symbol import (
    RunStockAnalysisBySymbol,
    UnknownStockSymbolError,
)
from app.application.reporting.get_alert_candidate import GetAlertCandidate
from app.application.notifications.deliver_alert_by_symbol import (
    AlertCandidateNotFoundError,
    DeliverAlertBySymbol,
)
from app.application.reporting.get_analysis_report import GetAnalysisReport

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
) -> FastAPI:
    app = FastAPI(title="EGX Stock Analyzer API")
    get_analysis_result = GetAnalysisResult(result_store)
    legacy_test_composition = isinstance(operator_token, _OperatorTokenNotProvided) and authenticator is None
    configured_token = (
        None
        if isinstance(operator_token, _OperatorTokenNotProvided)
        else operator_token if operator_token is not None else os.getenv("EGX_OPERATOR_TOKEN")
    )
    operator_authenticator = BearerTokenAuthenticator(configured_token) if configured_token else None
    authorizer = OperatorAuthorizer()

    def require_authenticated(
        authorization: str | None = Header(default=None),
    ) -> AuthenticatedIdentity:
        if legacy_test_composition:
            return AuthenticatedIdentity.operator()
        if authenticator is None:
            if operator_authenticator is None:
                raise HTTPException(status_code=503, detail="Authentication is not configured")
            try:
                return operator_authenticator.authenticate(authorization)
            except AuthenticationError as error:
                raise HTTPException(
                    status_code=401,
                    detail="Authentication required",
                    headers={"WWW-Authenticate": "Bearer"},
                ) from error
        try:
            return authenticator.authenticate(authorization)
        except AuthenticationError as error:
            raise HTTPException(
                status_code=401,
                detail="Authentication required",
                headers={"WWW-Authenticate": "Bearer"},
            ) from error

    def require_operator(authorization: str | None = Header(default=None)) -> AuthenticatedIdentity:
        if legacy_test_composition:
            return AuthenticatedIdentity.operator()
        if authenticator is not None:
            try:
                identity = authenticator.authenticate(authorization)
                authorizer.require(identity, Permission.OPERATOR)
                return identity
            except AuthenticationError as error:
                raise HTTPException(
                    status_code=401,
                    detail="Authentication required",
                    headers={"WWW-Authenticate": "Bearer"},
                ) from error
            except AuthorizationError as error:
                raise HTTPException(status_code=403, detail="Forbidden") from error
        if operator_authenticator is None:
            raise HTTPException(status_code=503, detail="Authentication is not configured")
        try:
            identity = operator_authenticator.authenticate(authorization)
            authorizer.require(identity, Permission.OPERATOR)
            return identity
        except AuthenticationError as error:
            raise HTTPException(
                status_code=401,
                detail="Authentication required",
                headers={"WWW-Authenticate": "Bearer"},
            ) from error
        except AuthorizationError as error:
            raise HTTPException(status_code=403, detail="Forbidden") from error

    @app.get("/health")
    def health() -> dict[str, str]:
        return {"status": "ok"}

    @app.get("/api/v1/auth/me")
    def get_authenticated_identity(
        identity: AuthenticatedIdentity = Depends(require_authenticated),
    ) -> dict[str, object]:
        return {
            "subject": identity.subject,
            "user_id": str(identity.user_id) if identity.user_id is not None else None,
            "status": identity.user_status.value if identity.user_status is not None else None,
        }

    @app.get("/api/v1/management/audit")
    def get_management_audit_report(
        actor_user_id: UUID | None = None,
        target_user_id: UUID | None = None,
        action: str | None = None,
        outcome: str | None = None,
        from_time: datetime | None = None,
        to_time: datetime | None = None,
        page_size: int = 50,
        offset: int = 0,
        identity: AuthenticatedIdentity = Depends(require_operator),
    ) -> dict[str, object]:
        if get_management_audit is None:
            raise HTTPException(status_code=503, detail="Management audit reporting is not configured")
        try:
            page = get_management_audit.execute(
                identity,
                actor_user_id=actor_user_id,
                target_user_id=target_user_id,
                action=action,
                outcome=outcome,
                from_time=from_time,
                to_time=to_time,
                page_size=page_size,
                offset=offset,
            )
        except InvalidManagementAuditPageSizeError as error:
            raise HTTPException(status_code=400, detail=str(error)) from error
        except ValueError as error:
            raise HTTPException(status_code=400, detail=str(error)) from error
        return asdict(ManagementAuditResponse.from_page(page))

    @app.get("/api/v1/users/me/audit")
    def get_user_audit_history_report(
        action: str | None = None,
        outcome: str | None = None,
        from_time: datetime | None = None,
        to_time: datetime | None = None,
        page_size: int = 50,
        offset: int = 0,
        identity: AuthenticatedIdentity = Depends(require_authenticated),
    ) -> dict[str, object]:
        if get_user_audit_history is None:
            raise HTTPException(status_code=503, detail="User audit history is not configured")
        try:
            page = get_user_audit_history.execute(
                identity,
                action=action,
                outcome=outcome,
                from_time=from_time,
                to_time=to_time,
                page_size=page_size,
                offset=offset,
            )
        except InvalidUserAuditPageSizeError as error:
            raise HTTPException(status_code=400, detail=str(error)) from error
        except InvalidUserAuditActionError as error:
            raise HTTPException(status_code=400, detail=str(error)) from error
        except ValueError as error:
            raise HTTPException(status_code=400, detail=str(error)) from error
        return asdict(UserAuditHistoryResponse.from_page(page))


    @app.get("/api/v1/users")
    def list_users(_identity: AuthenticatedIdentity = Depends(require_operator)) -> dict[str, object]:
        if user_management is None:
            raise HTTPException(status_code=503, detail="User management is not configured")
        users = user_management.list_users(_identity)
        return {
            "items": [
                {"user_id": str(user.id), "status": user.status.value}
                for user in users
            ]
        }

    @app.post("/api/v1/users")
    def create_user(_identity: AuthenticatedIdentity = Depends(require_operator)) -> dict[str, object]:
        if user_management is None:
            raise HTTPException(status_code=503, detail="User management is not configured")
        try:
            user, credential = user_management.create_user(_identity)
        except AuthorizationError as error:
            raise HTTPException(status_code=403, detail="Forbidden") from error
        return {
            "user_id": str(user.id),
            "status": user.status.value,
            "credential": credential.secret,
        }

    @app.patch("/api/v1/users/{user_id}/status")
    def change_user_status(
        user_id: UUID,
        status: str,
        _identity: AuthenticatedIdentity = Depends(require_operator),
    ) -> dict[str, object]:
        if user_management is None:
            raise HTTPException(status_code=503, detail="User management is not configured")
        try:
            requested = UserStatus(status)
        except ValueError as error:
            raise HTTPException(status_code=400, detail="Invalid user status") from error
        try:
            user = user_management.set_status(_identity, user_id, requested)
        except UserManagementError as error:
            if str(error) == "User not found":
                raise HTTPException(status_code=404, detail=str(error)) from error
            raise HTTPException(status_code=409, detail=str(error)) from error
        return {"user_id": str(user.id), "status": user.status.value}

    @app.post("/api/v1/users/{user_id}/credentials/rotate")
    def rotate_user_credential(
        user_id: UUID,
        _identity: AuthenticatedIdentity = Depends(require_operator),
    ) -> dict[str, object]:
        if user_management is None:
            raise HTTPException(status_code=503, detail="User management is not configured")
        try:
            credential = user_management.rotate_user_credential(_identity, user_id)
        except UserManagementError as error:
            if str(error) == "User not found":
                raise HTTPException(status_code=404, detail=str(error)) from error
            raise HTTPException(status_code=409, detail=str(error)) from error
        return {"user_id": str(credential.user_id), "credential": credential.secret}

    @app.post("/api/v1/users/me/credentials/rotate")
    def rotate_own_credential(
        identity: AuthenticatedIdentity = Depends(require_authenticated),
    ) -> dict[str, object]:
        if user_management is None:
            raise HTTPException(status_code=503, detail="User management is not configured")
        try:
            credential = user_management.rotate_own_credential(identity)
        except UserManagementError as error:
            raise HTTPException(status_code=409, detail=str(error)) from error
        return {"user_id": str(credential.user_id), "credential": credential.secret}

    @app.get("/api/v1/analysis/{symbol}")
    def get_analysis(symbol: str, _identity: AuthenticatedIdentity = Depends(require_operator)) -> dict[str, object]:
        result = get_analysis_result.execute(symbol)

        if result is None:
            raise HTTPException(
                status_code=404,
                detail=f"Analysis result not found for {symbol}",
            )

        response = AnalysisResultResponse.from_result(symbol, result)
        return asdict(response)

    @app.post("/api/v1/analysis/{symbol}")
    def run_analysis(symbol: str, _identity: AuthenticatedIdentity = Depends(require_operator)) -> dict[str, object]:
        if run_stock_analysis_by_symbol is None:
            raise HTTPException(
                status_code=503,
                detail="Analysis execution is not configured",
            )

        try:
            run_stock_analysis_by_symbol.execute(symbol, date.today())
        except UnknownStockSymbolError as error:
            raise HTTPException(status_code=404, detail=str(error)) from error
        except RuntimeError as error:
            logger.exception("Analysis execution failed for symbol %s", symbol, exc_info=error)
            raise HTTPException(
                status_code=500,
                detail="Analysis execution failed",
            ) from error

        result = get_analysis_result.execute(symbol)
        if result is None:
            raise HTTPException(
                status_code=500,
                detail=f"Analysis result was not stored for {symbol}",
            )

        response = AnalysisResultResponse.from_result(symbol, result)
        return asdict(response)

    @app.get("/api/v1/history/{symbol}")
    def get_history(
        symbol: str,
        from_date: date | None = None,
        to_date: date | None = None,
        _identity: AuthenticatedIdentity = Depends(require_operator),
    ) -> dict[str, object]:
        if get_analysis_history is None:
            raise HTTPException(status_code=503, detail="Analysis history is not configured")
        try:
            items = get_analysis_history.execute(symbol, start_date=from_date, end_date=to_date)
        except ValueError as error:
            raise HTTPException(status_code=400, detail=str(error)) from error
        if items is None:
            raise HTTPException(status_code=404, detail=f"Analysis history not found for {symbol}")
        response = AnalysisHistoryResponse.from_items(symbol.strip().upper(), items)
        return response.to_dict()


    @app.get("/api/v1/analysis-runs")
    def list_analysis_runs_route(
        state: str | None = None,
        page_size: int = 50,
        cursor: str | None = None,
        identity: AuthenticatedIdentity = Depends(require_authenticated),
    ) -> dict[str, object]:
        if list_analysis_runs is None:
            raise HTTPException(
                status_code=503,
                detail="Analysis run history is not configured",
            )

        requested_state = None
        if state is not None:
            try:
                requested_state = ExecutionState(state)
            except ValueError as error:
                raise HTTPException(status_code=400, detail="Invalid analysis run state") from error

        try:
            view = list_analysis_runs.execute(
                state=requested_state,
                page_size=page_size,
                cursor=cursor,
                identity=identity,
            )
        except InvalidAnalysisRunListQueryError as error:
            raise HTTPException(status_code=400, detail=str(error)) from error

        return AnalysisRunListResponse.from_view(view).to_dict()

    @app.get("/api/v1/analysis-runs/{run_id}")
    def get_analysis_run_route(
        run_id: UUID,
        page_size: int = 50,
        cursor: str | None = None,
        identity: AuthenticatedIdentity = Depends(require_authenticated),
    ) -> dict[str, object]:
        if get_analysis_run is None:
            raise HTTPException(
                status_code=503,
                detail="Analysis run history is not configured",
            )

        try:
            view = get_analysis_run.execute(
                run_id,
                page_size=page_size,
                cursor=cursor,
                identity=identity,
            )
        except AnalysisRunNotFoundError as error:
            raise HTTPException(status_code=404, detail=str(error)) from error
        except InvalidAnalysisRunQueryError as error:
            raise HTTPException(status_code=400, detail=str(error)) from error

        return AnalysisRunResponse.from_view(view).to_dict()

    @app.get("/api/v1/comparisons/{symbol}")
    def compare_analysis(
        symbol: str,
        before: UUID,
        after: UUID,
        _identity: AuthenticatedIdentity = Depends(require_operator),
    ) -> dict[str, object]:
        if compare_analysis_snapshots is None:
            raise HTTPException(
                status_code=503,
                detail="Analysis comparison is not configured",
            )

        try:
            comparison = compare_analysis_snapshots.execute(
                symbol,
                before_snapshot_id=before,
                after_snapshot_id=after,
            )
        except AnalysisSnapshotNotFoundError as error:
            raise HTTPException(status_code=404, detail=str(error)) from error
        except InvalidSnapshotComparisonError as error:
            raise HTTPException(status_code=400, detail=str(error)) from error

        return AnalysisComparisonResponse.from_comparison(comparison).to_dict()

    @app.get("/api/v1/performance/{symbol}")
    def calculate_performance(
        symbol: str,
        before: UUID,
        after: UUID,
        _identity: AuthenticatedIdentity = Depends(require_operator),
    ) -> dict[str, object]:
        if calculate_snapshot_performance is None:
            raise HTTPException(status_code=503, detail="Historical performance is not configured")
        try:
            performance = calculate_snapshot_performance.execute(
                symbol, before_snapshot_id=before, after_snapshot_id=after
            )
        except AnalysisSnapshotPerformanceNotFoundError as error:
            raise HTTPException(status_code=404, detail=str(error)) from error
        except InvalidSnapshotPerformanceError as error:
            raise HTTPException(status_code=400, detail=str(error)) from error
        return AnalysisSnapshotPerformanceResponse.from_performance(performance).to_dict()
    @app.get("/api/v1/reports/{symbol}")
    def get_report(symbol: str, _identity: AuthenticatedIdentity = Depends(require_operator)) -> dict[str, object]:
        if get_analysis_report is None:
            raise HTTPException(
                status_code=503,
                detail="Analysis reporting is not configured",
            )

        report = get_analysis_report.execute(symbol)
        if report is None:
            raise HTTPException(
                status_code=404,
                detail=f"Analysis report not found for {symbol}",
            )

        response = AnalysisReportResponse.from_report(report)
        return asdict(response)

    @app.post("/api/v1/market-analysis")
    def run_market_analysis(identity: AuthenticatedIdentity = Depends(require_authenticated)) -> dict[str, object]:
        if run_configured_market_analysis is None:
            raise HTTPException(status_code=503, detail="Market analysis execution is not configured")

        try:
            execution = run_configured_market_analysis.execute(
                date.today(),
                owner_user_id=identity.user_id if Permission.OPERATOR not in identity.permissions else None,
            )
        except Exception as error:
            logger.exception("Market-wide analysis execution failed", exc_info=error)
            raise HTTPException(status_code=500, detail="Market-wide analysis execution failed") from error

        response_execution = getattr(execution, "execution", execution)
        response = MarketAnalysisExecutionResponse.from_execution(response_execution)
        return asdict(response)

    @app.get("/api/v1/opportunities")
    def get_opportunities(symbols: str = "", _identity: AuthenticatedIdentity = Depends(require_operator)) -> dict[str, object]:
        if get_market_opportunity_ranking is None:
            raise HTTPException(status_code=503, detail="Market opportunity reporting is not configured")

        requested_symbols = [
            symbol.strip().upper()
            for symbol in symbols.split(",")
            if symbol.strip()
        ]

        try:
            view = get_market_opportunity_ranking.execute(requested_symbols)
        except ValueError as error:
            raise HTTPException(status_code=400, detail=str(error)) from error

        response = MarketOpportunityViewResponse.from_view(view)
        return asdict(response)
    @app.get("/api/v1/workflows/executions")
    def list_scheduled_workflow_executions(
        occurrence_id: str | None = None,
        identity: AuthenticatedIdentity = Depends(require_authenticated),
    ) -> dict[str, object]:
        if get_scheduled_workflow_executions is None:
            raise HTTPException(
                status_code=503,
                detail="Scheduled workflow execution reporting is not configured",
            )

        if occurrence_id is not None and not occurrence_id.strip():
            raise HTTPException(status_code=422, detail="occurrence_id cannot be empty")

        try:
            if authenticator is None:
                items = get_scheduled_workflow_executions.execute(
                    occurrence_id=occurrence_id,
                )
            else:
                items = get_scheduled_workflow_executions.execute(
                    occurrence_id=occurrence_id,
                    identity=identity,
                )
        except AuthorizationError as error:
            raise HTTPException(status_code=403, detail="Forbidden") from error
        except Exception as error:
            logger.exception("Scheduled workflow execution history failed", exc_info=error)
            raise HTTPException(
                status_code=500,
                detail="Scheduled workflow execution reporting failed",
            ) from error

        if occurrence_id is not None and not items:
            raise HTTPException(
                status_code=404,
                detail=f"Scheduled workflow execution not found for {occurrence_id}",
            )

        response = ScheduledWorkflowExecutionsResponse.from_items(items)
        return asdict(response)

    @app.get("/api/v1/workflows/history")
    def get_scheduled_workflow_history_route(
        page_size: int | None = None,
        cursor: str | None = None,
        from_state: str | None = None,
        to_state: str | None = None,
        occurred_from: datetime | None = None,
        occurred_to: datetime | None = None,
        identity: AuthenticatedIdentity = Depends(require_authenticated),
    ) -> dict[str, object]:
        if get_scheduled_workflow_history is None:
            raise HTTPException(status_code=503, detail="Scheduled workflow history is not configured")

        try:
            history = get_scheduled_workflow_history.execute(
                identity,
                page_size=page_size,
                cursor=cursor,
                from_state=from_state,
                to_state=to_state,
                occurred_from=occurred_from,
                occurred_to=occurred_to,
            )
        except InvalidScheduledWorkflowHistoryQueryError as error:
            raise HTTPException(status_code=400, detail=str(error)) from error
        except AuthorizationError as error:
            raise HTTPException(status_code=403, detail="Forbidden") from error
        except Exception as error:
            logger.exception("Scheduled workflow cross-execution history failed", exc_info=error)
            raise HTTPException(status_code=500, detail="Scheduled workflow history failed") from error

        response = ScheduledWorkflowHistoryResponse.from_read_model(history)
        return asdict(response)
    @app.get("/api/v1/workflows/executions/{execution_id}/history")
    def get_scheduled_workflow_execution_history_route(
        execution_id: UUID,
        page_size: int | None = None,
        cursor: str | None = None,
        from_state: str | None = None,
        to_state: str | None = None,
        occurred_from: datetime | None = None,
        occurred_to: datetime | None = None,
        identity: AuthenticatedIdentity = Depends(require_authenticated),
    ) -> dict[str, object]:
        if get_scheduled_workflow_execution_history is None:
            raise HTTPException(
                status_code=503,
                detail="Scheduled workflow execution history is not configured",
            )

        try:
            history = get_scheduled_workflow_execution_history.execute(
                execution_id,
                identity,
                page_size=page_size,
                cursor=cursor,
                from_state=from_state,
                to_state=to_state,
                occurred_from=occurred_from,
                occurred_to=occurred_to,
            )
        except ScheduledWorkflowExecutionHistoryNotFoundError as error:
            raise HTTPException(status_code=404, detail=str(error)) from error
        except InvalidScheduledWorkflowExecutionHistoryQueryError as error:
            raise HTTPException(status_code=400, detail=str(error)) from error
        except AuthorizationError as error:
            raise HTTPException(status_code=403, detail="Forbidden") from error
        except Exception as error:
            logger.exception(
                "Scheduled workflow execution history failed for %s",
                execution_id,
                exc_info=error,
            )
            raise HTTPException(
                status_code=500,
                detail="Scheduled workflow execution history failed",
            ) from error

        response = ScheduledWorkflowExecutionHistoryResponse.from_read_model(history)
        return asdict(response)

    @app.post("/api/v1/workflows/executions/{execution_id}/recover")
    def recover_scheduled_workflow_execution(
        execution_id: UUID,
        identity: AuthenticatedIdentity = Depends(require_authenticated),
    ) -> dict[str, object]:
        if recover_durable_scheduled_workflow is None:
            raise HTTPException(
                status_code=503,
                detail="Scheduled workflow recovery is not configured",
            )

        try:
            if authenticator is None:
                execution = recover_durable_scheduled_workflow.execute(
                    execution_id,
                    date.today(),
                )
            else:
                execution = recover_durable_scheduled_workflow.execute(
                    execution_id,
                    date.today(),
                    identity,
                )
        except WorkflowExecutionNotFoundError as error:
            raise HTTPException(status_code=404, detail=str(error)) from error
        except WorkflowExecutionNotRecoverableError as error:
            raise HTTPException(status_code=409, detail=str(error)) from error
        except AuthorizationError as error:
            raise HTTPException(status_code=403, detail="Forbidden") from error
        except Exception as error:
            logger.exception(
                "Scheduled workflow recovery failed for %s",
                execution_id,
                exc_info=error,
            )
            raise HTTPException(
                status_code=500,
                detail="Scheduled workflow recovery failed",
            ) from error

        response = ScheduledWorkflowExecutionResponse.from_execution(execution)
        return asdict(response)

    @app.post("/api/v1/alerts/{symbol}/deliver")
    def deliver_alert(symbol: str, channel: str, _identity: AuthenticatedIdentity = Depends(require_operator)) -> dict[str, object]:
        if deliver_alert_by_symbol is None:
            raise HTTPException(status_code=503, detail="Alert delivery is not configured")

        try:
            record = deliver_alert_by_symbol.execute(symbol, channel)
        except AlertCandidateNotFoundError as error:
            raise HTTPException(status_code=404, detail=str(error)) from error
        except ValueError as error:
            raise HTTPException(status_code=400, detail=str(error)) from error

        response = AlertDeliveryResponse.from_record(record)
        return asdict(response)

    @app.get("/api/v1/alerts/{symbol}")
    def get_alert(symbol: str, _identity: AuthenticatedIdentity = Depends(require_operator)) -> dict[str, object]:
        if get_alert_candidate is None:
            raise HTTPException(
                status_code=503,
                detail="Alert reporting is not configured",
            )

        candidate = get_alert_candidate.execute(symbol)
        if candidate is None:
            raise HTTPException(
                status_code=404,
                detail=f"Alert candidate not found for {symbol}",
            )

        response = AlertCandidateResponse.from_candidate(candidate)
        return asdict(response)

    return app
