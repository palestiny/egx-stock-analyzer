from __future__ import annotations

import sqlite3
from dataclasses import dataclass
from datetime import datetime
from pathlib import Path

from app.application.market_data.session_calendar_store import CalendarActivationEvent
from app.application.market_data.calendar_source_authenticity import CalendarSourceAuthenticityVerifier
from app.application.signals.validate_lifecycle_calendar_activation import (
    LifecycleCalendarActivationValidation,
    ValidateLifecycleCalendarActivation,
)
from app.infrastructure.persistence.sqlite_session_calendar_repository import (
    SQLiteSessionCalendarRepository,
)
from app.infrastructure.persistence.sqlite_signal_lifecycle_unit_of_work import (
    SQLiteSignalLifecycleUnitOfWork,
)


@dataclass(frozen=True)
class LifecycleCalendarActivationAttempt:
    validation: LifecycleCalendarActivationValidation
    event: CalendarActivationEvent | None


class _ActivationValidationRejected(Exception):
    def __init__(self, validation: LifecycleCalendarActivationValidation) -> None:
        super().__init__("lifecycle calendar activation validation was rejected")
        self.validation = validation


class SQLiteLifecycleCalendarActivationCoordinator:
    """Serialize lifecycle validation, calendar activation, and its audit event.

    The calendar repository owns the outer BEGIN IMMEDIATE transaction. The
    lifecycle unit of work joins that exact connection for bootstrap/cursor
    reads. Other repository reads are safe during this callback because the
    SQLite write reservation prevents any competing writer from changing the
    underlying database until the active pointer and audit event are committed.
    """

    def __init__(
        self,
        *,
        calendar_repository: SQLiteSessionCalendarRepository,
        lifecycle_unit_of_work: SQLiteSignalLifecycleUnitOfWork,
        validator: ValidateLifecycleCalendarActivation,
    ) -> None:
        calendar_path = Path(calendar_repository._database_path).resolve()
        lifecycle_path = Path(lifecycle_unit_of_work._database_path).resolve()
        if calendar_path != lifecycle_path:
            raise ValueError(
                "calendar repository and lifecycle unit of work must share one SQLite database"
            )
        if isinstance(validator, ValidateLifecycleCalendarActivation):
            if validator._unit_of_work is not lifecycle_unit_of_work:
                raise ValueError(
                    "activation validator must use the coordinator lifecycle unit of work"
                )
            dependent_stores = (
                validator._history,
                validator._calendar_store,
                validator._evidence_store,
                getattr(validator._schedule, "_calendar_store", None),
            )
            for store in dependent_stores:
                store_path = getattr(store, "_database_path", None)
                if store_path is None or Path(store_path).resolve() != calendar_path:
                    raise ValueError(
                        "all activation validation stores and the trusted schedule must share the coordinator SQLite database"
                    )
            if isinstance(validator._authenticity_verifier, CalendarSourceAuthenticityVerifier):
                authenticity_stores = (
                    validator._authenticity_verifier._origins,
                    validator._authenticity_verifier._records,
                )
                for store in authenticity_stores:
                    store_path = getattr(store, "_database_path", None)
                    if store_path is None or Path(store_path).resolve() != calendar_path:
                        raise ValueError(
                            "source-origin registry and verification audit must share the coordinator SQLite database"
                        )
        self._calendar_repository = calendar_repository
        self._lifecycle_unit_of_work = lifecycle_unit_of_work
        self._validator = validator

    def activate(
        self,
        calendar_version: str,
        *,
        performed_by: str,
        reason: str,
        as_of: datetime,
        occurred_at: datetime | None = None,
    ) -> LifecycleCalendarActivationAttempt:
        return self._execute(
            action="ACTIVATE",
            calendar_version=calendar_version,
            performed_by=performed_by,
            reason=reason,
            as_of=as_of,
            occurred_at=occurred_at,
            require_previously_active=False,
        )

    def rollback(
        self,
        calendar_version: str,
        *,
        performed_by: str,
        reason: str,
        as_of: datetime,
        occurred_at: datetime | None = None,
    ) -> LifecycleCalendarActivationAttempt:
        return self._execute(
            action="ROLLBACK",
            calendar_version=calendar_version,
            performed_by=performed_by,
            reason=reason,
            as_of=as_of,
            occurred_at=occurred_at,
            require_previously_active=True,
        )

    def _execute(
        self,
        *,
        action: str,
        calendar_version: str,
        performed_by: str,
        reason: str,
        as_of: datetime,
        occurred_at: datetime | None,
        require_previously_active: bool,
    ) -> LifecycleCalendarActivationAttempt:
        validation: LifecycleCalendarActivationValidation | None = None

        def validate(connection: sqlite3.Connection) -> None:
            nonlocal validation
            result = self._lifecycle_unit_of_work.execute_in_transaction(
                connection,
                lambda transaction: self._validator.execute(
                    calendar_version=calendar_version,
                    as_of=as_of,
                    transaction=transaction,
                ),
            )
            validation = result
            if not result.eligible:
                raise _ActivationValidationRejected(result)

        if isinstance(self._validator, ValidateLifecycleCalendarActivation):
            # External-only artifact re-fetch happens before BEGIN IMMEDIATE;
            # the transaction callback rechecks the persisted proof and trust version.
            self._validator.preflight_source_authenticity(
                calendar_version, at=as_of
            )

        try:
            event = self._calendar_repository.change_active_atomically(
                action=action,
                target_version=calendar_version,
                performed_by=performed_by,
                reason=reason,
                occurred_at=occurred_at,
                require_previously_active=require_previously_active,
                validate=validate,
            )
        except _ActivationValidationRejected as rejected:
            return LifecycleCalendarActivationAttempt(
                validation=rejected.validation,
                event=None,
            )

        if validation is None:
            raise RuntimeError("calendar activation completed without lifecycle validation")
        return LifecycleCalendarActivationAttempt(validation=validation, event=event)
