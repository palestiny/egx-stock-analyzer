from dataclasses import dataclass, field

from app.application.analysis.input_assembler import AnalysisInputAssembler
from app.application.alerts.dispatch_signal_alert_outbox import DispatchSignalAlertOutbox
from app.application.alerts.publish_signal_opportunity import PublishSignalOpportunity
from app.application.news.ingestion import NewsIngestionService
from app.domain.news.event import NewsSourceType
from app.infrastructure.news.rss_news_source_adapter import RssNewsSourceAdapter
from app.infrastructure.persistence.sqlite_news_event_store import SQLiteNewsEventStore
from app.application.subscriptions.entitlement_evaluator import EntitlementEvaluator
from app.application.notifications.telegram_account_linking import TelegramAccountLinkingService
from app.infrastructure.persistence.sqlite_telegram_account_link_store import SQLiteTelegramAccountLinkStore
from app.application.signals.lifecycle_orchestrator import SignalLifecycleOrchestrator
from app.application.reporting.build_session_opportunity_ledger import BuildSessionOpportunityLedger
from app.infrastructure.notifications.sqlite_alert_outbox import SQLiteAlertOutbox
from app.infrastructure.notifications.sqlite_signal_alert_delivery_store import SQLiteSignalAlertDeliveryStore
from app.infrastructure.persistence.sqlite_signal_history_store import SQLiteSignalHistoryStore
from app.infrastructure.persistence.sqlite_track_record_store import SQLiteTrackRecordStore
from app.infrastructure.persistence.sqlite_subscription_store import SQLiteSubscriptionStore
from app.application.identity.user_management import UserManagementService
from app.infrastructure.persistence.sqlite_management_audit_store import SQLiteManagementAuditStore
from app.application.analysis.automatic_analysis_retention import AutomaticRetentionPolicy
from app.application.analysis.result_store import (
    AnalysisResultStore,
)
from app.application.analysis.run_store import AnalysisRunStore
from app.application.analysis.runtime import (
    StockAnalysisRuntime,
    create_stock_analysis_runtime,
)
from app.application.execution.automatic_workflow_recovery import AutomaticWorkflowRecovery
from app.application.execution.get_scheduled_workflow_execution_history import GetScheduledWorkflowExecutionHistory
from app.application.execution.get_scheduled_workflow_history import GetScheduledWorkflowHistory
from app.application.execution.get_scheduled_workflow_executions import GetScheduledWorkflowExecutions
from app.application.execution.recover_durable_scheduled_workflow import RecoverDurableScheduledWorkflow
from app.application.execution.retry import RetryPolicy
from app.application.execution.run_durable_scheduled_workflow import RunDurableScheduledWorkflow
from app.application.notifications.automatic_alert_delivery import AutomaticAlertDelivery
from app.application.execution.run_configured_market_analysis_with_automatic_alert_delivery import (
    RunConfiguredMarketAnalysisWithAutomaticAlertDelivery,
)
from app.application.notifications.deliver_alert import DeliverAlert
from app.application.notifications.deliver_alert_by_symbol import DeliverAlertBySymbol
from app.application.stocks.catalog import StockCatalog
from app.infrastructure.config import InfrastructureConfig
from app.infrastructure.market_data.yahoo_finance import (
    YahooFinanceAdapter,
    YahooFinanceFundamentalDataSource,
    YahooFinanceHistoryClient,
)
from app.infrastructure.notifications.sqlite_alert_delivery_store import (
    SQLiteAlertDeliveryStore,
)
from app.infrastructure.notifications.telegram_provider import TelegramNotificationProvider
from app.infrastructure.persistence.sqlite_credential_store import SQLiteCredentialStore
from app.infrastructure.persistence.sqlite_analysis_result_store import (
    SQLiteAnalysisResultStore,
)
from app.infrastructure.persistence.sqlite_analysis_run_store import SQLiteAnalysisRunStore
from app.infrastructure.persistence.sqlite_analysis_lifecycle_store import SQLiteAnalysisLifecycleStore
from app.application.security.authentication import ConfiguredBearerTokenAuthenticator
from app.application.security.credentials import CredentialService
from app.application.security.durable_authentication import DurableBearerTokenAuthenticator
from app.infrastructure.persistence.sqlite_scheduled_workflow_execution_store import (
    SQLiteScheduledWorkflowExecutionStore,
)
from app.infrastructure.persistence.sqlite_user_store import SQLiteUserStore
from app.application.security.identity import LEGACY_OPERATOR_USER_ID
from app.domain.identity.user import UserStatus


