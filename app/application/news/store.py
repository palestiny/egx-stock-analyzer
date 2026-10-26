from datetime import datetime
from decimal import Decimal
from typing import Protocol
from uuid import UUID

from app.domain.news.event import NewsEvent


class NewsEventStore(Protocol):
    def upsert(self, event: NewsEvent) -> bool: ...
    def get(self, event_id: UUID) -> NewsEvent | None: ...
    def query_as_of(
        self,
        as_of: datetime,
        *,
        symbol: str | None = None,
        minimum_entity_confidence: Decimal = Decimal("0.8"),
        limit: int = 100,
    ) -> tuple[NewsEvent, ...]: ...
