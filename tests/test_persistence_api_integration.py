from datetime import date
from decimal import Decimal
from uuid import uuid4

from fastapi.testclient import TestClient

from app.api.main import create_app
from app.application.analysis.stock_analysis import StockAnalysisResult
from app.application.reporting.get_alert_candidate import GetAlertCandidate
from app.application.reporting.get_analysis_report import GetAnalysisReport
from app.application.stocks.catalog import InMemoryStockCatalog
from app.domain.entry_analysis.context import EntryContext
from app.domain.entry_analysis.scoring import EntryQualityScore
from app.domain.fundamental_analysis.growth import GrowthEvidence, GrowthStatus
from app.domain.fundamental_analysis.liquidity import LiquidityEvidence, LiquidityStatus
from app.domain.fundamental_analysis.profitability import (
    ProfitabilityEvidence,
    ProfitabilityStatus,
)
from app.domain.fundamental_analysis.result import FundamentalAnalysisResult
from app.domain.fundamental_analysis.scoring import FundamentalScore, ScoreContribution
from app.domain.market_data.price import Price
from app.domain.market_data.timeframe import Timeframe
from app.domain.opportunity.classification import (
    OpportunityClassification,
    OpportunityClassificationResult,
)
from app.domain.scoring.stock_quality import StockQualityScore
from app.domain.stocks.stock import Stock
from app.domain.technical_analysis.momentum import MomentumEvidence, MomentumStatus
from app.domain.technical_analysis.result import TechnicalAnalysisResult
from app.domain.technical_analysis.scoring import TechnicalScore
from app.domain.technical_analysis.support_resistance import SupportResistanceEvidence
from app.domain.technical_analysis.trend import TrendEvidence, TrendStatus
from app.domain.technical_analysis.volume import VolumeEvidence, VolumeStatus
from app.infrastructure.persistence.sqlite_analysis_result_store import (
    SQLiteAnalysisResultStore,
)


def make_result():
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
        profitability=ProfitabilityEvidence(
            ProfitabilityStatus.PROFITABLE,
            Decimal("0.15"),
        ),
        liquidity=LiquidityEvidence(
            LiquidityStatus.ABOVE_ONE,
            Decimal("1.8"),
        ),
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
    entry_quality = EntryQualityScore(1, 1, 2)

    return StockAnalysisResult(
        technical_analysis=technical,
        fundamental_analysis=fundamental,
        technical_score=technical_score,
        fundamental_score=fundamental_score,
        stock_quality=stock_quality,
        entry_context=EntryContext(
            current_price=Price(Decimal("350.5")),
            nearest_support=None,
            nearest_resistance=None,
        ),
        entry_quality=entry_quality,
        opportunity=OpportunityClassificationResult(
            OpportunityClassification.BUY
        ),
    )


def test_api_report_and_alert_read_persisted_result_after_store_recreation(tmp_path):
    database_path = tmp_path / "analysis.db"
    analysis_date = date(2026, 9, 18)
    stock = Stock.create("EGAL", "Egypt Aluminum")

    first_store = SQLiteAnalysisResultStore(database_path)
    first_store.save("EGAL", make_result(), analysis_date)

    recreated_store = SQLiteAnalysisResultStore(database_path)
    catalog = InMemoryStockCatalog([stock])
    report_capability = GetAnalysisReport(catalog, recreated_store)
    alert_capability = GetAlertCandidate(catalog, recreated_store)
    app = create_app(
        recreated_store,
        get_analysis_report=report_capability,
        get_alert_candidate=alert_capability,
    )

    with TestClient(app) as client:
        report_response = client.get("/api/v1/reports/EGAL")
        alert_response = client.get("/api/v1/alerts/EGAL")

    assert report_response.status_code == 200
    assert report_response.json()["symbol"] == "EGAL"
    assert report_response.json()["analysis_date"] == "2026-09-18"
    assert report_response.json()["opportunity"] == "buy"

    assert alert_response.status_code == 200
    assert alert_response.json() == {
        "stock_id": str(stock.id),
        "classification": "buy",
        "stock_quality_score": 6,
        "entry_quality_score": 2,
    }
