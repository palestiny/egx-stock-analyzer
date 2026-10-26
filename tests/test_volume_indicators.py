from decimal import Decimal

import pytest

from app.domain.technical_analysis.indicators import money_flow_index, on_balance_volume


def d(*items: str) -> list[Decimal]:
    return [Decimal(item) for item in items]


def test_obv_tracks_volume_direction_without_claiming_buy_sell_orders() -> None:
    assert on_balance_volume(d("10", "11", "10", "10"), [100, 50, 30, 20]) == (
        0, 50, 20, 20
    )


def test_obv_rejects_negative_volume() -> None:
    with pytest.raises(ValueError, match="non-negative integers"):
        on_balance_volume(d("10"), [-1])


def test_mfi_aligns_warmup_and_detects_all_positive_money_flow() -> None:
    result = money_flow_index(
        highs=d("10", "11", "12", "13"),
        lows=d("9", "10", "11", "12"),
        closes=d("9.5", "10.5", "11.5", "12.5"),
        volumes=[100, 100, 100, 100],
        period=2,
    )
    assert result[:2] == (None, None)
    assert result[2] == Decimal("100")
    assert result[3] == Decimal("100")


def test_mfi_rejects_misaligned_inputs() -> None:
    with pytest.raises(ValueError, match="equal lengths"):
        money_flow_index(d("10", "11"), d("9"), d("9.5", "10.5"), [10, 10], period=1)
