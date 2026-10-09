import logging
import os
from dataclasses import asdict
from datetime import date
from uuid import UUID

from fastapi import Depends, FastAPI, Header, HTTPException, Request
from fastapi.middleware.cors import CORSMiddleware

from app.api.market_intelligence_routes import create_market_intelligence_router

from app.api.user_management_routes import create_user_management_router
from app.api.scheduled_workflow_routes import create_scheduled_workflow_router
from app.application.clock import egx_today

from app.api.auth_rate_limit import AuthenticationRateLimiter
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
from app.api.market_opportunity_view_response import MarketOpportunityViewResponse
from app.api.stock_research_response import StockResearchResponse
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
from app.application.analysis.delete_analysis_run import AnalysisLifecycleNotFoundError, DeleteAnalysisRun
from app.application.analysis.delete_analysis_snapshot import DeleteAnalysisSnapshot
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
    Authenticator,
)
from app.application.security.authorization import AuthorizationError, OperatorAuthorizer
from app.application.security.identity import AuthenticatedIdentity, Permission
from app.application.identity.get_management_audit import GetManagementAudit
from app.application.identity.get_user_audit_history import (
    GetUserAuditHistory,
)
from app.application.identity.user_management import UserManagementService
from app.domain.execution import ExecutionState
from app.application.analysis.run_configured_market_analysis import RunConfiguredMarketAnalysis
from app.application.execution.get_scheduled_workflow_history import (
    GetScheduledWorkflowHistory,
)
from app.application.execution.get_scheduled_workflow_execution_history import (
    GetScheduledWorkflowExecutionHistory,
)
from app.application.execution.get_scheduled_workflow_executions import GetScheduledWorkflowExecutions
from app.application.execution.recover_durable_scheduled_workflow import (
    RecoverDurableScheduledWorkflow,
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
from app.application.research.get_stock_research import GetStockResearch, StockResearchNotFoundError
from app.application.market_intelligence.rank_momentum import RankMomentumLeaders
from app.application.market_intelligence.run_technical_scanner import RunTechnicalScanner
from app.application.market_intelligence.rank_sectors import RankSectors
from app.application.market_intelligence.scan_fibonacci import ScanFibonacciOpportunities
from app.application.market_intelligence.scan_breakouts import ScanBreakouts
from app.application.signals.generate_signal import GenerateSignal

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
    allowed_origins = [
        origin.strip().rstrip("/")
        for origin in os.getenv("EGX_CORS_ALLOWED_ORIGINS", "").split(",")
        if origin.strip()
    ]
    if "*" in allowed_origins:
        raise ValueError("EGX_CORS_ALLOWED_ORIGINS must use explicit origins, not '*'")
    if allowed_origins:
        app.add_middleware(
            CORSMiddleware,
            allow_origins=allowed_origins,
            allow_credentials=True,
            allow_methods=["GET", "POST", "PUT", "PATCH", "DELETE", "OPTIONS"],
            allow_headers=["Authorization", "Content-Type"],
        )
    get_analysis_result = GetAnalysisResult(result_store)
    rank_momentum_leaders = RankMomentumLeaders(result_store)
    run_technical_scanner = RunTechnicalScanner(result_store)
    rank_sectors = RankSectors(result_store)
    scan_fibonacci = ScanFibonacciOpportunities(result_store)
    scan_breakouts = ScanBreakouts(result_store)
    generate_signal = GenerateSignal(result_store)
    get_stock_research = GetStockResearch(get_analysis_report) if get_analysis_report is not None else None
    legacy_test_composition = isinstance(operator_token, _OperatorTokenNotProvided) and authenticator is None
    configured_token = (
        None
        if isinstance(operator_token, _OperatorTokenNotProvided)
        else operator_token if operator_token is not None else os.getenv("EGX_OPERATOR_TOKEN")
    )
    operator_authenticator = BearerTokenAuthenticator(configured_token) if configured_token else None
    authorizer = OperatorAuthorizer()

    auth_rate_limiter = AuthenticationRateLimiter()

    def _client_key(request: Request) -> str:
        trust_proxy_headers = os.getenv("EGX_TRUST_PROXY_HEADERS", "").strip().lower() in {
            "1", "true", "yes", "on"
        }
        if trust_proxy_headers:
            real_ip = request.headers.get("x-real-ip", "").strip()
            if real_ip and "," not in real_ip:
                return real_ip
        return request.client.host if request.client is not None else "unknown"

    def _reject_if_rate_limited(client_key: str) -> None:
        if auth_rate_limiter.is_blocked(client_key):
            raise HTTPException(
                status_code=429,
                detail="Too many failed authentication attempts",
                headers={"Retry-After": str(auth_rate_limiter.retry_after_seconds(client_key))},
            )

    def require_authenticated(
        request: Request,
        authorization: str | None = Header(default=None),
    ) -> AuthenticatedIdentity:
        if legacy_test_composition:
            return AuthenticatedIdentity.operator()
        client_key = _client_key(request)
        _reject_if_rate_limited(client_key)
        if authenticator is None and operator_authenticator is None:
            raise HTTPException(status_code=503, detail="Authentication is not configured")
        try:
            if authenticator is not None:
                identity = authenticator.authenticate(authorization)
            else:
                if operator_authenticator is None:
                    raise HTTPException(status_code=503, detail="Authentication is not configured")
                identity = operator_authenticator.authenticate(authorization)
        except AuthenticationError as error:
            auth_rate_limiter.record_failure(client_key)
            raise HTTPException(
                status_code=401,
                detail="Authentication required",
                headers={"WWW-Authenticate": "Bearer"},
            ) from error
        auth_rate_limiter.record_success(client_key)
        return identity

    def require_operator(
        request: Request,
        authorization: str | None = Header(default=None),
    ) -> AuthenticatedIdentity:
        if legacy_test_composition:
            return AuthenticatedIdentity.operator()
        client_key = _client_key(request)
        _reject_if_rate_limited(client_key)
        if authenticator is None and operator_authenticator is None:
            raise HTTPException(status_code=503, detail="Authentication is not configured")
        try:
            if authenticator is not None:
                identity = authenticator.authenticate(authorization)
            else:
                if operator_authenticator is None:
                    raise HTTPException(status_code=503, detail="Authentication is not configured")
                identity = operator_authenticator.authenticate(authorization)
        except AuthenticationError as error:
            auth_rate_limiter.record_failure(client_key)
            raise HTTPException(
                status_code=401,
                detail="Authentication required",
                headers={"WWW-Authenticate": "Bearer"},
            ) from error
        try:
            authorizer.require(identity, Permission.OPERATOR)
        except AuthorizationError as error:
            raise HTTPException(status_code=403, detail="Forbidden") from error
        auth_rate_limiter.record_success(client_key)
        return identity

    app.include_router(
        create_scheduled_workflow_router(
            get_scheduled_workflow_executions=get_scheduled_workflow_executions,
            get_scheduled_workflow_execution_history=get_scheduled_workflow_execution_history,
            get_scheduled_workflow_history=get_scheduled_workflow_history,
            recover_durable_scheduled_workflow=recover_durable_scheduled_workflow,
            authenticator=authenticator,
            require_authenticated=require_authenticated,
        )
    )

    app.include_router(
        create_market_intelligence_router(
            rank_momentum_leaders=rank_momentum_leaders,
            run_technical_scanner=run_technical_scanner,
            rank_sectors=rank_sectors,
            scan_fibonacci=scan_fibonacci,
            scan_breakouts=scan_breakouts,
            generate_signal=generate_signal,
            require_authenticated=require_authenticated,
        )
    )

    app.include_router(
        create_user_management_router(
            user_management=user_management,
            get_management_audit=get_management_audit,
            get_user_audit_history=get_user_audit_history,
            require_authenticated=require_authenticated,
            require_operator=require_operator,
        )
    )

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

    @app.get("/api/v1/analysis/{symbol}")
    def get_analysis(symbol: str, identity: AuthenticatedIdentity = Depends(require_authenticated)) -> dict[str, object]:
        result = get_analysis_result.execute(symbol, identity=identity)

        if result is None:
            raise HTTPException(
                status_code=404,
                detail=f"Analysis result not found for {symbol}",
            )

        response = AnalysisResultResponse.from_result(symbol, result)
        return asdict(response)

    @app.post("/api/v1/analysis/{symbol}")
    def run_analysis(symbol: str, identity: AuthenticatedIdentity = Depends(require_authenticated)) -> dict[str, object]:
        if run_stock_analysis_by_symbol is None:
            raise HTTPException(
                status_code=503,
                detail="Analysis execution is not configured",
            )

        try:
            run_stock_analysis_by_symbol.execute(symbol, egx_today(), identity=identity)
        except UnknownStockSymbolError as error:
            raise HTTPException(status_code=404, detail=str(error)) from error
        except RuntimeError as error:
            logger.exception("Analysis execution failed for symbol %s", symbol, exc_info=error)
            raise HTTPException(
                status_code=500,
                detail="Analysis execution failed",
            ) from error

        result = get_analysis_result.execute(symbol, identity=identity)
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
        identity: AuthenticatedIdentity = Depends(require_authenticated),
    ) -> dict[str, object]:
        if get_analysis_history is None:
            raise HTTPException(status_code=503, detail="Analysis history is not configured")
        try:
            items = get_analysis_history.execute(symbol, start_date=from_date, end_date=to_date, identity=identity)
        except ValueError as error:
            raise HTTPException(status_code=400, detail=str(error)) from error
        if items is None:
            raise HTTPException(status_code=404, detail=f"Analysis history not found for {symbol}")
        response = AnalysisHistoryResponse.from_items(symbol.strip().upper(), items)
        return response.to_dict()


    @app.delete("/api/v1/analysis-runs/{run_id}")
    def delete_analysis_run_route(
        run_id: UUID,
        identity: AuthenticatedIdentity = Depends(require_authenticated),
    ) -> dict[str, object]:
        if delete_analysis_run is None:
            raise HTTPException(status_code=503, detail="Analysis lifecycle is not configured")
        try:
            result = delete_analysis_run.execute(run_id, identity)
        except AnalysisLifecycleNotFoundError as error:
            raise HTTPException(status_code=404, detail="Analysis run not found") from error
        except AuthorizationError as error:
            raise HTTPException(status_code=403, detail="Forbidden") from error
        except ValueError as error:
            raise HTTPException(status_code=409, detail=str(error)) from error
        return {"run_id": str(run_id), "deleted": result.deleted}

    @app.delete("/api/v1/analysis-snapshots/{snapshot_id}")
    def delete_analysis_snapshot_route(
        snapshot_id: UUID,
        identity: AuthenticatedIdentity = Depends(require_authenticated),
    ) -> dict[str, object]:
        if delete_analysis_snapshot is None:
            raise HTTPException(status_code=503, detail="Analysis lifecycle is not configured")
        try:
            result = delete_analysis_snapshot.execute(snapshot_id, identity)
        except AuthorizationError as error:
            raise HTTPException(status_code=403, detail="Forbidden") from error
        except ValueError as error:
            raise HTTPException(status_code=409, detail=str(error)) from error
        if not result.deleted:
            raise HTTPException(status_code=404, detail="Analysis snapshot not found")
        return {"snapshot_id": str(snapshot_id), "deleted": True}

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
    def get_report(symbol: str, identity: AuthenticatedIdentity = Depends(require_authenticated)) -> dict[str, object]:
        if get_analysis_report is None:
            raise HTTPException(
                status_code=503,
                detail="Analysis reporting is not configured",
            )

        report = get_analysis_report.execute(symbol, identity=identity)
        if report is None:
            raise HTTPException(
                status_code=404,
                detail=f"Analysis report not found for {symbol}",
            )

        response = AnalysisReportResponse.from_report(report)
        return asdict(response)

    @app.get("/api/v1/research/{symbol}")
    def get_stock_research_route(
        symbol: str,
        identity: AuthenticatedIdentity = Depends(require_authenticated),
    ) -> dict[str, object]:
        if get_stock_research is None:
            raise HTTPException(status_code=503, detail="Stock research is not configured")
        try:
            view = get_stock_research.execute(symbol, identity=identity)
        except StockResearchNotFoundError as error:
            raise HTTPException(status_code=404, detail=str(error)) from error
        return StockResearchResponse.from_view(view).to_dict()

    @app.post("/api/v1/market-analysis")
    def run_market_analysis(identity: AuthenticatedIdentity = Depends(require_authenticated)) -> dict[str, object]:
        if run_configured_market_analysis is None:
            raise HTTPException(status_code=503, detail="Market analysis execution is not configured")

        try:
            execution = run_configured_market_analysis.execute(
                egx_today(),
                owner_user_id=identity.user_id if Permission.OPERATOR not in identity.permissions else None,
            )
        except Exception as error:
            logger.exception("Market-wide analysis execution failed", exc_info=error)
            raise HTTPException(status_code=500, detail="Market-wide analysis execution failed") from error

        response = MarketAnalysisExecutionResponse.from_execution(execution.execution)
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
