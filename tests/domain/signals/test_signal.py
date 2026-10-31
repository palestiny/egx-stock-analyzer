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


@pytest.mark.parametrize(
    "lower,upper",
    [
        (Decimal("NaN"), Decimal("132")),
        (Decimal("130"), Decimal("Infinity")),
        (Decimal("-Infinity"), Decimal("132")),
    ],
)
def test_price_zone_rejects_non_finite_bounds(lower: Decimal, upper: Decimal) -> None:
    with pytest.raises(ValueError, match="finite"):
        PriceZone(lower, upper)


@pytest.mark.parametrize("price", [Decimal("NaN"), Decimal("Infinity"), Decimal("-Infinity")])
def test_target_rejects_non_finite_price(price: Decimal) -> None:
    with pytest.raises(ValueError, match="finite"):
        Target(price, "TP1")


@pytest.mark.parametrize("weight", [Decimal("NaN"), Decimal("Infinity"), Decimal("-Infinity")])
def test_signal_evidence_rejects_non_finite_weight(weight: Decimal) -> None:
    with pytest.raises(ValueError, match="finite"):
        SignalEvidence("volume", "Volume confirmation", weight)


@pytest.mark.parametrize(
    "field,value",
    [
        ("invalidation", Decimal("NaN")),
        ("invalidation", Decimal("Infinity")),
        ("confidence", Decimal("NaN")),
        ("confidence", Decimal("Infinity")),
        ("risk_score", Decimal("NaN")),
        ("risk_score", Decimal("Infinity")),
    ],
)
def test_signal_rejects_non_finite_numeric_fields(field: str, value: Decimal) -> None:
    with pytest.raises(ValueError, match="finite"):
        make_signal(**{field: value})


@pytest.mark.parametrize("field", ["generated_at", "data_timestamp"])
def test_signal_requires_timezone_aware_timestamps(field: str) -> None:
    with pytest.raises(ValueError, match="timezone-aware"):
        make_signal(**{field: datetime(2026, 10, 4, 10, 0)})
