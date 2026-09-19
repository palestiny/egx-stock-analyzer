from datetime import date

from app.application.analysis.result_store import InMemoryAnalysisResultStore
from app.application.analysis.runtime import StockAnalysisRuntime
from app.application.execution.retry import RetryPolicy
from app.application.stocks.catalog import InMemoryStockCatalog
from app.domain.stocks.stock import Stock
from app.infrastructure.config import InfrastructureConfig
from app.infrastructure.market_data.yahoo_finance import (
    YahooFinanceAdapter,
    YahooFinanceFundamentalDataSource,
)
from app.infrastructure.persistence.sqlite_analysis_result_store import SQLiteAnalysisResultStore
from app.infrastructure.runtime import InfrastructureRuntime, create_infrastructure_runtime


class FakeYFinanceModule:
    pass


def test_create_infrastructure_runtime_composes_real_adapters() -> None:
    stock = Stock.create("EGAL", "Egypt Aluminum")

    runtime = create_infrastructure_runtime(
        stock_catalog=InMemoryStockCatalog([stock]),
        yfinance_module=FakeYFinanceModule(),
        config=InfrastructureConfig(operator_token="test-token", ),
        result_store=InMemoryAnalysisResultStore(),
        retry_policy=RetryPolicy(1),
    )

    assert isinstance(runtime, InfrastructureRuntime)
    assert isinstance(runtime.application_runtime, StockAnalysisRuntime)
    assert isinstance(runtime.market_data_provider, YahooFinanceAdapter)
    assert isinstance(
        runtime.fundamental_data_provider,
        YahooFinanceFundamentalDataSource,
    )

    runtime.close()


def test_infrastructure_runtime_owns_shared_result_store() -> None:
    stock = Stock.create("EGAL", "Egypt Aluminum")
    result_store = InMemoryAnalysisResultStore()

    runtime = create_infrastructure_runtime(
        stock_catalog=InMemoryStockCatalog([stock]),
        yfinance_module=FakeYFinanceModule(),
        config=InfrastructureConfig(operator_token="test-token", ),
        result_store=result_store,
        retry_policy=RetryPolicy(1),
    )

    assert runtime.application_runtime.result_store is result_store
    runtime.close()


def test_infrastructure_runtime_close_is_idempotent() -> None:
    stock = Stock.create("EGAL", "Egypt Aluminum")
    runtime = create_infrastructure_runtime(
        stock_catalog=InMemoryStockCatalog([stock]),
        yfinance_module=FakeYFinanceModule(),
        config=InfrastructureConfig(operator_token="test-token", ),
    )

    assert runtime.closed is False
    runtime.close()
    assert runtime.closed is True
    runtime.close()
    assert runtime.closed is True



def _make_persisted_result():
    from datetime import date
    from decimal import Decimal
    from uuid import uuid4

    from app.application.analysis.stock_analysis import StockAnalysisResult
    from app.domain.entry_analysis.context import EntryContext
    from app.domain.entry_analysis.scoring import EntryQualityScore
    from app.domain.fundamental_analysis.growth import GrowthEvidence, GrowthStatus
    from app.domain.fundamental_analysis.liquidity import LiquidityEvidence, LiquidityStatus
    from app.domain.fundamental_analysis.profitability import ProfitabilityEvidence, ProfitabilityStatus
    from app.domain.fundamental_analysis.result import FundamentalAnalysisResult
    from app.domain.fundamental_analysis.scoring import FundamentalScore, ScoreContribution
    from app.domain.market_data.price import Price
    from app.domain.market_data.timeframe import Timeframe
    from app.domain.opportunity.classification import OpportunityClassification, OpportunityClassificationResult
    from app.domain.scoring.stock_quality import StockQualityScore
    from app.domain.technical_analysis.momentum import MomentumEvidence, MomentumStatus
    from app.domain.technical_analysis.result import TechnicalAnalysisResult
    from app.domain.technical_analysis.scoring import TechnicalScore
    from app.domain.technical_analysis.support_resistance import SupportResistanceEvidence
    from app.domain.technical_analysis.trend import TrendEvidence, TrendStatus
    from app.domain.technical_analysis.volume import VolumeEvidence, VolumeStatus

    stock_id = uuid4()
    technical = TechnicalAnalysisResult(
        stock_id=stock_id,
        timeframe=Timeframe.DAILY,
        trend=TrendEvidence(TrendStatus.UPTREND),
        support_resistance=SupportResistanceEvidence((), ()),
        momentum=MomentumEvidence(MomentumStatus.POSITIVE, Decimal("2.5")),
        volume=VolumeEvidence(VolumeStatus.ABOVE_AVERAGE, Decimal("1.25")),
    )
    fundamental = FundamentalAnalysisResult(
        stock_id=stock_id,
        period_end=date(2026, 9, 17),
        profitability=ProfitabilityEvidence(ProfitabilityStatus.PROFITABLE, Decimal("0.15")),
        liquidity=LiquidityEvidence(LiquidityStatus.ABOVE_ONE, Decimal("1.8")),
        growth=GrowthEvidence(GrowthStatus.POSITIVE, Decimal("0.2")),
    )
    technical_score = TechnicalScore(1, 1, 1, 3)
    fundamental_score = FundamentalScore(
        total=3,
        contributions=(
            ScoreContribution("profitability", 1),
            ScoreContribution("liquidity", 1),
            ScoreContribution("growth", 1),
        ),
    )
    stock_quality = StockQualityScore(
        fundamental_score=fundamental_score,
        technical_score=technical_score,
        total_score=6,
    )
    return StockAnalysisResult(
        technical_analysis=technical,
        fundamental_analysis=fundamental,
        technical_score=technical_score,
        fundamental_score=fundamental_score,
        stock_quality=stock_quality,
        entry_context=EntryContext(current_price=Price(Decimal("350.5")), nearest_support=None, nearest_resistance=None),
        entry_quality=EntryQualityScore(1, 1, 2),
        opportunity=OpportunityClassificationResult(OpportunityClassification.BUY),
    )

