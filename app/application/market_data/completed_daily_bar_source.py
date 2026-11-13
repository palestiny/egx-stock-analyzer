from __future__ import annotations

from dataclasses import dataclass
from datetime import date, datetime
from typing import Protocol, Sequence
from zoneinfo import ZoneInfo

from app.domain.signals.lifecycle import CompletedDailyBarObservation


EGX_TIMEZONE = ZoneInfo("Africa/Cairo")


@dataclass(frozen=True)
class ProviderDailyBarEvidence:
    """Provider-neutral envelope around one lifecycle-eligible daily bar.

    This envelope makes provider contract version, EGX session identity, source
    timestamp, and local retrieval time explicit. It is not itself proof that
    the provider's finality claim is true; a separately approved verifier must
    validate the claim against documented provider guarantees.
    """

    provider_id: str
    provider_contract_version: str
    instrument_symbol: str
    session_date: date
    source_timestamp: datetime
    retrieved_at: datetime
    bar: CompletedDailyBarObservation

    def __post_init__(self) -> None:
        for name in (
            "provider_id",
            "provider_contract_version",
            "instrument_symbol",
        ):
            value = getattr(self, name)
            if not isinstance(value, str) or not value.strip():
                raise ValueError(f"{name} is required")

        if not isinstance(self.session_date, date) or isinstance(
            self.session_date, datetime
        ):
            raise ValueError("session_date must be a calendar date")

        for name, value in (
            ("source_timestamp", self.source_timestamp),
            ("retrieved_at", self.retrieved_at),
        ):
            if value.tzinfo is None or value.utcoffset() is None:
                raise ValueError(f"{name} must be timezone-aware")

        if self.source_timestamp > self.retrieved_at:
            raise ValueError("source_timestamp cannot be later than retrieved_at")
        if self.bar.observed_at > self.retrieved_at:
            raise ValueError("bar observed_at cannot be later than retrieved_at")
        if self.provider_id.strip().casefold() != self.bar.provider.strip().casefold():
            raise ValueError("provider_id does not match the bar provider")
        if (
            self.instrument_symbol.strip().upper()
            != self.bar.symbol.strip().upper()
        ):
            raise ValueError("instrument_symbol does not match the bar symbol")
        actual_session = self.bar.candle_at.astimezone(EGX_TIMEZONE).date()
        if actual_session != self.session_date:
            raise ValueError(
                "session_date does not match the bar candle date in Africa/Cairo"
            )


class CompletedDailyBarSource(Protocol):
    """Port for retrieving provider-described daily-bar evidence.

    Implementations must preserve the provider's original timestamps,
    revision/correction identity, and attestation text. They must not infer
    finality from elapsed time or manufacture a finality attestation.
    """

    def get_completed_daily_bars(
        self,
        instrument_symbol: str,
        from_session: date,
        through_session: date,
    ) -> Sequence[ProviderDailyBarEvidence]:
        ...
