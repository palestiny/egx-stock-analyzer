from decimal import Decimal

from app.api.technical_scanner_response import TechnicalScannerResponse
from app.domain.market_intelligence.scanner import (
    ScannerCriterion,
    ScannerMatch,
    TechnicalScannerResult,
)


def test_response_exposes_pre_breakout_evidence():
    result = TechnicalScannerResult(
        scanner_id="pre-breakout-momentum-volume",
        matches=(
            ScannerMatch(
                symbol="COMI",
                score=82,
                criteria=(
                    ScannerCriterion.POSITIVE_MOMENTUM,
                    ScannerCriterion.VOLUME_EXPANSION,
                    ScannerCriterion.NEAR_RESISTANCE,
                ),
                momentum_percent=Decimal("4.2"),
                volume_ratio=Decimal("1.8"),
                resistance_price=Decimal("100"),
                distance_to_resistance_percent=Decimal("-4"),
            ),
        ),
        evaluated_symbols=1,
        data_status="HISTORICAL_ANALYSIS_RESULT",
    )

    response = TechnicalScannerResponse.from_result(result).to_dict()

    assert response["matches"][0] == {
        "symbol": "COMI",
        "score": 82,
        "criteria": ["positive_momentum", "volume_expansion", "near_resistance"],
        "momentum_percent": Decimal("4.2"),
        "volume_ratio": Decimal("1.8"),
        "resistance_price": Decimal("100"),
        "distance_to_resistance_percent": Decimal("-4"),
    }
