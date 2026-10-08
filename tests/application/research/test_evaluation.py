from datetime import datetime, timezone
from decimal import Decimal
import pytest
from app.domain.research.dataset import ResearchBar, ResearchCostConfig
from app.application.research.evaluation import evaluate_exit_bar, next_open_entry


def bar(day, *, open="100", high="105", low="95", close="102"):
    ts = datetime(2026, 10, day, tzinfo=timezone.utc)
    return ResearchBar("COMI", "1d", ts, ts, Decimal(open), Decimal(high), Decimal(low), Decimal(close), Decimal("1000"), "fixture", "v1")

ZERO = ResearchCostConfig(Decimal("0"), Decimal("0"))

def test_next_open_uses_following_bar_not_decision_close():
    fill = next_open_entry((bar(6, close="103"), bar(7, open="108")), 0, side="LONG", costs=ZERO)
    assert fill.reference_price == Decimal("108")
    assert fill.fill_timestamp > fill.decision_timestamp

def test_missing_next_bar_has_no_fill():
    assert next_open_entry((bar(6),), 0, side="LONG", costs=ZERO) is None

def test_long_entry_slippage_is_adverse():
    costs = ResearchCostConfig(Decimal("0.001"), Decimal("0.01"))
    fill = next_open_entry((bar(6), bar(7)), 0, side="LONG", costs=costs)
    assert fill.fill_price == Decimal("101.00")
    assert fill.commission == Decimal("0.10100")

def test_same_bar_target_and_stop_uses_invalidation_first():
    result = evaluate_exit_bar(bar(7, open="100", high="112", low="88"), side="LONG", target=Decimal("110"), invalidation=Decimal("90"), entry_price=Decimal("100"), costs=ZERO)
    assert result.reason == "INVALIDATION"
    assert result.exit_price == Decimal("90")

def test_gap_through_long_stop_exits_at_open():
    result = evaluate_exit_bar(bar(7, open="85", high="92", low="80"), side="LONG", target=Decimal("110"), invalidation=Decimal("90"), entry_price=Decimal("100"), costs=ZERO)
    assert result.exit_price == Decimal("85")

def test_exit_costs_reduce_net_return():
    result = evaluate_exit_bar(bar(7, open="100", high="112", low="96"), side="LONG", target=Decimal("110"), invalidation=Decimal("90"), entry_price=Decimal("100"), costs=ResearchCostConfig(Decimal("0.01"), Decimal("0.01")))
    assert result.reason == "TARGET"
    assert result.net_return < result.gross_return

def test_rejects_invalid_side():
    with pytest.raises(ValueError, match="side"):
        next_open_entry((bar(6), bar(7)), 0, side="BUY", costs=ZERO)
