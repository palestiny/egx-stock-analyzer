import hmac
import logging
import os
from dataclasses import asdict
from decimal import Decimal
from datetime import date, datetime, timezone
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
from app.api.technical_indicator_response import TechnicalIndicatorHistoryResponse
from app.api.analysis_response import AnalysisResultResponse
from app.api.market_analysis_execution_response import MarketAnalysisExecutionResponse
from app.api.market_opportunity_view_response import MarketOpportunityViewResponse
from app.api.stock_research_response import StockResearchResponse
from app.api.session_opportunity_ledger_response import SessionOpportunityLedgerResponse
from app.application.reporting.get_analysis_history import GetAnalysisHistory
from app.application.reporting.build_session_opportunity_ledger import BuildSessionOpportunityLedger, SessionOpportunityReportStore
from app.application.reporting.get_owner_dashboard_overview import GetOwnerDashboardOverview
from app.application.alerts.dispatch_signal_alert_outbox import DispatchSignalAlertOutbox
from app.application.alerts.publish_signal_opportunity import PublishSignalOpportunity
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
from app.application.market_intelligence.analyze_stock_regime import AnalyzeStockRegime
from app.application.market_intelligence.rank_momentum import RankMomentumLeaders
from app.application.market_intelligence.calculate_market_breadth import CalculateMarketBreadth
from app.application.market_intelligence.run_technical_scanner import RunTechnicalScanner
from app.application.market_intelligence.rank_sectors import RankSectors
from app.application.market_intelligence.scan_fibonacci import ScanFibonacciOpportunities
from app.application.market_intelligence.scan_breakouts import ScanBreakouts
from app.application.signals.generate_signal import GenerateSignal
from app.application.news.ingestion import NewsIngestionService
from app.application.news.store import NewsEventStore
from app.application.notifications.telegram_account_linking import (
    TelegramAccountLinkingService,
    TelegramChatAlreadyLinked,
)
from app.application.notifications.telegram_message_sender import TelegramMessageSender

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
    analyze_stock_regime: AnalyzeStockRegime | None = None,
    build_session_opportunity_ledger: BuildSessionOpportunityLedger | None = None,
    news_event_store: NewsEventStore | None = None,
    news_ingestion_service: NewsIngestionService | None = None,
    telegram_account_linking: TelegramAccountLinkingService | None = None,
    telegram_notification_provider: TelegramMessageSender | None = None,
    telegram_webhook_secret: str | None = None,
    generate_signal: GenerateSignal | None = None,
    publish_signal_opportunity: PublishSignalOpportunity | None = None,
    dispatch_signal_alert_outbox: DispatchSignalAlertOutbox | None = None,
    get_owner_dashboard_overview: GetOwnerDashboardOverview | None = None,
    session_opportunity_report_store: SessionOpportunityReportStore | None = None,
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
    calculate_market_breadth = CalculateMarketBreadth(result_store)
    run_technical_scanner = RunTechnicalScanner(result_store)
    rank_sectors = RankSectors(result_store)
    scan_fibonacci = ScanFibonacciOpportunities(result_store)
    scan_breakouts = ScanBreakouts(result_store)
    generate_signal = generate_signal or GenerateSignal(result_store)
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
            calculate_market_breadth=calculate_market_breadth,
            analyze_stock_regime=analyze_stock_regime,
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
    @app.get("/api/v1/session-opportunity-ledger")
    def get_session_opportunity_ledger_route(
        session_date: date,
        generated_at: datetime | None = None,
        _identity: AuthenticatedIdentity = Depends(require_operator),
    ) -> dict[str, object]:
        if build_session_opportunity_ledger is None:
            raise HTTPException(
                status_code=503,
                detail="Session opportunity ledger is not configured",
            )
        cutoff = generated_at or datetime.now(timezone.utc)
        if cutoff.tzinfo is None or cutoff.utcoffset() is None:
            raise HTTPException(status_code=422, detail="generated_at must include a timezone")
        try:
            report = build_session_opportunity_ledger.execute(
                session_date,
                generated_at=cutoff,
            )
        except ValueError as error:
            raise HTTPException(status_code=422, detail=str(error)) from error
        return SessionOpportunityLedgerResponse.from_report(report)

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

    @app.get("/api/v1/technical-indicators/{symbol}")
    def get_technical_indicator_history(
        symbol: str,
        limit: int = 250,
        identity: AuthenticatedIdentity = Depends(require_authenticated),
    ) -> dict[str, object]:
        if get_analysis_report is None:
            raise HTTPException(status_code=503, detail="Analysis reporting is not configured")
        if limit < 1 or limit > 1000:
            raise HTTPException(status_code=400, detail="limit must be between 1 and 1000")
        report = get_analysis_report.execute(symbol, identity=identity)
        if report is None:
            raise HTTPException(status_code=404, detail=f"Analysis report not found for {symbol}")
        return TechnicalIndicatorHistoryResponse.from_report(report, limit=limit)

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

    @app.post("/api/v1/telegram/link-challenges")
    def issue_telegram_link_challenge(
        identity: AuthenticatedIdentity = Depends(require_authenticated),
    ) -> dict[str, object]:
        if telegram_account_linking is None or telegram_notification_provider is None:
            raise HTTPException(status_code=503, detail="Telegram account linking is not configured")
        if identity.user_id is None:
            raise HTTPException(status_code=403, detail="A user account is required")
        challenge = telegram_account_linking.issue(
            identity.user_id,
            now=datetime.now(timezone.utc),
        )
        return {
            "token": challenge.token,
            "expires_at": challenge.expires_at.isoformat(),
            "instruction": "Send /start <token> to the configured Telegram bot before the token expires.",
        }

    @app.delete("/api/v1/telegram/link")
    def unlink_telegram_account(
        identity: AuthenticatedIdentity = Depends(require_authenticated),
    ) -> dict[str, object]:
        if telegram_account_linking is None:
            raise HTTPException(status_code=503, detail="Telegram account linking is not configured")
        if identity.user_id is None:
            raise HTTPException(status_code=403, detail="A user account is required")
        removed = telegram_account_linking.unlink(
            identity.user_id,
            now=datetime.now(timezone.utc),
        )
        return {"unlinked": removed}

    @app.post("/api/v1/telegram/webhook")
    async def telegram_webhook(
        request: Request,
        x_telegram_bot_api_secret_token: str | None = Header(default=None),
    ) -> dict[str, object]:
        if (
            telegram_account_linking is None
            or telegram_notification_provider is None
            or not telegram_webhook_secret
        ):
            raise HTTPException(status_code=503, detail="Telegram webhook is not configured")
        if (
            x_telegram_bot_api_secret_token is None
            or not hmac.compare_digest(
                x_telegram_bot_api_secret_token,
                telegram_webhook_secret,
            )
        ):
            raise HTTPException(status_code=403, detail="Invalid Telegram webhook secret")

        try:
            update = await request.json()
        except ValueError:
            raise HTTPException(status_code=400, detail="Invalid Telegram update") from None
        if not isinstance(update, dict):
            return {"ok": True}
        raw_update_id = update.get("update_id")
        if not isinstance(raw_update_id, (str, int)) or not str(raw_update_id).strip():
            return {"ok": True}
        webhook_now = datetime.now(timezone.utc)
        message = update.get("message")
        if not isinstance(message, dict):
            return {"ok": True}
        chat = message.get("chat")
        text_value = message.get("text")
        if not isinstance(chat, dict) or not isinstance(text_value, str):
            return {"ok": True}
        raw_chat_id = chat.get("id")
        if not isinstance(raw_chat_id, (str, int)):
            return {"ok": True}
        chat_id = str(raw_chat_id)
        parts = text_value.strip().split(maxsplit=1)
        if not parts or parts[0].split("@", maxsplit=1)[0].lower() != "/start":
            return {"ok": True}

        if len(parts) != 2 or not parts[1].strip():
            if not telegram_account_linking.claim_webhook_update(
                str(raw_update_id),
                now=webhook_now,
            ):
                return {"ok": True, "duplicate": True}
            telegram_notification_provider.send_message(
                chat_id,
                "To link your account, generate a one-time link token in EGX Stock Analyzer and send /start <token>.",
            )
            return {"ok": True}

        try:
            linked_user_id = telegram_account_linking.consume(
                parts[1].strip(),
                chat_id,
                now=webhook_now,
            )
        except TelegramChatAlreadyLinked:
            if not telegram_account_linking.claim_webhook_update(
                str(raw_update_id),
                now=webhook_now,
            ):
                return {"ok": True, "duplicate": True}
            telegram_notification_provider.send_message(
                chat_id,
                "This Telegram chat is already linked to another EGX account.",
            )
            return {"ok": True}

        if not telegram_account_linking.claim_webhook_update(
            str(raw_update_id),
            now=webhook_now,
        ):
            return {"ok": True, "duplicate": True}

        if linked_user_id is None:
            telegram_notification_provider.send_message(
                chat_id,
                "This link token is invalid or expired. Generate a new token in EGX Stock Analyzer.",
            )
        else:
            telegram_notification_provider.send_message(
                chat_id,
                "Your Telegram account is now linked to EGX Stock Analyzer.",
            )
        return {"ok": True}

    @app.post("/api/v1/news/ingest")
    def ingest_news_events_route(
        since: datetime | None = None,
        _identity: AuthenticatedIdentity = Depends(require_operator),
    ) -> dict[str, object]:
        if news_ingestion_service is None:
            raise HTTPException(
                status_code=503,
                detail="News ingestion is not configured; set EGX_NEWS_RSS_URL to an approved HTTPS feed",
            )
        if since is not None and (since.tzinfo is None or since.utcoffset() is None):
            raise HTTPException(status_code=422, detail="since must include a timezone")
        try:
            summary = news_ingestion_service.ingest(since)
        except (ValueError, OSError, TimeoutError) as error:
            logger.warning("Configured news feed ingestion failed: %s", error.__class__.__name__)
            raise HTTPException(
                status_code=502,
                detail="Configured news source could not be ingested",
            ) from error
        return {
            "source_name": summary.source_name,
            "fetched": summary.fetched,
            "inserted": summary.inserted,
            "duplicates": summary.duplicates,
        }

    @app.get("/api/v1/news/events")
    def get_news_events_route(
        symbol: str | None = None,
        as_of: datetime | None = None,
        minimum_entity_confidence: Decimal = Decimal("0.8"),
        limit: int = 100,
        _identity: AuthenticatedIdentity = Depends(require_authenticated),
    ) -> dict[str, object]:
        if news_event_store is None:
            raise HTTPException(status_code=503, detail="News event reporting is not configured")
        normalized_symbol = symbol.strip().upper() if symbol is not None else None
        if symbol is not None and not normalized_symbol:
            raise HTTPException(status_code=400, detail="symbol cannot be empty")
        cutoff = as_of or datetime.now(timezone.utc)
        if cutoff.tzinfo is None or cutoff.utcoffset() is None:
            raise HTTPException(status_code=422, detail="as_of must include a timezone")
        try:
            events = news_event_store.query_as_of(
                cutoff,
                symbol=normalized_symbol,
                minimum_entity_confidence=minimum_entity_confidence,
                limit=limit,
            )
        except ValueError as error:
            raise HTTPException(status_code=422, detail=str(error)) from error
        return {
            "as_of": cutoff.isoformat(),
            "symbol": normalized_symbol,
            "count": len(events),
            "events": [
                {
                    "event_id": str(event.event_id),
                    "source_name": event.source_name,
                    "source_type": event.source_type.value,
                    "source_url": event.source_url,
                    "title": event.title,
                    "category": event.category.value,
                    "published_at": event.published_at.isoformat() if event.published_at else None,
                    "retrieved_at": event.retrieved_at.isoformat(),
                    "first_seen_at": event.first_seen_at.isoformat(),
                    "matched_symbols": list(event.matched_symbols),
                    "entity_match_confidence": str(event.entity_match_confidence),
                    "content_fingerprint": event.content_fingerprint,
                }
                for event in events
            ],
        }



    @app.post("/api/v1/session-opportunity-reports")
    def create_session_report(
        session_date: date,
        generated_at: datetime | None = None,
        _identity: AuthenticatedIdentity = Depends(require_operator),
    ) -> dict[str, object]:
        if build_session_opportunity_ledger is None or session_opportunity_report_store is None:
            raise HTTPException(status_code=503, detail="Session opportunity reporting is not configured")
        cutoff = generated_at or datetime.now(timezone.utc)
        if cutoff.tzinfo is None or cutoff.utcoffset() is None:
            raise HTTPException(status_code=422, detail="generated_at must include a timezone")
        try:
            report = build_session_opportunity_ledger.execute(session_date, generated_at=cutoff)
            created = session_opportunity_report_store.save(report)
        except ValueError as error:
            raise HTTPException(status_code=422, detail=str(error)) from error
        response = SessionOpportunityLedgerResponse.from_report(report)
        response["persisted"] = True
        response["created"] = created
        return response

    @app.get("/api/v1/session-opportunity-reports")
    def read_session_report(
        session_date: date,
        as_of: datetime | None = None,
        _identity: AuthenticatedIdentity = Depends(require_operator),
    ) -> dict[str, object]:
        if session_opportunity_report_store is None:
            raise HTTPException(status_code=503, detail="Session opportunity reporting is not configured")
        cutoff = as_of or datetime.now(timezone.utc)
        if cutoff.tzinfo is None or cutoff.utcoffset() is None:
            raise HTTPException(status_code=422, detail="as_of must include a timezone")
        try:
            report = session_opportunity_report_store.get_latest(session_date, as_of=cutoff)
        except ValueError as error:
            raise HTTPException(status_code=422, detail=str(error)) from error
        if report is None:
            raise HTTPException(status_code=404, detail="No saved session opportunity report exists for that date and cutoff")
        return report

    @app.get("/api/v1/owner/overview")
    def get_owner_dashboard_overview_route(
        as_of: datetime | None = None,
        _identity: AuthenticatedIdentity = Depends(require_operator),
    ) -> dict[str, object]:
        if get_owner_dashboard_overview is None:
            raise HTTPException(status_code=503, detail="Owner dashboard reporting is not configured")
        if as_of is not None and (as_of.tzinfo is None or as_of.utcoffset() is None):
            raise HTTPException(status_code=422, detail="as_of must include a timezone")
        try:
            return get_owner_dashboard_overview.execute(as_of=as_of)
        except ValueError as error:
            raise HTTPException(status_code=422, detail=str(error)) from error

    @app.post("/api/v1/opportunities/{symbol}/publish")
    def publish_opportunity_route(
        symbol: str,
        _identity: AuthenticatedIdentity = Depends(require_operator),
    ) -> dict[str, object]:
        if generate_signal is None or publish_signal_opportunity is None:
            raise HTTPException(status_code=503, detail="Opportunity publication is not configured")
        try:
            signal = generate_signal.execute(symbol)
        except ValueError as error:
            raise HTTPException(status_code=400, detail=str(error)) from error
        if signal is None:
            raise HTTPException(status_code=404, detail="No actionable signal exists in the latest dated analysis snapshot")
        now = datetime.now(timezone.utc)
        try:
            publication = publish_signal_opportunity.execute(signal, recorded_at=now)
        except ValueError as error:
            raise HTTPException(status_code=422, detail=str(error)) from error
        if publication is None:
            raise HTTPException(status_code=409, detail="This signal is no longer active and cannot be published")
        return {
            "signal_id": str(publication.signal_id),
            "event_id": str(publication.event_id),
            "queued_new_event": publication.queued_new_event,
            "recorded_at": now.isoformat(),
            "delivery": "queued_not_yet_delivered",
        }

    @app.post("/api/v1/telegram/opportunities/dispatch")
    def dispatch_telegram_opportunities_route(
        limit: int = 100,
        _identity: AuthenticatedIdentity = Depends(require_operator),
    ) -> dict[str, object]:
        if dispatch_signal_alert_outbox is None:
            raise HTTPException(status_code=503, detail="Subscriber-aware Telegram dispatch is not configured")
        try:
            result = dispatch_signal_alert_outbox.execute(
                now=datetime.now(timezone.utc),
                limit=limit,
            )
        except ValueError as error:
            raise HTTPException(status_code=400, detail=str(error)) from error
        return {
            "events_processed": result.events_processed,
            "recipients_delivered": result.recipients_delivered,
            "recipients_suppressed": result.recipients_suppressed,
            "recipients_failed": result.recipients_failed,
        }

    return app
