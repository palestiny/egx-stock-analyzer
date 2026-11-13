from datetime import date, datetime, timezone
from decimal import Decimal

import pytest

from app.application.market_data.completed_daily_bar_source import (
    ProviderDailyBarEvidence,
)
from app.domain.signals.lifecycle import CompletedDailyBarObservation


def _bar(
    *,
    provider: str = "fixture-provider",
    symbol: str = "COMI",
    candle_at: datetime | None = None,
    observed_at: datetime | None = None,
) -> CompletedDailyBarObservation:
    return CompletedDailyBarObservation(
        symbol=symbol,
        provider=provider,
        timeframe="DAILY",
        candle_at=candle_at or datetime(2026, 11, 12, 14, 30, tzinfo=timezone.utc),
        observed_at=observed_at or datetime(2026, 11, 12, 17, 0, tzinfo=timezone.utc),
        revision="revision-1",
        source_reference="fixture://provider/COMI/2026-11-12",
        finality_attestation="fixture finality claim; verifier still required",
        is_final=True,
        open=Decimal("100"),
        high=Decimal("105"),
        low=Decimal("99"),
        close=Decimal("103"),
    )


def _evidence(**overrides: object) -> ProviderDailyBarEvidence:
    values: dict[str, object] = {
        "provider_id": "fixture-provider",
        "provider_contract_version": "fixture-v1",
        "instrument_symbol": "COMI",
        "session_date": date(2026, 11, 12),
        "source_timestamp": datetime(2026, 11, 12, 17, 5, tzinfo=timezone.utc),
        "retrieved_at": datetime(2026, 11, 12, 17, 15, tzinfo=timezone.utc),
        "bar": _bar(),
    }
    values.update(overrides)
    return ProviderDailyBarEvidence(**values)  # type: ignore[arg-type]


def test_provider_daily_bar_evidence_preserves_explicit_session_and_contract_identity() -> None:
    evidence = _evidence()

    assert evidence.provider_contract_version == "fixture-v1"
    assert evidence.session_date == date(2026, 11, 12)
    assert evidence.provider_id == evidence.bar.provider
    assert evidence.instrument_symbol == evidence.bar.symbol


@pytest.mark.parametrize(
    ("overrides", "message"),
    [
        ({"provider_id": "different-provider"}, "provider_id"),
        ({"instrument_symbol": "EGAL"}, "instrument_symbol"),
        ({"session_date": date(2026, 11, 11)}, "session_date"),
        (
            {"source_timestamp": datetime(2026, 11, 12, 17, 5)},
            "source_timestamp must be timezone-aware",
        ),
        (
            {"retrieved_at": datetime(2026, 11, 12, 17, 15)},
            "retrieved_at must be timezone-aware",
        ),
        (
            {
                "source_timestamp": datetime(2026, 11, 12, 17, 20, tzinfo=timezone.utc),
                "retrieved_at": datetime(2026, 11, 12, 17, 15, tzinfo=timezone.utc),
            },
            "source_timestamp cannot be later than retrieved_at",
        ),
        (
            {
                "bar": _bar(
                    observed_at=datetime(2026, 11, 12, 17, 20, tzinfo=timezone.utc)
                )
            },
            "bar observed_at cannot be later than retrieved_at",
        ),
        ({"provider_contract_version": " "}, "provider_contract_version"),
    ],
)
def test_provider_daily_bar_evidence_rejects_ambiguous_or_mismatched_metadata(
    overrides: dict[str, object],
    message: str,
) -> None:
    with pytest.raises(ValueError, match=message):
        _evidence(**overrides)


def test_provider_daily_bar_evidence_uses_cairo_session_date_not_utc_date() -> None:
    evidence = _evidence(
        bar=_bar(candle_at=datetime(2026, 11, 11, 22, 30, tzinfo=timezone.utc)),
        source_timestamp=datetime(2026, 11, 12, 0, 5, tzinfo=timezone.utc),
        retrieved_at=datetime(2026, 11, 12, 0, 15, tzinfo=timezone.utc),
    )

    assert evidence.session_date == date(2026, 11, 12)
