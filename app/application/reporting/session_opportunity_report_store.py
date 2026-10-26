from __future__ import annotations

from datetime import date, datetime
from typing import Any, Protocol

from app.domain.reporting.session_opportunity_ledger import SessionOpportunityLedgerReport


class SessionOpportunityReportStore(Protocol):
    """Persistence contract for immutable session opportunity report snapshots."""

    def save(self, report: SessionOpportunityLedgerReport) -> bool: ...

    def get_latest(
        self,
        session_date: date,
        *,
        as_of: datetime | None = None,
    ) -> dict[str, Any] | None: ...
