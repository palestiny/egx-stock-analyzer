from decimal import Decimal
from types import SimpleNamespace

from app.application.analysis.result_store import InMemoryAnalysisResultStore
from app.application.market_intelligence.scan_fibonacci import ScanFibonacciOpportunities


def _result(price: str, score: int) -> SimpleNamespace:
    return SimpleNamespace(
        entry_context=SimpleNamespace(
            current_price=SimpleNamespace(value=Decimal(price))
        ),
        stock_quality=SimpleNamespace(total_score=score),
    )


def test_finds_nearby_fibonacci_level():
    store = InMemoryAnalysisResultStore()
    store.save("COMI", _result("100", 90))
    store.save("EGAL", _result("110", 80))

    result = ScanFibonacciOpportunities(store).execute(
        {"COMI": Decimal("100.5"), "EGAL": Decimal("120")}
    )

    assert [item.symbol for item in result.opportunities] == ["COMI"]
    assert result.metric == "distance_to_fibonacci_level_percent"


def test_orders_by_distance_then_score():
    store = InMemoryAnalysisResultStore()
    store.save("COMI", _result("100", 80))
    store.save("AIDC", _result("100", 90))

    result = ScanFibonacciOpportunities(store).execute(
        {"COMI": Decimal("100.5"), "AIDC": Decimal("100.5")}
    )

    assert [item.symbol for item in result.opportunities] == ["AIDC", "COMI"]
