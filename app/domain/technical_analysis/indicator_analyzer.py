from decimal import Decimal

from app.domain.market_data.price_bar import PriceBar
from app.domain.technical_analysis.indicator_evidence import (
    TechnicalIndicatorEvidence,
    TechnicalIndicatorPoint,
)
from app.domain.technical_analysis.indicators import (
    average_directional_index,
    average_true_range,
    bollinger_bands,
    commodity_channel_index,
    exponential_moving_average,
    ichimoku_cloud,
    macd,
    money_flow_index,
    on_balance_volume,
    relative_strength_index,
    simple_moving_average,
    stochastic_oscillator,
)
from app.domain.technical_analysis.candlestick_patterns import detect_candlestick_patterns
from app.domain.technical_analysis.price_action import fibonacci_retracements
from app.domain.technical_analysis.price_action_extensions import (
    fibonacci_extensions as project_fibonacci_extensions,
)
from app.domain.technical_analysis.price_structure import detect_swing_points
from app.domain.technical_analysis.elliott import enumerate_impulse_counts


class TechnicalIndicatorAnalyzer:
    @staticmethod
    def analyze(price_bars: list[PriceBar]) -> TechnicalIndicatorEvidence:
        if not price_bars:
            return TechnicalIndicatorEvidence(())

        for previous, current in zip(price_bars, price_bars[1:]):
            if current.timestamp <= previous.timestamp:
                raise ValueError("price bars must be strictly ordered by timestamp")
            if current.stock_id != previous.stock_id or current.timeframe != previous.timeframe:
                raise ValueError("price bars must share stock identity and timeframe")

        closes = tuple(bar.close.value for bar in price_bars)
        highs = tuple(bar.high.value for bar in price_bars)
        lows = tuple(bar.low.value for bar in price_bars)
        volumes = tuple(bar.volume.value for bar in price_bars)

        sma20 = simple_moving_average(closes, 20)
        sma50 = simple_moving_average(closes, 50)
        sma200 = simple_moving_average(closes, 200)
        ema9 = exponential_moving_average(closes, 9)
        ema20 = exponential_moving_average(closes, 20)
        ema50 = exponential_moving_average(closes, 50)
        ema200 = exponential_moving_average(closes, 200)
        rsi14 = relative_strength_index(closes, 14)
        macd_result = macd(closes)
        bands = bollinger_bands(closes, 20)
        atr14 = average_true_range(highs, lows, closes, 14)
        stochastic = stochastic_oscillator(highs, lows, closes, 14, 3)
        cci20 = commodity_channel_index(highs, lows, closes, 20)
        obv = on_balance_volume(closes, volumes)
        mfi14 = money_flow_index(highs, lows, closes, volumes, 14)
        directional = average_directional_index(highs, lows, closes, 14)
        ichimoku = ichimoku_cloud(highs, lows)
        candle_evidence = detect_candlestick_patterns(
            tuple(bar.open.value for bar in price_bars),
            highs,
            lows,
            closes,
        )
        # A pivot becomes observable only after its right-side confirmation bars close.
        swings = detect_swing_points(highs, lows, left_bars=2, right_bars=2)
        confirmed_swings_by_index: list[list[tuple[str, Decimal]]] = [
            [] for _ in price_bars
        ]
        for swing in swings:
            confirmation_index = swing.index + 2
            if confirmation_index < len(price_bars):
                confirmed_swings_by_index[confirmation_index].append(
                    (swing.kind.value, swing.price)
                )

        fib_by_index: list[tuple[str | None, tuple[int, int] | None, tuple[tuple[Decimal, Decimal], ...]]] = []
        elliott_by_index = []
        fib_extensions_by_index: list[tuple[str | None, tuple[int, int, int] | None, tuple[tuple[Decimal, Decimal], ...]]] = []
        visible_swings = []
        for index in range(len(price_bars)):
            visible_swings = [
                swing for swing in swings
                if swing.index + 2 <= index
            ]
            # Elliott candidates use only pivots confirmed by this bar; no future bars leak into history.
            elliott_by_index.append(enumerate_impulse_counts(visible_swings))
            latest_pair = next(
                (
                    (visible_swings[position - 1], visible_swings[position])
                    for position in range(len(visible_swings) - 1, 0, -1)
                    if visible_swings[position - 1].index < visible_swings[position].index
                    and visible_swings[position - 1].kind is not visible_swings[position].kind
                ),
                None,
            )
            if latest_pair is None:
                fib_by_index.append((None, None, ()))
                fib_extensions_by_index.append((None, None, ()))
                continue
            first_swing, second_swing = latest_pair
            if first_swing.kind.value == "low":
                low_swing, high_swing, direction = first_swing, second_swing, "up"
            else:
                high_swing, low_swing, direction = first_swing, second_swing, "down"
            fib = fibonacci_retracements(
                low_swing.price,
                high_swing.price,
                direction=direction,
            )
            fib_by_index.append((
                direction,
                (low_swing.index, high_swing.index),
                fib.retracements,
            ))

            index_counts = {
                pivot.index: sum(1 for item in visible_swings if item.index == pivot.index)
                for pivot in visible_swings
            }
            unambiguous_swings = [
                pivot for pivot in visible_swings
                if index_counts[pivot.index] == 1
            ]
            extension_result = None
            extension_anchors = None
            extension_direction = None
            for start_position in range(len(unambiguous_swings) - 3, -1, -1):
                triple = unambiguous_swings[start_position:start_position + 3]
                kinds = tuple(item.kind.value for item in triple)
                if kinds == ("low", "high", "low"):
                    extension_direction = "up"
                elif kinds == ("high", "low", "high"):
                    extension_direction = "down"
                else:
                    continue
                # Invalid retracement geometry is not a valid extension anchor; keep scanning earlier swings.
                if not (
                    min(triple[0].price, triple[1].price)
                    <= triple[2].price
                    <= max(triple[0].price, triple[1].price)
                ):
                    continue
                extension_result = project_fibonacci_extensions(
                    triple[0].price,
                    triple[1].price,
                    triple[2].price,
                    direction=extension_direction,
                )
                extension_anchors = tuple(item.index for item in triple)
                break
            fib_extensions_by_index.append((
                extension_direction,
                extension_anchors,  # type: ignore[arg-type]
                extension_result.levels if extension_result is not None else (),
            ))

        candle_patterns_by_index: list[list[str]] = [
            [] for _ in price_bars
        ]
        for item in candle_evidence:
            candle_patterns_by_index[item.index].append(item.pattern.value)

        points = tuple(
            TechnicalIndicatorPoint(
                timestamp=bar.timestamp,
                close=bar.close.value,
                sma_20=sma20[index],
                sma_50=sma50[index],
                sma_200=sma200[index],
                ema_9=ema9[index],
                ema_20=ema20[index],
                ema_50=ema50[index],
                ema_200=ema200[index],
                rsi_14=rsi14[index],
                macd_line=macd_result.line[index],
                macd_signal=macd_result.signal[index],
                macd_histogram=macd_result.histogram[index],
                bollinger_upper=bands.upper[index],
                bollinger_middle=bands.middle[index],
                bollinger_lower=bands.lower[index],
                atr_14=atr14[index],
                stochastic_k_14=stochastic.percent_k[index],
                stochastic_d_3=stochastic.percent_d[index],
                cci_20=cci20[index],
                obv=obv[index],
                mfi_14=mfi14[index],
                plus_di_14=directional.plus_di[index],
                minus_di_14=directional.minus_di[index],
                adx_14=directional.adx[index],
                ichimoku_conversion_9=ichimoku.conversion_line[index],
                ichimoku_base_26=ichimoku.base_line[index],
                ichimoku_span_a_unshifted=ichimoku.leading_span_a_unshifted[index],
                ichimoku_span_b_unshifted=ichimoku.leading_span_b_unshifted[index],
                candlestick_patterns=tuple(candle_patterns_by_index[index]),
                confirmed_swings=tuple(confirmed_swings_by_index[index]),
                fibonacci_direction=fib_by_index[index][0],
                fibonacci_anchor_indices=fib_by_index[index][1],
                fibonacci_retracements=fib_by_index[index][2],
                fibonacci_extension_direction=fib_extensions_by_index[index][0],
                fibonacci_extension_anchor_indices=fib_extensions_by_index[index][1],
                fibonacci_extensions=fib_extensions_by_index[index][2],
                elliott_candidates=elliott_by_index[index],
            )
            for index, bar in enumerate(price_bars)
        )
        return TechnicalIndicatorEvidence(points)
