from dataclasses import dataclass
from datetime import datetime
from decimal import Decimal
from enum import StrEnum
from uuid import UUID


class NewsSourceType(StrEnum):
    EXCHANGE_DISCLOSURE = "exchange_disclosure"
    REGULATOR = "regulator"
    CENTRAL_BANK = "central_bank"
    COMPANY_ANNOUNCEMENT = "company_announcement"
    MACROECONOMIC = "macroeconomic"
    FINANCIAL_MEDIA = "financial_media"
    OTHER = "other"


class NewsEventCategory(StrEnum):
    EARNINGS = "earnings"
    DIVIDEND = "dividend"
    CORPORATE_ACTION = "corporate_action"
    CAPITAL_CHANGE = "capital_change"
    REGULATORY = "regulatory"
    MACROECONOMIC = "macroeconomic"
    OPERATIONS = "operations"
    MANAGEMENT = "management"
    LITIGATION = "litigation"
    TRADING_SUSPENSION = "trading_suspension"
    MARKET_WIDE = "market_wide"
    UNKNOWN = "unknown"


@dataclass(frozen=True)
class NewsEvent:
    """Normalized news metadata; full article text is intentionally not stored here."""

    event_id: UUID
    source_name: str
    source_type: NewsSourceType
    source_url: str
    title: str
    category: NewsEventCategory
    published_at: datetime | None
    retrieved_at: datetime
    first_seen_at: datetime
    matched_symbols: tuple[str, ...]
    entity_match_confidence: Decimal
    content_fingerprint: str | None = None

    def __post_init__(self) -> None:
        for field_name, value in (
            ("published_at", self.published_at),
            ("retrieved_at", self.retrieved_at),
            ("first_seen_at", self.first_seen_at),
        ):
            if value is not None and (value.tzinfo is None or value.utcoffset() is None):
                raise ValueError(f"{field_name} must be timezone-aware")
        if not self.source_name.strip():
            raise ValueError("source_name cannot be empty")
        if not self.title.strip():
            raise ValueError("title cannot be empty")
        if not self.source_url.startswith(("https://", "http://")):
            raise ValueError("source_url must be an HTTP(S) URL")
        if not self.entity_match_confidence.is_finite() or not (
            Decimal("0") <= self.entity_match_confidence <= Decimal("1")
        ):
            raise ValueError("entity_match_confidence must be between zero and one")
        normalized_symbols = tuple(symbol.strip().upper() for symbol in self.matched_symbols)
        if any(not symbol for symbol in normalized_symbols):
            raise ValueError("matched symbols cannot be empty")
        if len(set(normalized_symbols)) != len(normalized_symbols):
            raise ValueError("matched symbols must be unique after normalization")
        object.__setattr__(self, "matched_symbols", normalized_symbols)

    def eligible_as_of(self, as_of: datetime) -> bool:
        """Conservative backtest eligibility: both publication and first-seen time must be known."""
        if as_of.tzinfo is None or as_of.utcoffset() is None:
            raise ValueError("as_of must be timezone-aware")
        if self.published_at is None:
            return False
        return self.published_at <= as_of and self.first_seen_at <= as_of
