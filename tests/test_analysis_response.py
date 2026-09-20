from unittest.mock import Mock

from app.api.analysis_response import AnalysisResultResponse
from app.application.analysis.stock_analysis import StockAnalysisResult
from app.domain.entry_analysis.scoring import EntryQualityScore
from app.domain.fundamental_analysis.scoring import FundamentalScore
from app.domain.opportunity.classification import OpportunityClassification, OpportunityClassificationResult
from app.domain.scoring.stock_quality import StockQualityScore
from app.domain.technical_analysis.scoring import TechnicalScore


def test_analysis_result_response_maps_analysis_scores():
    result = Mock(spec=StockAnalysisResult)
    result.technical_score = TechnicalScore(1, 0, -1, 0)
    result.fundamental_score = FundamentalScore(2, ())
    result.stock_quality = StockQualityScore(
        fundamental_score=result.fundamental_score,
        technical_score=result.technical_score,
        total_score=2,
    )
    result.entry_quality = EntryQualityScore(1, 0, 1)
    result.opportunity = OpportunityClassificationResult(OpportunityClassification.BUY)

    response = AnalysisResultResponse.from_result("EGAL", result)

    assert response.symbol == "EGAL"
    assert response.technical_score == 0
    assert response.fundamental_score == 2
    assert response.stock_quality == 2
    assert response.entry_quality == 1
    assert response.opportunity == "buy"
