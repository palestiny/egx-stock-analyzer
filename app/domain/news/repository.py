from datetime import datetime
from typing import Protocol
from uuid import UUID

from app.domain.news.event import NewsEvent


class NewsEventStore(Protocol):
    def save(self, event: NewsEvent) -> bool:
        raise NotImplementedError

    def get(self, event_id: UUID) -> NewsEvent | None:
        raise NotImplementedError

    def list_for_symbol_as_of(self, symbol: str, as_of: datetime, limit: int = 100) -> tuple[NewsEvent, ...]:
        raise NotImplementedError
