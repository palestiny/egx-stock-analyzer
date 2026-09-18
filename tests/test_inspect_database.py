from app.infrastructure.persistence.inspect_database import inspect_database


def test_inspect_database_reports_empty_database(tmp_path, capsys):
    database_path = tmp_path / "analysis.db"

    from app.infrastructure.persistence.sqlite_analysis_result_store import (
        SQLiteAnalysisResultStore,
    )

    SQLiteAnalysisResultStore(database_path)

    assert inspect_database(str(database_path)) == 0
    output = capsys.readouterr().out

    assert f"Database: {database_path}" in output
    assert "Records: 0" in output


def test_inspect_database_reports_persisted_result(tmp_path, capsys):
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
    from app.domain.fundamental_analysis.scoring import FundamentalScore
    from app.domain.market_data.price import Price
    from app.domain.opportunity.classification import (
        OpportunityClassification,
        OpportunityClassificationResult,
    )
    from app.domain.scoring.stock_quality import StockQualityScore
    from app.domain.technical_analysis.momentum import MomentumEvidence, MomentumStatus
    from app.domain.technical_analysis.result import TechnicalAnalysisResult
    from app.domain.technical_analysis.support_resistance import SupportResistanceEvidence
    from app.domain.technical_analysis.trend import TrendEvidence, TrendStatus
    from app.domain.technical_analysis.volume import VolumeEvidence, VolumeStatus
    from app.domain.technical_analysis.scoring import TechnicalScore
    from app.domain.market_data.timeframe import Timeframe
    from app.infrastructure.persistence.sqlite_analysis_result_store import (
        SQLiteAnalysisResultStore,
    )

    stock_id = uuid4()
    technical = TechnicalAnalysisResult(
        stock_id=stock_id,
        timeframe=Timeframe.DAILY,
        trend=TrendEvidence(TrendStatus.UPTREND),
        support_resistance=SupportResistanceEvidence((), ()),
        momentum=MomentumEvidence(MomentumStatus.POSITIVE),
        volume=VolumeEvidence(VolumeStatus.ABOVE_AVERAGE),
    )
    fundamental = FundamentalAnalysisResult(
        stock_id=stock_id,
        period_end=date(2026, 9, 18),
        profitability=ProfitabilityEvidence(ProfitabilityStatus.PROFITABLE),
        liquidity=LiquidityEvidence(LiquidityStatus.ABOVE_ONE),
        growth=GrowthEvidence(GrowthStatus.POSITIVE),
    )
    technical_score = TechnicalScore(1, 1, 1, 3)
    fundamental_score = FundamentalScore(total=2, contributions=())
    result = StockAnalysisResult(
        technical_analysis=technical,
        fundamental_analysis=fundamental,
        technical_score=technical_score,
        fundamental_score=fundamental_score,
        stock_quality=StockQualityScore(
            fundamental_score=fundamental_score,
            technical_score=technical_score,
            total_score=5,
        ),
        entry_context=EntryContext(
            current_price=Price(Decimal("350.5")),
            nearest_support=None,
            nearest_resistance=None,
        ),
        entry_quality=EntryQualityScore(1, 1, 1),
        opportunity=OpportunityClassificationResult(
            OpportunityClassification.BUY
        ),
    )

    database_path = tmp_path / "analysis.db"
    store = SQLiteAnalysisResultStore(database_path)
    store.save("EGAL", result, date(2026, 9, 18))

    assert inspect_database(str(database_path), "EGAL") == 0
    output = capsys.readouterr().out

    assert "Records: 1" in output
    assert "EGAL" in output
    assert "Analysis date:    2026-09-18" in output
    assert "Technical score:  3" in output
    assert "Fundamental:      2" in output
    assert "Stock quality:    5" in output
    assert "Entry quality:    3" in output
    assert "Opportunity:      buy" in output
    assert "Current price:    350.5" in output