@dataclass
class InfrastructureRuntime:
    application_runtime: StockAnalysisRuntime
    market_data_provider: YahooFinanceAdapter
    fundamental_data_provider: YahooFinanceFundamentalDataSource
    deliver_alert: DeliverAlert | None = None
    deliver_alert_by_symbol: DeliverAlertBySymbol | None = None
    automatic_alert_delivery: AutomaticAlertDelivery | None = None
    run_configured_market_analysis_with_automatic_alert_delivery: RunConfiguredMarketAnalysisWithAutomaticAlertDelivery | None = None
    telegram_notification_provider: TelegramNotificationProvider | None = None
    telegram_account_linking: TelegramAccountLinkingService | None = None
    telegram_account_link_store: SQLiteTelegramAccountLinkStore | None = None
    dispatch_signal_alert_outbox: DispatchSignalAlertOutbox | None = None
    publish_signal_opportunity: PublishSignalOpportunity | None = None
    signal_alert_delivery_store: SQLiteSignalAlertDeliveryStore | None = None
    telegram_webhook_secret: str | None = None
    news_event_store: SQLiteNewsEventStore | None = None
    news_ingestion_service: NewsIngestionService | None = None
    subscription_store: SQLiteSubscriptionStore | None = None
    entitlement_evaluator: EntitlementEvaluator | None = None
    automatic_workflow_recovery: AutomaticWorkflowRecovery | None = None
    get_scheduled_workflow_executions: GetScheduledWorkflowExecutions | None = None
    get_scheduled_workflow_execution_history: GetScheduledWorkflowExecutionHistory | None = None
    get_scheduled_workflow_history: GetScheduledWorkflowHistory | None = None
    recover_durable_scheduled_workflow: RecoverDurableScheduledWorkflow | None = None
    authenticator: DurableBearerTokenAuthenticator | None = None
    credential_service: CredentialService | None = None
    user_store: SQLiteUserStore | None = None
    user_management: UserManagementService | None = None
    signal_history_store: SQLiteSignalHistoryStore | None = None
    signal_track_record_store: SQLiteTrackRecordStore | None = None
    signal_alert_outbox: SQLiteAlertOutbox | None = None
    signal_lifecycle_orchestrator: SignalLifecycleOrchestrator | None = None
    build_session_opportunity_ledger: BuildSessionOpportunityLedger | None = None
    _closed: bool = field(default=False, init=False, repr=False)

    @property
    def closed(self) -> bool:
        return self._closed

    def close(self) -> None:
        if self._closed:
            return
        self.fundamental_data_provider.close()
        if self.telegram_notification_provider is not None:
            self.telegram_notification_provider.close()
        self._closed = True


