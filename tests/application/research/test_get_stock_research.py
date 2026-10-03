from datetime import date
from decimal import Decimal
from unittest.mock import Mock
from uuid import uuid4

import pytest

from app.application.research.get_stock_research import (
    GetStockResearch,
    StockResearchNotFoundError,
)
from app.domain.entry_analysis.context import EntryContext
from app.domain.fundamental_analysis.result import FundamentalAnalysisResult
from app.domain.opportunity.classification import (
    OpportunityClassification,
    OpportunityClassificationResult,
)
from app.domain.reporting.report import AnalysisReport
from app.domain.technical_analysis.momentum import MomentumEvidence, MomentumStatus
from app.domain.technical_analysis.result import TechnicalAnalysisResult
from app.domain.technical_analysis.support_resistance import PriceLevelEvidence, SupportResistanceEvidence
from app.domain.technical_analysis.trend import TrendEvidence, TrendStatus
from app.domain.technical_analysis.volume import VolumeEvidence, VolumeStatus
from app.domain.market_data.timeframe import Timeframe
from app.domain.market_data.price import Price


def _report() -> AnalysisReport:
    stock_id = uuid4()
    technical = TechnicalAnalysisResult(
        stock_id=stock_id,
        timeframe=Timeframe.DAILY,
        trend=TrendEvidence(TrendStatus.UPTREND),
        support_resistance=SupportResistanceEvidence(
            support_levels=(PriceLevelEvidence(Price(Decimal("98")), datetime_from_date()),),
            resistance_levels=(PriceLevelEvidence(Price(Decimal("110")), datetime_from_date()),),
        ),
        momentum=MomentumEvidence(MomentumStatus.POSITIVE, Decimal("3.5")),
        volume=VolumeEvidence(VolumeStatus.ABOVE_AVERAGE, Decimal("1.4")),
    )
    fundamental = Mock(spec=FundamentalAnalysisResult)
    fundamental.profitability = {"status": "positive"}
    fundamental.liquidity = {"status": "healthy"}
    fundamental.growth = {"status": "positive"}
    return AnalysisReport.create(
        stock_id=stock_id,
        stock_symbol="COMI",
        analysis_date=date(2026, 10, 3),
        technical_analysis=technical,
        fundamental_analysis=fundamental,
        stock_quality=Mock(total_score=5),
        entry_context=EntryContext(
            current_price=Price(Decimal("105")),
            nearest_support=technical.support_resistance.support_levels[0],
            nearest_resistance=technical.support_resistance.resistance_levels[0],
        ),
        entry_quality=Mock(total_score=2),
        classification=OpportunityClassificationResult(OpportunityClassification.BUY),
    )


def datetime_from_date():
    from datetime import datetime
    return datetime(2026, 10, 3)


def test_maps_analysis_report_to_decision_ready_stock_research():
    provider = Mock()
    provider.execute.return_value = _report()

    view = GetStockResearch(provider).execute(" comi ")

    assert view.symbol == "COMI"
    assert view.classification is OpportunityClassification.BUY
    assert view.current_price == Decimal("105")
    assert view.nearest_support == Decimal("98")
    assert view.nearest_resistance == Decimal("110")
    assert view.trend == "uptrend"
    assert view.momentum_rate_of_change == Decimal("3.5")
    assert view.volume_ratio == Decimal("1.4")


def test_missing_report_is_explicit():
    provider = Mock()
    provider.execute.return_value = None

    with pytest.raises(StockResearchNotFoundError):
        GetStockResearch(provider).execute("COMI")
