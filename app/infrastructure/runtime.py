from dataclasses import dataclass, field

from app.application.analysis.input_assembler import AnalysisInputAssembler
from app.application.analysis.result_store import (
    AnalysisResultStore,
)
from app.application.analysis.runtime import (
    StockAnalysisRuntime,
    create_stock_analysis_runtime,
)
from app.application.execution.retry import RetryPolicy
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
from app.infrastructure.persistence.sqlite_analysis_result_store import (
    SQLiteAnalysisResultStore,
)


@dataclass
class InfrastructureRuntime:
    application_runtime: StockAnalysisRuntime
    market_data_provider: YahooFinanceAdapter
    fundamental_data_provider: YahooFinanceFundamentalDataSource
    deliver_alert: DeliverAlert | None = None
    deliver_alert_by_symbol: DeliverAlertBySymbol | None = None
    telegram_notification_provider: TelegramNotificationProvider | None = None
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
) -> InfrastructureRuntime:
    result_store = result_store or SQLiteAnalysisResultStore(config.analysis_database_path)
    retry_policy = retry_policy or RetryPolicy(1)

    yahoo_history_client = YahooFinanceHistoryClient(yfinance_module)
    market_data_provider = YahooFinanceAdapter(yahoo_history_client)
    fundamental_data_provider = YahooFinanceFundamentalDataSource(yfinance_module)

    input_assembler = AnalysisInputAssembler(
        market_data_provider=market_data_provider,
        fundamental_data_provider=fundamental_data_provider,
    )

    application_runtime = create_stock_analysis_runtime(
        stock_catalog=stock_catalog,
        input_assembler=input_assembler,
        result_store=result_store,
        retry_policy=retry_policy,
    )

    has_telegram_token = config.telegram_bot_token is not None
    has_telegram_chat_id = config.telegram_chat_id is not None
    if has_telegram_token != has_telegram_chat_id:
        raise ValueError(
            "Telegram bot token and chat ID must be configured together"
        )

    telegram_notification_provider = None
    deliver_alert = None
    deliver_alert_by_symbol = None
    if has_telegram_token and has_telegram_chat_id:
        telegram_notification_provider = TelegramNotificationProvider(
            config.telegram_bot_token,
            config.telegram_chat_id,
            timeout=config.telegram_timeout_seconds,
        )
        delivery_store = SQLiteAlertDeliveryStore(config.analysis_database_path)
        deliver_alert = DeliverAlert(
            store=delivery_store,
            provider=telegram_notification_provider,
        )
        deliver_alert_by_symbol = DeliverAlertBySymbol(
            get_alert_candidate=application_runtime.get_alert_candidate,
            deliver_alert=deliver_alert,
        )

    return InfrastructureRuntime(
        application_runtime=application_runtime,
        market_data_provider=market_data_provider,
        fundamental_data_provider=fundamental_data_provider,
        deliver_alert=deliver_alert,
        deliver_alert_by_symbol=deliver_alert_by_symbol,
        telegram_notification_provider=telegram_notification_provider,
    )
