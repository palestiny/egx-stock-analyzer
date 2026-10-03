from datetime import datetime, timezone
from decimal import Decimal

import pytest

from app.domain.signals import (
    PriceZone,
    Signal,
    SignalDirection,
    SignalEvidence,
    SignalStatus,
    Target,
)


def make_signal(**overrides: object) -> Signal:
    generated = datetime(2026, 10, 4, 10, 0, tzinfo=timezone.utc)
    values = {
        "symbol": "COMI",
        "direction": SignalDirection.BUY,
        "status": SignalStatus.ACTIVE,
        "generated_at": generated,
        "timeframe": "1D",
        "entry_zone": PriceZone(Decimal("130"), Decimal("132")),
        "invalidation": Decimal("127"),
        "targets": (Target(Decimal("136"), "TP1"),),
        "confidence": Decimal("82"),
        "risk_score": Decimal("34"),
        "evidence": (
            SignalEvidence("trend", "Bullish trend"),
            SignalEvidence("volume", "Volume confirmation"),
        ),
        "strategy_id": "confluence-v1",
        "strategy_version": "1.0.0",
        "data_timestamp": generated,
    }
    values.update(overrides)
    return Signal(**values)


def test_signal_preserves_canonical_decision_payload() -> None:
    signal = make_signal()

    assert signal.symbol == "COMI"
    assert signal.direction is SignalDirection.BUY
    assert signal.entry_zone.lower == Decimal("130")
    assert signal.targets[0].label == "TP1"
    assert signal.strategy_id == "confluence-v1"


@pytest.mark.parametrize(
    "field,value",
    [
        ("confidence", Decimal("-1")),
        ("confidence", Decimal("101")),
        ("risk_score", Decimal("-1")),
        ("risk_score", Decimal("101")),
    ],
)
def test_signal_rejects_invalid_scores(field: str, value: Decimal) -> None:
    with pytest.raises(ValueError):
        make_signal(**{field: value})


def test_signal_rejects_future_data_timestamp() -> None:
    generated = datetime(2026, 10, 4, 10, 0, tzinfo=timezone.utc)

    with pytest.raises(ValueError):
        make_signal(
            generated_at=generated,
            data_timestamp=datetime(2026, 10, 4, 10, 1, tzinfo=timezone.utc),
        )


def test_price_zone_rejects_reversed_bounds() -> None:
    with pytest.raises(ValueError):
        PriceZone(Decimal("132"), Decimal("130"))
