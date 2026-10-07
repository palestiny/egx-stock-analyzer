from datetime import datetime, timedelta, timezone
from decimal import Decimal
from uuid import uuid4

from app.domain.market_data.price import Price
from app.domain.market_data.price_bar import PriceBar
from app.domain.market_data.timeframe import Timeframe
from app.domain.market_data.volume import Volume
from app.domain.market_intelligence.stress import (
    CrashRadarAnalyzer,
    CrashRadarSignal,
    MarketStressAnalyzer,
    StressLevel,
)


def make_bars(*, start_price: str, returns: list[str], volumes: list[int]):
    stock_id = uuid4()
    bars = [
        PriceBar.create(
            stock_id=stock_id,
            timeframe=Timeframe.DAILY,
            timestamp=datetime(2025, 1, 1, tzinfo=timezone.utc) + timedelta(days=index),
            open=Price(price),
            high=Price(price),
            low=Price(price),
            close=Price(price),
            volume=Volume(volumes[index]),
        )
        for index, price in enumerate(
            [Decimal(start_price)]
            + [
                Decimal(start_price)
                * __import__("functools").reduce(
                    lambda value, ret: value * (Decimal("1") + Decimal(ret)),
                    returns[: index + 1],
                    Decimal("1"),
                )
                for index in range(len(returns))
            ]
        )
    ]
    return stock_id, bars


def test_crash_radar_identifies_negative_move_with_volume_expansion():
    stock_id, bars = make_bars(
        start_price="100",
        returns=["0.01"] * 20 + ["-0.10"],
        volumes=[100_000] * 20 + [600_000],
    )

    signal = CrashRadarAnalyzer.analyze(stock_id, bars, lookback=20)

    assert signal.return_percent < 0
    assert signal.volume_ratio > Decimal("4")
    assert signal.score >= 50
    assert signal.level in (StressLevel.HIGH, StressLevel.EXTREME)


def test_crash_radar_does_not_flag_normal_day_as_crash():
    stock_id, bars = make_bars(
        start_price="100",
        returns=["0.002"] * 21,
        volumes=[100_000] * 22,
    )

    signal = CrashRadarAnalyzer.analyze(stock_id, bars, lookback=20)

    assert signal.score < 25
    assert signal.level is StressLevel.NORMAL


def signal(stock_id, return_percent, volatility, score, level):
    return CrashRadarSignal(
        stock_id=stock_id,
        return_percent=Decimal(return_percent),
        volatility_percent=Decimal(volatility),
        volume_ratio=Decimal("2"),
        score=score,
        level=level,
    )


def test_market_stress_requires_broad_cross_sectional_stress():
    isolated = MarketStressAnalyzer.analyze([
        signal(uuid4(), "-10", "6", 80, StressLevel.EXTREME),
        *[
            signal(uuid4(), "1", "1", 5, StressLevel.NORMAL)
            for _ in range(9)
        ],
    ])
    broad = MarketStressAnalyzer.analyze([
        signal(uuid4(), "-5", "5", 70, StressLevel.HIGH)
        for _ in range(8)
    ] + [
        signal(uuid4(), "0", "1", 5, StressLevel.NORMAL)
        for _ in range(2)
    ])

    assert isolated.score < broad.score
    assert isolated.crash_ratio < broad.crash_ratio
    assert broad.level in (StressLevel.HIGH, StressLevel.EXTREME)


def test_market_stress_is_deterministic_and_empty_is_normal():
    empty = MarketStressAnalyzer.analyze([])
    assert empty.score == 0
    assert empty.level is StressLevel.NORMAL

    signals = [
        signal(uuid4(), "-2", "4", 55, StressLevel.HIGH),
        signal(uuid4(), "-1", "3.5", 50, StressLevel.HIGH),
    ]
    assert MarketStressAnalyzer.analyze(signals) == MarketStressAnalyzer.analyze(signals)