def test_infrastructure_runtime_uses_sqlite_store_by_default(tmp_path) -> None:
    stock = Stock.create("EGAL", "Egypt Aluminum")
    database_path = tmp_path / "analysis.db"

    runtime = create_infrastructure_runtime(
        stock_catalog=InMemoryStockCatalog([stock]),
        yfinance_module=FakeYFinanceModule(),
        config=InfrastructureConfig(operator_token="test-token", analysis_database_path=str(database_path)),
    )

    assert isinstance(
        runtime.application_runtime.result_store,
        SQLiteAnalysisResultStore,
    )
    assert database_path.exists()
    runtime.close()


def test_infrastructure_runtime_persists_analysis_across_runtime_recreation(tmp_path) -> None:
    stock = Stock.create("EGAL", "Egypt Aluminum")
    database_path = tmp_path / "analysis.db"
    config = InfrastructureConfig(operator_token="test-token", analysis_database_path=str(database_path))

    first_runtime = create_infrastructure_runtime(
        stock_catalog=InMemoryStockCatalog([stock]),
        yfinance_module=FakeYFinanceModule(),
        config=config,
    )
    first_result_store = first_runtime.application_runtime.result_store
    first_result_store.save("EGAL", _make_persisted_result(), date(2026, 9, 18))
    first_runtime.close()

    second_runtime = create_infrastructure_runtime(
        stock_catalog=InMemoryStockCatalog([stock]),
        yfinance_module=FakeYFinanceModule(),
        config=config,
    )

    assert second_runtime.application_runtime.result_store.get("EGAL") is not None
    record = second_runtime.application_runtime.result_store.get_record("EGAL")
    assert record is not None
    assert record.analysis_date == date(2026, 9, 18)
    second_runtime.close()


def test_infrastructure_runtime_composes_telegram_delivery_when_configured() -> None:
    from app.application.execution.run_configured_market_analysis_with_automatic_alert_delivery import RunConfiguredMarketAnalysisWithAutomaticAlertDelivery
    from app.application.notifications.deliver_alert import DeliverAlert
    from app.infrastructure.notifications.telegram_provider import TelegramNotificationProvider

    stock = Stock.create("EGAL", "Egypt Aluminum")
    runtime = create_infrastructure_runtime(
        stock_catalog=InMemoryStockCatalog([stock]),
        yfinance_module=FakeYFinanceModule(),
        config=InfrastructureConfig(operator_token="test-token", 
            telegram_bot_token="token",
            telegram_chat_id="chat",
        ),
        result_store=InMemoryAnalysisResultStore(),
        retry_policy=RetryPolicy(1),
    )

    assert isinstance(runtime.telegram_notification_provider, TelegramNotificationProvider)
    assert isinstance(runtime.deliver_alert, DeliverAlert)
    assert isinstance(
        runtime.run_configured_market_analysis_with_automatic_alert_delivery,
        RunConfiguredMarketAnalysisWithAutomaticAlertDelivery,
    )
    runtime.close()


def test_infrastructure_runtime_rejects_partial_telegram_configuration() -> None:
    stock = Stock.create("EGAL", "Egypt Aluminum")

    try:
        create_infrastructure_runtime(
            stock_catalog=InMemoryStockCatalog([stock]),
            yfinance_module=FakeYFinanceModule(),
            config=InfrastructureConfig(operator_token="test-token", telegram_bot_token="token"),
            result_store=InMemoryAnalysisResultStore(),
            retry_policy=RetryPolicy(1),
        )
    except ValueError as error:
        assert str(error) == "Telegram bot token and chat ID must be configured together"
    else:
        raise AssertionError("Expected ValueError")


def test_infrastructure_runtime_requires_operator_token() -> None:
    stock = Stock.create("EGAL", "Egypt Aluminum")

    try:
        create_infrastructure_runtime(
            stock_catalog=InMemoryStockCatalog([stock]),
            yfinance_module=FakeYFinanceModule(),
            config=InfrastructureConfig(operator_token=None),
            result_store=InMemoryAnalysisResultStore(),
            retry_policy=RetryPolicy(1),
        )
    except ValueError as error:
        assert str(error) == "EGX_OPERATOR_TOKEN must be configured"
    else:
        raise AssertionError("Expected ValueError")
