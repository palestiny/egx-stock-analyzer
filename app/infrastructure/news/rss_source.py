from __future__ import annotations

import hashlib
import re
import urllib.request
import xml.etree.ElementTree as ET
from dataclasses import dataclass
from datetime import datetime, timezone
from email.utils import parsedate_to_datetime
from collections.abc import Callable, Mapping, Sequence
from decimal import Decimal
from typing import Protocol
from urllib.parse import urljoin
from uuid import NAMESPACE_URL, uuid5

from app.domain.news.event import NewsEvent, NewsEventCategory, NewsSourceType


MAX_FEED_BYTES = 2_000_000
MAX_ITEMS_PER_FEED = 500
USER_AGENT = "EGX-Stock-Analyzer/1.0 (+configured RSS ingestion)"


@dataclass(frozen=True)
class RSSFeedConfig:
    source_name: str
    url: str
    source_type: NewsSourceType
    timeout_seconds: float = 8.0

    def __post_init__(self) -> None:
        if not self.source_name.strip():
            raise ValueError("RSS source_name cannot be empty")
        if not self.url.startswith("https://"):
            raise ValueError("RSS feed URL must use HTTPS")
        if not 0.1 <= self.timeout_seconds <= 60:
            raise ValueError("RSS timeout_seconds must be between 0.1 and 60")


class NewsSourceAdapter(Protocol):
    @property
    def source_name(self) -> str: ...

    def fetch_recent(self, since: datetime | None = None) -> Sequence[NewsEvent]: ...


def _download_feed(url: str, timeout_seconds: float) -> bytes:
    request = urllib.request.Request(
        url,
        headers={"User-Agent": USER_AGENT, "Accept": "application/rss+xml, application/atom+xml, application/xml, text/xml"},
    )
    with urllib.request.urlopen(request, timeout=timeout_seconds) as response:
        payload = response.read(MAX_FEED_BYTES + 1)
    if len(payload) > MAX_FEED_BYTES:
        raise ValueError("RSS feed exceeds the configured 2 MB limit")
    return payload


def _local_name(tag: str) -> str:
    return tag.rsplit("}", 1)[-1].lower()


def _child_text(element: ET.Element, *names: str) -> str | None:
    accepted = {name.lower() for name in names}
    for child in element.iter():
        if child is element:
            continue
        if _local_name(child.tag) in accepted and child.text and child.text.strip():
            return child.text.strip()
    return None


def _item_link(item: ET.Element, feed_url: str) -> str | None:
    for child in item.iter():
        if _local_name(child.tag) != "link":
            continue
        href = child.attrib.get("href")
        value = href or (child.text.strip() if child.text else "")
        if value:
            resolved = urljoin(feed_url, value)
            if resolved.startswith(("https://", "http://")):
                return resolved
    return None


def _parse_timestamp(raw: str | None) -> datetime | None:
    if not raw:
        return None
    parsed: datetime | None = None
    try:
        parsed = datetime.fromisoformat(raw.replace("Z", "+00:00"))
    except ValueError:
        try:
            parsed = parsedate_to_datetime(raw)
        except (TypeError, ValueError, OverflowError):
            return None
    if parsed.tzinfo is None or parsed.utcoffset() is None:
        return None
    return parsed.astimezone(timezone.utc)


def _matches_title(title: str, aliases: Mapping[str, Sequence[str]]) -> tuple[tuple[str, ...], Decimal]:
    matches: list[str] = []
    best_confidence = Decimal("0")
    normalized_title = title.casefold()
    for raw_symbol, raw_aliases in aliases.items():
        symbol = raw_symbol.strip().upper()
        candidates = (symbol, *tuple(alias.strip() for alias in raw_aliases if alias.strip()))
        confidence = Decimal("0")
        for candidate in candidates:
            pattern = rf"(?<![\w]){re.escape(candidate.casefold())}(?![\w])"
            if re.search(pattern, normalized_title):
                confidence = max(confidence, Decimal("0.99") if candidate.upper() == symbol else Decimal("0.90"))
        if confidence:
            matches.append(symbol)
            best_confidence = max(best_confidence, confidence)
    return tuple(sorted(set(matches))), best_confidence


