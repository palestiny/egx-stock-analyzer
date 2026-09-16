from datetime import date, datetime, timezone
from decimal import Decimal
from uuid import uuid4

from app.domain.entry_analysis.context import EntryContext
from app.domain.entry_analysis.scoring import EntryQualityScore
from app.domain.fundamental_analysis.financial_period import FinancialPeriod
from app.domain.fundamental_analysis.growth import GrowthEvidence, GrowthStatus
from app.domain.fundamental_analysis.liquidity import LiquidityEvidence, LiquidityStatus
from app.domain.fundamental_analysis.profitability import ProfitabilityEvidence, ProfitabilityStatus
from app.domain.fundamental_analysis.result import FundamentalAnalysisResult
from app.domain.market_data.price import Price
from app.domain.market_data.timeframe import Timeframe
from app.domain.opportunity.classification import (
    OpportunityClassification,
    OpportunityClassificationResult,
)
from app.domain.scoring.stock_quality import StockQualityScore
from app.domain.technical_analysis.momentum import MomentumEvidence, MomentumStatus
from app.domain.technical_analysis.result import TechnicalAnalysisResult
from app.domain.technical_analysis.scoring import TechnicalScore
from app.domain.technical_analysis.support_resistance import SupportResistanceEvidence
from app.domain.technical_analysis.trend import TrendEvidence, TrendStatus
from app.domain.technical_analysis.volume import VolumeEvidence, VolumeStatus
from app.domain.reporting.report import AnalysisReport


STOCK_ID = uuid4()
ANALYSIS_DATE = date(2026, 9, 16)


def build_fundamental_result() -> FundamentalAnalysisResult:
    period = FinancialPeriod(
        period_end=ANALYSIS_DATE,
        revenue=Decimal("1000"),
        net_income=Decimal("100"),
        current_assets=Decimal("500"),
        current_liabilities=Decimal("250"),
    )

    return FundamentalAnalysisResult(
        stock_id=STOCK_ID,
        period_end=period.period_end,
        profitability=ProfitabilityEvidence(ProfitabilityStatus.PROFITABLE),
        liquidity=LiquidityEvidence(LiquidityStatus.ABOVE_ONE),
        growth=GrowthEvidence(GrowthStatus.POSITIVE, Decimal("0.10")),
    )


def build_technical_result() -> TechnicalAnalysisResult:
    return TechnicalAnalysisResult(
        stock_id=STOCK_ID,
        timeframe=Timeframe.DAILY,
        trend=TrendEvidence(TrendStatus.UPTREND),
        support_resistance=SupportResistanceEvidence((), ()),
        momentum=MomentumEvidence(MomentumStatus.POSITIVE, Decimal("5")),
        volume=VolumeEvidence(VolumeStatus.ABOVE_AVERAGE, Decimal("1.5")),
    )


def build_stock_quality() -> StockQualityScore:
    return StockQualityScore(
        fundamental_score=None,
        technical_score=None,
        total_score=5,
    )


def build_entry_context() -> EntryContext:
    return EntryContext(
        current_price=Price(Decimal("100")),
        nearest_support=None,
        nearest_resistance=None,
    )


def test_analysis_report_preserves_supplied_results_without_recalculation():
    fundamental = build_fundamental_result()
    technical = build_technical_result()
    stock_quality = build_stock_quality()
    entry_context = build_entry_context()
    entry_quality = EntryQualityScore(1, 1, 2)
    classification = OpportunityClassificationResult(OpportunityClassification.BUY)

    report = AnalysisReport.create(
        stock_id=STOCK_ID,
        stock_symbol="EGAL",
        analysis_date=ANALYSIS_DATE,
        technical_analysis=technical,
        fundamental_analysis=fundamental,
        stock_quality=stock_quality,
        entry_context=entry_context,
        entry_quality=entry_quality,
        classification=classification,
    )

    assert report.stock_id == STOCK_ID
    assert report.stock_symbol == "EGAL"
    assert report.analysis_date == ANALYSIS_DATE
    assert report.technical_analysis is technical
    assert report.fundamental_analysis is fundamental
    assert report.stock_quality is stock_quality
    assert report.entry_context is entry_context
    assert report.entry_quality is entry_quality
    assert report.classification is classification


def test_analysis_report_is_immutable():
    report = AnalysisReport.create(
        stock_id=STOCK_ID,
        stock_symbol="EGAL",
        analysis_date=ANALYSIS_DATE,
        technical_analysis=build_technical_result(),
        fundamental_analysis=build_fundamental_result(),
        stock_quality=build_stock_quality(),
        entry_context=build_entry_context(),
        entry_quality=EntryQualityScore(1, 1, 2),
        classification=OpportunityClassificationResult(OpportunityClassification.BUY),
    )

    try:
        report.stock_symbol = "IEEC"
    except Exception:
        pass
    else:
        raise AssertionError("AnalysisReport must be immutable")


def test_analysis_report_is_deterministic_for_same_inputs():
    kwargs = dict(
        stock_id=STOCK_ID,
        stock_symbol="EGAL",
        analysis_date=ANALYSIS_DATE,
        technical_analysis=build_technical_result(),
        fundamental_analysis=build_fundamental_result(),
        stock_quality=build_stock_quality(),
        entry_context=build_entry_context(),
        entry_quality=EntryQualityScore(1, 1, 2),
        classification=OpportunityClassificationResult(OpportunityClassification.BUY),
    )

    first = AnalysisReport.create(**kwargs)
    second = AnalysisReport.create(**kwargs)

    assert first == second
