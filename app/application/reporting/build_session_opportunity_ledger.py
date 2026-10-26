from datetime import date, datetime
from zoneinfo import ZoneInfo, ZoneInfoNotFoundError

from app.application.signals.store import SignalHistoryStore, SignalRecord
from app.application.signals.track_record import TrackRecordStore
from app.domain.reporting.session_opportunity_ledger import (
    SessionOpportunityEntry,
    SessionOpportunityLedgerReport,
)


class BuildSessionOpportunityLedger:
    def __init__(
        self,
        history: SignalHistoryStore,
        track_record: TrackRecordStore,
        *,
        exchange_timezone: str = "Africa/Cairo",
        methodology_version: str = "session-opportunity-ledger-v1",
    ) -> None:
        try:
            self._timezone = ZoneInfo(exchange_timezone)
        except ZoneInfoNotFoundError as error:
            raise ValueError(f"unknown exchange timezone: {exchange_timezone}") from error
        self._history = history
        self._track_record = track_record
        self._timezone_name = exchange_timezone
        self._methodology_version = methodology_version

    def execute(
        self,
        session_date: date,
        *,
        generated_at: datetime,
    ) -> SessionOpportunityLedgerReport:
        if generated_at.tzinfo is None or generated_at.utcoffset() is None:
            raise ValueError("generated_at must be timezone-aware")

        records_by_signal: dict[object, list[SignalRecord]] = {}
        for record in self._history.all_records():
            if record.recorded_at.tzinfo is None or record.recorded_at.utcoffset() is None:
                raise ValueError("signal history timestamps must be timezone-aware")
            if record.recorded_at <= generated_at:
                records_by_signal.setdefault(record.signal_id, []).append(record)

        outcomes = {
            outcome.signal_id: outcome
            for outcome in self._track_record.all()
            if outcome.observed_at <= generated_at
        }
        entries: list[SessionOpportunityEntry] = []
        for signal_id, history in records_by_signal.items():
            if not history:
                continue
            history.sort(key=lambda item: (item.recorded_at, item.event))
            original_record = history[0]
            current_record = history[-1]
            original = original_record.signal
            current = current_record.signal
            if original.generated_at.tzinfo is None or original.generated_at.utcoffset() is None:
                raise ValueError("signal generation timestamps must be timezone-aware")
            if original.generated_at.astimezone(self._timezone).date() != session_date:
                continue

            outcome = outcomes.get(signal_id)
            entries.append(SessionOpportunityEntry(
                signal_id=signal_id,
                symbol=original.symbol.strip().upper(),
                publication_time=original_record.recorded_at,
                original_entry_lower=original.entry_zone.lower,
                original_entry_upper=original.entry_zone.upper,
                original_invalidation=original.invalidation,
                original_targets=tuple((target.label, target.price) for target in original.targets),
                current_status=current.status,
                current_evidence=tuple(evidence.description for evidence in current.evidence),
                market_proxy_outcome=outcome.outcome if outcome is not None else None,
                market_proxy_return=outcome.realized_return if outcome is not None else None,
                market_proxy_r=outcome.realized_r if outcome is not None else None,
                outcome_observed_at=outcome.observed_at if outcome is not None else None,
            ))

        entries.sort(key=lambda item: (item.publication_time, item.symbol, str(item.signal_id)))
        resolved = sum(1 for item in entries if item.market_proxy_outcome is not None)
        return SessionOpportunityLedgerReport(
            session_date=session_date,
            generated_at=generated_at,
            exchange_timezone=self._timezone_name,
            methodology_version=self._methodology_version,
            opportunities=tuple(entries),
            unresolved_count=len(entries) - resolved,
            resolved_proxy_count=resolved,
        )
