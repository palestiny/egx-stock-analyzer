from datetime import datetime, timedelta, timezone
from decimal import Decimal
from uuid import uuid4

from app.domain.market_data.price import Price
from app.domain.market_data.price_bar import PriceBar
from app.domain.market_data.timeframe import Timeframe
from app.domain.market_data.volume import Volume
from app.domain.opportunity.classification import OpportunityClassification
from app.domain.backtesting.evaluator import BacktestEvaluator


STOCK_ID = uuid4()
START = datetime(2026, 1, 1, tzinfo=timezone.utc)


def price_bar(day: int, close: str) -> PriceBar:
    value = Price(Decimal(close))

    return PriceBar.create(
        stock_id=STOCK_ID,
        timeframe=Timeframe.DAILY,
        timestamp=START + timedelta(days=day),
        open=value,
        high=value,
        low=value,
        close=value,
        volume=Volume(1000),
    )


def test_signal_generation_receives_only_data_available_at_signal_timestamp():
    price_bars = [
        price_bar(0, "100"),
        price_bar(1, "110"),
        price_bar(2, "120"),
        price_bar(3, "130"),
    ]
    observed_history_lengths: list[int] = []

    def strategy(history: list[PriceBar]) -> OpportunityClassification:
        observed_history_lengths.append(len(history))
        assert history
        assert history[-1].timestamp <= START + timedelta(days=len(history) - 1)
        return OpportunityClassification.BUY

    BacktestEvaluator.evaluate(
        price_bars=price_bars,
        strategy=strategy,
        forward_window=2,
    )

    assert observed_history_lengths == [1, 2, 3, 4]


def test_buy_signal_uses_next_available_bar_not_signal_close():
    price_bars = [
        price_bar(0, "100"),
        price_bar(1, "110"),
        price_bar(2, "120"),
    ]

    def strategy(history: list[PriceBar]) -> OpportunityClassification:
        return (
            OpportunityClassification.BUY
            if history[-1].timestamp == START
            else OpportunityClassification.HOLD
        )

    result = BacktestEvaluator.evaluate(
        price_bars=price_bars,
        strategy=strategy,
        forward_window=1,
    )

    outcome = result.outcomes[0]

    assert outcome.signal_timestamp == price_bars[0].timestamp
    assert outcome.execution_timestamp == price_bars[1].timestamp
    assert outcome.entry_price == price_bars[1].close


def test_configured_forward_window_is_respected():
    price_bars = [
        price_bar(0, "100"),
        price_bar(1, "110"),
        price_bar(2, "120"),
        price_bar(3, "130"),
        price_bar(4, "140"),
    ]

    def strategy(history: list[PriceBar]) -> OpportunityClassification:
        return (
            OpportunityClassification.BUY
            if history[-1].timestamp == START
            else OpportunityClassification.HOLD
        )

    result = BacktestEvaluator.evaluate(
        price_bars=price_bars,
        strategy=strategy,
        forward_window=3,
    )

    outcome = result.outcomes[0]

    assert outcome.execution_timestamp == price_bars[1].timestamp
    assert outcome.outcome_timestamp == price_bars[3].timestamp
    assert outcome.outcome_price == price_bars[3].close


def test_future_prices_affect_only_outcome_after_signal_is_fixed():
    price_bars = [
        price_bar(0, "100"),
        price_bar(1, "110"),
        price_bar(2, "150"),
    ]
    seen_history: list[tuple[datetime, ...]] = []

    def strategy(history: list[PriceBar]) -> OpportunityClassification:
        seen_history.append(tuple(bar.timestamp for bar in history))
        return (
            OpportunityClassification.BUY
            if history[-1].timestamp == START
            else OpportunityClassification.HOLD
        )

    result = BacktestEvaluator.evaluate(
        price_bars=price_bars,
        strategy=strategy,
        forward_window=2,
    )

    assert seen_history[0] == (price_bars[0].timestamp,)
    assert result.outcomes[0].outcome_price == price_bars[2].close


def test_buy_signal_produces_measurable_forward_return():
    price_bars = [
        price_bar(0, "100"),
        price_bar(1, "110"),
        price_bar(2, "121"),
    ]

    def strategy(history: list[PriceBar]) -> OpportunityClassification:
        return (
            OpportunityClassification.BUY
            if history[-1].timestamp == START
            else OpportunityClassification.HOLD
        )

    result = BacktestEvaluator.evaluate(
        price_bars=price_bars,
        strategy=strategy,
        forward_window=2,
    )

    assert result.outcomes[0].forward_return == Decimal("0.1")


def test_no_buy_signals_produces_empty_valid_result():
    price_bars = [
        price_bar(0, "100"),
        price_bar(1, "110"),
        price_bar(2, "120"),
    ]

    def strategy(history: list[PriceBar]) -> OpportunityClassification:
        return OpportunityClassification.HOLD

    result = BacktestEvaluator.evaluate(
        price_bars=price_bars,
        strategy=strategy,
        forward_window=2,
    )

    assert result.outcomes == ()
    assert result.buy_signal_count == 0


def test_results_are_deterministic_for_same_input_and_configuration():
    price_bars = [
        price_bar(0, "100"),
        price_bar(1, "110"),
        price_bar(2, "120"),
        price_bar(3, "130"),
    ]

    def strategy(history: list[PriceBar]) -> OpportunityClassification:
        return (
            OpportunityClassification.BUY
            if history[-1].timestamp == START
            else OpportunityClassification.HOLD
        )

    first = BacktestEvaluator.evaluate(
        price_bars=price_bars,
        strategy=strategy,
        forward_window=2,
    )
    second = BacktestEvaluator.evaluate(
        price_bars=price_bars,
        strategy=strategy,
        forward_window=2,
    )

    assert first == second


def test_evaluator_does_not_create_hidden_stop_loss_or_target():
    price_bars = [
        price_bar(0, "100"),
        price_bar(1, "90"),
        price_bar(2, "80"),
        price_bar(3, "120"),
    ]

    def strategy(history: list[PriceBar]) -> OpportunityClassification:
        return (
            OpportunityClassification.BUY
            if history[-1].timestamp == START
            else OpportunityClassification.HOLD
        )

    result = BacktestEvaluator.evaluate(
        price_bars=price_bars,
        strategy=strategy,
        forward_window=3,
    )

    outcome = result.outcomes[0]

    assert outcome.outcome_timestamp == price_bars[3].timestamp
    assert outcome.outcome_price == price_bars[3].close


def test_repeated_evaluation_of_same_historical_input_produces_same_result():
    price_bars = [
        price_bar(0, "100"),
        price_bar(1, "110"),
        price_bar(2, "105"),
        price_bar(3, "115"),
    ]

    def strategy(history: list[PriceBar]) -> OpportunityClassification:
        return (
            OpportunityClassification.BUY
            if history[-1].timestamp == START
            else OpportunityClassification.HOLD
        )

    results = [
        BacktestEvaluator.evaluate(
            price_bars=price_bars,
            strategy=strategy,
            forward_window=2,
        )
        for _ in range(3)
    ]

    assert results[0] == results[1] == results[2]
