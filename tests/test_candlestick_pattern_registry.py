from decimal import Decimal

import pytest

from app.domain.technical_analysis.candlestick_patterns import (
    CandlestickPattern,
    PatternDirection,
    detect_candlestick_patterns,
)


def d(*values: str) -> tuple[Decimal, ...]:
    return tuple(Decimal(value) for value in values)


def patterns(*ohlc: tuple[str, str, str, str]):
    opens, highs, lows, closes = zip(*ohlc)
    return detect_candlestick_patterns(
        d(*opens), d(*highs), d(*lows), d(*closes)
    )


def test_detects_doji_hammer_and_shooting_star() -> None:
    doji = patterns(("10", "11", "9", "10.1"))
    hammer = patterns(("10", "11.2", "7.8", "11"))
    star = patterns(("10", "12.5", "8.8", "9"))

    assert any(item.pattern is CandlestickPattern.DOJI for item in doji)
    assert any(item.pattern is CandlestickPattern.HAMMER for item in hammer)
    assert any(item.pattern is CandlestickPattern.SHOOTING_STAR for item in star)


def test_detects_bullish_and_bearish_engulfing() -> None:
    bullish = patterns(("10", "10.2", "7.8", "8"), ("7.5", "10.6", "7.3", "10.5"))
    bearish = patterns(("8", "10.2", "7.8", "10"), ("10.5", "10.7", "7.4", "7.5"))

    assert any(item.pattern is CandlestickPattern.BULLISH_ENGULFING for item in bullish)
    assert any(item.pattern is CandlestickPattern.BEARISH_ENGULFING for item in bearish)


def test_detects_harami_patterns() -> None:
    bullish = patterns(("10", "10.2", "7.8", "8"), ("8.2", "9.2", "8.1", "9"))
    bearish = patterns(("8", "10.2", "7.8", "10"), ("9.8", "9.9", "8.8", "9"))

    assert any(item.pattern is CandlestickPattern.BULLISH_HARAMI for item in bullish)
    assert any(item.pattern is CandlestickPattern.BEARISH_HARAMI for item in bearish)


def test_detects_piercing_line_and_dark_cloud_cover() -> None:
    bullish = patterns(("10", "10.2", "5.8", "6"), ("5.5", "8.5", "5.4", "8.2"))
    bearish = patterns(("6", "10.2", "5.8", "10"), ("10.5", "10.6", "7.5", "7.8"))

    assert any(item.pattern is CandlestickPattern.PIERCING_LINE for item in bullish)
    assert any(item.pattern is CandlestickPattern.DARK_CLOUD_COVER for item in bearish)


def test_detects_morning_and_evening_stars() -> None:
    morning = patterns(
        ("10", "10.2", "5.8", "6"),
        ("5.5", "6", "5.2", "5.7"),
        ("6", "9.2", "5.8", "9"),
    )
    evening = patterns(
        ("6", "10.2", "5.8", "10"),
        ("10.5", "10.8", "10.2", "10.3"),
        ("10", "10.2", "6.8", "7"),
    )

    assert any(item.pattern is CandlestickPattern.MORNING_STAR for item in morning)
    assert any(item.pattern is CandlestickPattern.EVENING_STAR for item in evening)


def test_detects_three_white_soldiers_and_three_black_crows() -> None:
    soldiers = patterns(
        ("1", "2.2", "0.8", "2"),
        ("1.8", "3.2", "1.7", "3"),
        ("2.8", "4.2", "2.7", "4"),
    )
    crows = patterns(
        ("4", "4.2", "2.8", "3"),
        ("3.2", "3.3", "1.8", "2"),
        ("2.2", "2.3", "0.8", "1"),
    )

    assert any(item.pattern is CandlestickPattern.THREE_WHITE_SOLDIERS for item in soldiers)
    assert any(item.pattern is CandlestickPattern.THREE_BLACK_CROWS for item in crows)


def test_pattern_evidence_is_timestamp_indexed_and_requires_context() -> None:
    matches = patterns(("10", "11.2", "7.8", "11"), ("10", "12.5", "8.8", "9"))
    assert all(item.index in (0, 1) for item in matches)
    assert all(item.requires_context_confirmation for item in matches)
    assert all(item.rule_version == "candles-v1" for item in matches)


def test_rejects_invalid_or_misaligned_ohlc() -> None:
    with pytest.raises(ValueError, match="equal lengths"):
        detect_candlestick_patterns(d("1"), d("2", "3"), d("0"), d("1"))

    with pytest.raises(ValueError, match="inconsistent"):
        detect_candlestick_patterns(d("5"), d("4"), d("3"), d("4"))

    with pytest.raises(ValueError, match="finite Decimal"):
        detect_candlestick_patterns(d("NaN"), d("2"), d("0"), d("1"))

    with pytest.raises(ValueError, match="between zero and one"):
        detect_candlestick_patterns(d("1"), d("2"), d("0"), d("1"), doji_body_fraction=Decimal("2"))
