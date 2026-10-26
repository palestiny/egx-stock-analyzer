from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime, timezone
from typing import Any, Protocol


class OwnerDashboardReadStore(Protocol):
    def snapshot(self, *, as_of: datetime) -> dict[str, Any]: ...


@dataclass(frozen=True)
class GetOwnerDashboardOverview:
    store: OwnerDashboardReadStore
    telegram_configured: bool
    news_source_configured: bool = False

    def execute(self, *, as_of: datetime | None = None) -> dict[str, Any]:
        cutoff = as_of or datetime.now(timezone.utc)
        if cutoff.tzinfo is None or cutoff.utcoffset() is None:
            raise ValueError("as_of must be timezone-aware")
        result = self.store.snapshot(as_of=cutoff)
        return {
            **result,
            "integrations": {
                "telegram_transport_configured": self.telegram_configured,
                "news_source_configured": self.news_source_configured,
            },
        }