def create_infrastructure_runtime(
    stock_catalog: StockCatalog,
    yfinance_module,
    config: InfrastructureConfig,
    result_store: AnalysisResultStore | None = None,
    retry_policy: RetryPolicy | None = None,
    analysis_run_store: AnalysisRunStore | None = None,
) -> InfrastructureRuntime:
    if not config.operator_token or not config.operator_token.strip():
        raise ValueError("EGX_OPERATOR_TOKEN must be configured")

    result_store = result_store or SQLiteAnalysisResultStore(config.analysis_database_path)
    analysis_run_store = analysis_run_store or SQLiteAnalysisRunStore(config.analysis_database_path)
    retry_policy = retry_policy or RetryPolicy(1)

    yahoo_history_client = YahooFinanceHistoryClient(yfinance_module)
    market_data_provider = YahooFinanceAdapter(yahoo_history_client)
    fundamental_data_provider = YahooFinanceFundamentalDataSource(yfinance_module)

    input_assembler = AnalysisInputAssembler(
        market_data_provider=market_data_provider,
        fundamental_data_provider=fundamental_data_provider,
    )

    user_store = SQLiteUserStore(config.analysis_database_path)
    user_store.get_or_create(LEGACY_OPERATOR_USER_ID, UserStatus.ACTIVE)
    configured_authenticator = ConfiguredBearerTokenAuthenticator(
        config.user_bearer_tokens,
        user_store=user_store,
        legacy_operator_token=config.operator_token,
    )
    credential_store = SQLiteCredentialStore(config.analysis_database_path)
    credential_service = CredentialService(credential_store)
    management_audit_store = SQLiteManagementAuditStore(config.analysis_database_path)
    lifecycle_store = SQLiteAnalysisLifecycleStore(config.analysis_database_path)
    user_management = UserManagementService(
        user_store=user_store,
        credential_service=credential_service,
        audit_store=management_audit_store,
    )
    news_event_store = SQLiteNewsEventStore(config.analysis_database_path)
    news_ingestion_service = None
    if config.news_rss_feed_url is not None:
        try:
            news_source_type = NewsSourceType(config.news_rss_source_type)
        except ValueError as error:
            raise ValueError(
                "EGX_NEWS_RSS_SOURCE_TYPE must be a supported NewsSourceType"
            ) from error
        symbol_names = {
            symbol: stock.name
            for symbol in stock_catalog.symbols()
            if (stock := stock_catalog.get(symbol)) is not None
        }
        news_source = RssNewsSourceAdapter(
            source_name=config.news_rss_source_name,
            source_type=news_source_type,
            feed_url=config.news_rss_feed_url,
            symbol_names=symbol_names,
        )
        news_ingestion_service = NewsIngestionService(news_source, news_event_store)
    authenticator = DurableBearerTokenAuthenticator(
        credential_store=credential_store,
        user_store=user_store,
        fallback=configured_authenticator,
    )

    signal_history_store = SQLiteSignalHistoryStore(config.analysis_database_path)
    subscription_store = SQLiteSubscriptionStore(config.analysis_database_path)
    entitlement_evaluator = EntitlementEvaluator(
        subscription_store,
        default_plan_id=config.default_subscription_plan_id,
        default_plan_version=config.default_subscription_plan_version,
    )
    signal_track_record_store = SQLiteTrackRecordStore(config.analysis_database_path)
    signal_alert_outbox = SQLiteAlertOutbox(config.analysis_database_path)
    signal_lifecycle_orchestrator = SignalLifecycleOrchestrator(
        history=signal_history_store,
        alerts=signal_alert_outbox,
        track_record=signal_track_record_store,
    )
    build_session_opportunity_ledger = BuildSessionOpportunityLedger(
        history=signal_history_store,
        track_record=signal_track_record_store,
    )
    publish_signal_opportunity = PublishSignalOpportunity(
        history=signal_history_store,
        outbox=signal_alert_outbox,
    )

    application_runtime = create_stock_analysis_runtime(
        stock_catalog=stock_catalog,
        input_assembler=input_assembler,
        result_store=result_store,
        retry_policy=retry_policy,
        management_audit_store=management_audit_store,
        analysis_run_store=analysis_run_store,
        lifecycle_store=lifecycle_store,
        automatic_retention_policy=AutomaticRetentionPolicy(
            enabled=config.automatic_retention_enabled,
            preservation_days=config.automatic_retention_days,
            batch_limit=config.automatic_retention_batch_limit,
        ),
    )

    has_telegram_token = config.telegram_bot_token is not None
    has_telegram_chat_id = config.telegram_chat_id is not None
    if has_telegram_chat_id and not has_telegram_token:
        raise ValueError("Telegram chat ID requires a bot token")
    if config.telegram_webhook_secret is not None and not config.telegram_webhook_secret.strip():
        raise ValueError("Telegram webhook secret cannot be empty")
    if config.telegram_webhook_secret is not None and not has_telegram_token:
        raise ValueError("Telegram webhook secret requires a bot token")

    telegram_account_link_store = SQLiteTelegramAccountLinkStore(config.analysis_database_path)
    telegram_account_linking = TelegramAccountLinkingService(telegram_account_link_store)
    signal_alert_delivery_store = SQLiteSignalAlertDeliveryStore(config.analysis_database_path)
    telegram_notification_provider = (
        TelegramNotificationProvider(
            config.telegram_bot_token,
            config.telegram_chat_id,
            timeout=config.telegram_timeout_seconds,
        )
        if has_telegram_token and config.telegram_bot_token is not None
        else None
    )
    deliver_alert = None
    deliver_alert_by_symbol = None
    automatic_alert_delivery = None
    run_configured_market_analysis_with_automatic_alert_delivery = None
    automatic_workflow_recovery = None
    recover_durable_scheduled_workflow = None
    workflow_store = SQLiteScheduledWorkflowExecutionStore(config.analysis_database_path)
    get_scheduled_workflow_executions = GetScheduledWorkflowExecutions(workflow_store)
    get_scheduled_workflow_execution_history = GetScheduledWorkflowExecutionHistory(workflow_store)
    get_scheduled_workflow_history = GetScheduledWorkflowHistory(workflow_store)
    dispatch_signal_alert_outbox = None
    if telegram_notification_provider is not None:
        dispatch_signal_alert_outbox = DispatchSignalAlertOutbox(
            outbox=signal_alert_outbox,
            recipients=telegram_account_link_store,
            deliveries=signal_alert_delivery_store,
            users=user_store,
            history=signal_history_store,
            entitlements=entitlement_evaluator,
            transport=telegram_notification_provider,
        )

    if has_telegram_token and has_telegram_chat_id:
        assert telegram_notification_provider is not None
        delivery_store = SQLiteAlertDeliveryStore(config.analysis_database_path)
        deliver_alert = DeliverAlert(
            store=delivery_store,
            provider=telegram_notification_provider,
        )
        deliver_alert_by_symbol = DeliverAlertBySymbol(
            get_alert_candidate=application_runtime.get_alert_candidate,
            deliver_alert=deliver_alert,
        )
        automatic_alert_delivery = AutomaticAlertDelivery(
            get_alert_candidate=application_runtime.get_alert_candidate,
            deliver_alert=deliver_alert,
            default_channel=config.automatic_alert_delivery_channel,
        )
        run_configured_market_analysis_with_automatic_alert_delivery = (
            RunConfiguredMarketAnalysisWithAutomaticAlertDelivery(
                run_configured_market_analysis=application_runtime.run_configured_market_analysis,
                automatic_alert_delivery=automatic_alert_delivery,
            )
        )
        durable_workflow = RunDurableScheduledWorkflow(
            scheduled_operation=run_configured_market_analysis_with_automatic_alert_delivery,
            store=workflow_store,
        )
        recover_workflow = RecoverDurableScheduledWorkflow(
            scheduled_workflow=durable_workflow,
            store=workflow_store,
        )
        recover_durable_scheduled_workflow = recover_workflow
        automatic_workflow_recovery = AutomaticWorkflowRecovery(
            recover_workflow=recover_workflow,
            store=workflow_store,
        )

    return InfrastructureRuntime(
        application_runtime=application_runtime,
        market_data_provider=market_data_provider,
        fundamental_data_provider=fundamental_data_provider,
        deliver_alert=deliver_alert,
        deliver_alert_by_symbol=deliver_alert_by_symbol,
        automatic_alert_delivery=automatic_alert_delivery,
        run_configured_market_analysis_with_automatic_alert_delivery=(
            run_configured_market_analysis_with_automatic_alert_delivery
        ),
        telegram_notification_provider=telegram_notification_provider,
        telegram_account_linking=telegram_account_linking,
        telegram_account_link_store=telegram_account_link_store,
        dispatch_signal_alert_outbox=dispatch_signal_alert_outbox,
        publish_signal_opportunity=publish_signal_opportunity,
        signal_alert_delivery_store=signal_alert_delivery_store,
        telegram_webhook_secret=config.telegram_webhook_secret,
        news_event_store=news_event_store,
        news_ingestion_service=news_ingestion_service,
        subscription_store=subscription_store,
        entitlement_evaluator=entitlement_evaluator,
        automatic_workflow_recovery=automatic_workflow_recovery,
        get_scheduled_workflow_executions=get_scheduled_workflow_executions,
        get_scheduled_workflow_execution_history=get_scheduled_workflow_execution_history,
        get_scheduled_workflow_history=get_scheduled_workflow_history,
        recover_durable_scheduled_workflow=recover_durable_scheduled_workflow,
        authenticator=authenticator,
        credential_service=credential_service,
        user_store=user_store,
        user_management=user_management,
        signal_history_store=signal_history_store,
        signal_track_record_store=signal_track_record_store,
        signal_alert_outbox=signal_alert_outbox,
        signal_lifecycle_orchestrator=signal_lifecycle_orchestrator,
        build_session_opportunity_ledger=build_session_opportunity_ledger,
    )
