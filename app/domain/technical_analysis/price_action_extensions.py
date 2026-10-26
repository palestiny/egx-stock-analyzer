from collections.abc import Sequence
from dataclasses import dataclass
from decimal import Decimal


@dataclass(frozen=True)
class FibonacciExtensions:
    direction: str
    levels: tuple[tuple[Decimal, Decimal], ...]


def fibonacci_extensions(
    impulse_start: Decimal,
    impulse_end: Decimal,
    pullback_end: Decimal,
    *,
    direction: str,
    ratios: tuple[Decimal, ...] = (
        Decimal("1.0"),
        Decimal("1.272"),
        Decimal("1.618"),
        Decimal("2.0"),
        Decimal("2.618"),
    ),
) -> FibonacciExtensions:
    """Project extensions from three explicit swing points; no pivots are inferred."""
    points = (impulse_start, impulse_end, pullback_end)
    if any(not point.is_finite() or point <= 0 for point in points):
        raise ValueError("swing prices must be finite positive Decimal values")
    if direction not in {"up", "down"}:
        raise ValueError("direction must be 'up' or 'down'")
    if direction == "up" and not impulse_start < impulse_end:
        raise ValueError("an upward impulse requires impulse_end above impulse_start")
    if direction == "down" and not impulse_start > impulse_end:
        raise ValueError("a downward impulse requires impulse_end below impulse_start")
    if not (min(impulse_start, impulse_end) <= pullback_end <= max(impulse_start, impulse_end)):
        raise ValueError("pullback_end must lie within the impulse range")
    if not ratios or any(
        not ratio.is_finite() or ratio <= 0
        for ratio in ratios
    ):
        raise ValueError("extension ratios must be finite and positive")

    impulse_range = abs(impulse_end - impulse_start)
    levels = tuple(
        (
            ratio,
            pullback_end + impulse_range * ratio
            if direction == "up"
            else pullback_end - impulse_range * ratio,
        )
        for ratio in ratios
    )
    return FibonacciExtensions(direction=direction, levels=levels)


def session_vwap(
    highs: Sequence[Decimal],
    lows: Sequence[Decimal],
    closes: Sequence[Decimal],
    volumes: Sequence[int],
    session_ids: Sequence[str],
) -> tuple[Decimal | None, ...]:
    """Calculate typical-price VWAP, resetting at each supplied trading-session boundary.

    Callers must supply intraday bars and a verified session identifier for each bar.
    The function deliberately does not infer exchange sessions or apply VWAP to daily bars.
    """
    high_values, low_values, close_values = tuple(highs), tuple(lows), tuple(closes)
    volume_values, sessions = tuple(volumes), tuple(session_ids)
    lengths = {len(high_values), len(low_values), len(close_values), len(volume_values), len(sessions)}
    if len(lengths) != 1:
        raise ValueError("OHLC, volume, and session inputs must have equal lengths")
    if any(
        not value.is_finite()
        for value in (*high_values, *low_values, *close_values)
    ):
        raise ValueError("indicator inputs must be finite Decimal values")
    if any(high < low for high, low in zip(high_values, low_values)):
        raise ValueError("each high must be greater than or equal to its low")
    if any(close < low or close > high for high, low, close in zip(high_values, low_values, close_values)):
        raise ValueError("each close must be within its high-low range")
    if any(isinstance(volume, bool) or not isinstance(volume, int) or volume < 0 for volume in volume_values):
        raise ValueError("volumes must be non-negative integers")
    if any(not isinstance(session, str) or not session.strip() for session in sessions):
        raise ValueError("session identifiers must be non-empty strings")
    seen_sessions: set[str] = set()
    previous_session: str | None = None
    for session in sessions:
        if session != previous_session:
            if session in seen_sessions:
                raise ValueError("session identifiers must be contiguous in chronological input")
            seen_sessions.add(session)
            previous_session = session

    result: list[Decimal | None] = []
    active_session: str | None = None
    cumulative_pv = Decimal("0")
    cumulative_volume = 0
    for high, low, close, volume, session in zip(
        high_values, low_values, close_values, volume_values, sessions
    ):
        if session != active_session:
            active_session = session
            cumulative_pv = Decimal("0")
            cumulative_volume = 0
        typical_price = (high + low + close) / Decimal("3")
        cumulative_pv += typical_price * Decimal(volume)
        cumulative_volume += volume
        result.append(
            cumulative_pv / Decimal(cumulative_volume)
            if cumulative_volume > 0
            else None
        )
    return tuple(result)