def _classify(title: str) -> NewsEventCategory:
    value = title.casefold()
    rules: tuple[tuple[NewsEventCategory, tuple[str, ...]], ...] = (
        (NewsEventCategory.TRADING_SUSPENSION, ("suspend trading", "trading suspension", "resume trading", "وقف التداول", "تعليق التداول", "استئناف التداول")),
        (NewsEventCategory.DIVIDEND, ("dividend", "cash distribution", "coupon", "توزيع الأرباح", "توزيع كوبون")),
        (NewsEventCategory.EARNINGS, ("financial results", "quarterly results", "annual results", "financial statements", "نتائج الأعمال", "القوائم المالية")),
        (NewsEventCategory.CAPITAL_CHANGE, ("capital increase", "capital reduction", "rights issue", "زيادة رأس المال", "تخفيض رأس المال")),
        (NewsEventCategory.CORPORATE_ACTION, ("treasury shares", "stock split", "merger", "acquisition", "أسهم خزينة", "تجزئة الأسهم", "استحواذ")),
        (NewsEventCategory.LITIGATION, ("lawsuit", "court ruling", "litigation", "دعوى قضائية", "حكم قضائي")),
        (NewsEventCategory.MANAGEMENT, ("board of directors", "general assembly", "agm", "egm", "مجلس الإدارة", "الجمعية العامة")),
        (NewsEventCategory.REGULATORY, ("fra approval", "regulatory approval", "listing committee", "الهيئة العامة للرقابة المالية", "لجنة القيد")),
        (NewsEventCategory.MACROECONOMIC, ("inflation", "interest rate", "central bank", "exchange rate", "التضخم", "سعر الفائدة", "البنك المركزي")),
        (NewsEventCategory.OPERATIONS, ("new contract", "production", "factory", "operations", "عقد جديد", "الإنتاج", "مصنع")),
    )
    for category, keywords in rules:
        if any(keyword in value for keyword in keywords):
            return category
    return NewsEventCategory.UNKNOWN


class RSSNewsSource:
    """Fetch metadata-only RSS/Atom items; article bodies are never persisted."""

    def __init__(
        self,
        config: RSSFeedConfig,
        *,
        symbol_aliases: Mapping[str, Sequence[str]] | None = None,
        fetch_bytes: Callable[[str, float], bytes] = _download_feed,
        clock: Callable[[], datetime] = lambda: datetime.now(timezone.utc),
    ) -> None:
        self._config = config
        self._aliases = symbol_aliases or {}
        self._fetch_bytes = fetch_bytes
        self._clock = clock

    @property
    def source_name(self) -> str:
        return self._config.source_name

    def fetch_recent(self, since: datetime | None = None) -> tuple[NewsEvent, ...]:
        if since is not None and (since.tzinfo is None or since.utcoffset() is None):
            raise ValueError("since must be timezone-aware")
        retrieved_at = self._clock()
        if retrieved_at.tzinfo is None or retrieved_at.utcoffset() is None:
            raise ValueError("clock must return a timezone-aware datetime")
        retrieved_at = retrieved_at.astimezone(timezone.utc)

        payload = self._fetch_bytes(self._config.url, self._config.timeout_seconds)
        if len(payload) > MAX_FEED_BYTES:
            raise ValueError("RSS feed exceeds the configured 2 MB limit")
        try:
            root = ET.fromstring(payload)
        except ET.ParseError as error:
            raise ValueError("RSS source returned invalid XML") from error

        items = [element for element in root.iter() if _local_name(element.tag) in {"item", "entry"}]
        events: list[NewsEvent] = []
        for item in items[:MAX_ITEMS_PER_FEED]:
            title = _child_text(item, "title")
            link = _item_link(item, self._config.url)
            if not title or not link:
                continue
            published = _parse_timestamp(_child_text(item, "pubdate", "published", "updated", "date"))
            if since is not None:
                if published is None or published < since.astimezone(timezone.utc):
                    continue
            guid = _child_text(item, "guid", "id") or link
            event_id = uuid5(NAMESPACE_URL, f"{self.source_name}|{guid}")
            symbols, confidence = _matches_title(title, self._aliases)
            fingerprint_text = f"{title.strip().casefold()}|{published.isoformat() if published else ''}"
            fingerprint = "sha256:" + hashlib.sha256(fingerprint_text.encode("utf-8")).hexdigest()
            events.append(
                NewsEvent(
                    event_id=event_id,
                    source_name=self.source_name,
                    source_type=self._config.source_type,
                    source_url=link,
                    title=title.strip(),
                    category=_classify(title),
                    published_at=published,
                    retrieved_at=retrieved_at,
                    first_seen_at=retrieved_at,
                    matched_symbols=symbols,
                    entity_match_confidence=confidence,
                    content_fingerprint=fingerprint,
                )
            )
        return tuple(events)
