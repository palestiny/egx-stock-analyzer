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
from app.domain.technical_analysis.price_action import detect_candlestick_patterns


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
        candle_evidence = detect_candlestick_patterns(price_bars)

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
                candlestick_patterns=tuple(
                    item.pattern.value for item in candle_evidence[index]
                ),
            )
            for index, bar in enumerate(price_bars)
        )
        return TechnicalIndicatorEvidence(points)
