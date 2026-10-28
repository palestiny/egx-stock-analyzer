from __future__ import annotations

import hashlib
import re
import urllib.request
import xml.etree.ElementTree as ET
from collections.abc import Callable, Mapping
from datetime import datetime, timezone
from decimal import Decimal
from email.utils import parsedate_to_datetime
from urllib.parse import urljoin, urlparse
from uuid import NAMESPACE_URL, uuid5

from app.domain.news.event import NewsEvent, NewsEventCategory, NewsSourceType


_MAX_FEED_BYTES = 2 * 1024 * 1024
_MAX_FEED_ENTRIES = 500
_DEFAULT_TIMEOUT_SECONDS = 10.0
_ATOM_NAMESPACE = "{http://www.w3.org/2005/Atom}"


class RssNewsSourceAdapter:
    """Read-only RSS/Atom adapter with bounded HTTPS retrieval and point-in-time metadata.

    Feed URLs are explicit operator configuration; this adapter does not guess or scrape
    a provider's website. Article bodies are only inspected transiently for symbol matching
    and are never persisted in NewsEvent.
    """

    def __init__(
        self,
        *,
        source_name: str,
        source_type: NewsSourceType,
        feed_url: str,
        symbol_names: Mapping[str, str],
        timeout_seconds: float = _DEFAULT_TIMEOUT_SECONDS,
        fetch_bytes: Callable[[str, float, int], bytes] | None = None,
        clock: Callable[[], datetime] | None = None,
    ) -> None:
        normalized_url = feed_url.strip()
        parsed = urlparse(normalized_url)
        if parsed.scheme.lower() != "https" or not parsed.netloc:
            raise ValueError("news feed URL must be an absolute HTTPS URL")
        if not source_name.strip():
            raise ValueError("source_name cannot be empty")
        if not 0.1 <= timeout_seconds <= 60:
            raise ValueError("timeout_seconds must be between 0.1 and 60 seconds")

        self._source_name = source_name.strip()
        self._source_type = source_type
        self._feed_url = normalized_url
        self._timeout = timeout_seconds
        self._fetch_bytes = fetch_bytes or self._download
        self._clock = clock or (lambda: datetime.now(timezone.utc))
        self._symbol_patterns: tuple[tuple[str, re.Pattern[str], bool], ...] = tuple(
            (
                symbol.strip().upper(),
                re.compile(r"(?<![A-Z0-9])" + re.escape(alias.strip()) + r"(?![A-Z0-9])", re.IGNORECASE),
                alias.strip().upper() == symbol.strip().upper(),
            )
            for symbol, name in symbol_names.items()
            for alias in (symbol, name)
            if symbol.strip() and alias.strip()
        )

    @property
    def source_name(self) -> str:
        return self._source_name

    def fetch_recent(self, since: datetime | None = None) -> tuple[NewsEvent, ...]:
        if since is not None and (since.tzinfo is None or since.utcoffset() is None):
            raise ValueError("since must be timezone-aware")
        retrieved_at = self._clock()
        if retrieved_at.tzinfo is None or retrieved_at.utcoffset() is None:
            raise ValueError("clock must return a timezone-aware datetime")

        raw = self._fetch_bytes(self._feed_url, self._timeout, _MAX_FEED_BYTES)
        if len(raw) > _MAX_FEED_BYTES:
            raise ValueError("news feed exceeds the configured size limit")
        upper = raw.upper()
        if b"<!DOCTYPE" in upper or b"<!ENTITY" in upper:
            raise ValueError("DTD and entity declarations are not accepted")
        try:
            root = ET.fromstring(raw)
        except ET.ParseError as error:
            raise ValueError("news feed is not valid RSS/Atom XML") from error

        events: list[NewsEvent] = []
        for entry in self._entries(root)[:_MAX_FEED_ENTRIES]:
            title = self._child_text(entry, "title")
            if not title:
                continue
            link = self._entry_link(entry)
            source_url = urljoin(self._feed_url, link) if link else self._feed_url
            if urlparse(source_url).scheme.lower() not in {"http", "https"}:
                source_url = self._feed_url
            identity = self._child_text(entry, "guid") or self._child_text(entry, "id") or link or title
            published = self._parse_timestamp(
                self._child_text(entry, "pubDate")
                or self._child_text(entry, "published")
                or self._child_text(entry, "updated")
                or self._child_text(entry, "date")
            )
            if since is not None and (published is None or published < since):
                continue

            summary = self._child_text(entry, "description") or self._child_text(entry, "summary")
            matched_symbols, confidence = self._match_symbols(f"{title} {summary}")
            category = self._classify(f"{title} {summary}")
            stable_identity = f"{self._source_name}|{identity}|{published.isoformat() if published else ''}"
            event_id = uuid5(NAMESPACE_URL, stable_identity)
            fingerprint_source = f"{title.casefold().strip()}|{published.isoformat() if published else ''}"
            fingerprint = hashlib.sha256(fingerprint_source.encode("utf-8")).hexdigest()
            events.append(
                NewsEvent(
                    event_id=event_id,
                    source_name=self._source_name,
                    source_type=self._source_type,
                    source_url=source_url,
                    title=title.strip(),
                    category=category,
                    published_at=published,
                    retrieved_at=retrieved_at,
                    first_seen_at=retrieved_at,
                    matched_symbols=matched_symbols,
                    entity_match_confidence=confidence,
                    content_fingerprint=fingerprint,
                )
            )
        return tuple(events)

    @staticmethod
    def _download(url: str, timeout: float, maximum_bytes: int) -> bytes:
        request = urllib.request.Request(
            url,
            headers={"User-Agent": "EGX-Stock-Analyzer/1.0 (+configured RSS reader)", "Accept": "application/rss+xml, application/atom+xml, application/xml, text/xml"},
        )
        with urllib.request.urlopen(request, timeout=timeout) as response:
            final_url = response.geturl()
            if urlparse(final_url).scheme.lower() != "https":
                raise ValueError("news feed redirects must remain on HTTPS")
            raw = response.read(maximum_bytes + 1)
        if len(raw) > maximum_bytes:
            raise ValueError("news feed exceeds the configured size limit")
        return raw

    @staticmethod
    def _entries(root: ET.Element) -> tuple[ET.Element, ...]:
        local_name = root.tag.rsplit("}", 1)[-1].lower()
        if local_name == "feed":
            return tuple(root.findall(f"{_ATOM_NAMESPACE}entry"))
        if local_name == "rss":
            channel = root.find("channel")
            return tuple(channel.findall("item")) if channel is not None else ()
        if local_name == "rdf":
            return tuple(child for child in root if child.tag.rsplit("}", 1)[-1].lower() == "item")
        return tuple(child for child in root if child.tag.rsplit("}", 1)[-1].lower() == "item")

    @staticmethod
    def _child_by_local_name(entry: ET.Element, name: str) -> ET.Element | None:
        expected = name.casefold()
        return next(
            (
                child
                for child in entry
                if child.tag.rsplit("}", 1)[-1].casefold() == expected
            ),
            None,
        )

    @classmethod
    def _child_text(cls, entry: ET.Element, name: str) -> str:
        child = cls._child_by_local_name(entry, name)
        if child is None:
            return ""
        return "".join(child.itertext()).strip()

    @classmethod
    def _entry_link(cls, entry: ET.Element) -> str:
        link = cls._child_by_local_name(entry, "link")
        if link is None:
            return ""
        href = link.attrib.get("href")
        return href.strip() if href else (link.text or "").strip()

    @staticmethod
    def _parse_timestamp(raw: str) -> datetime | None:
        if not raw:
            return None
        try:
            value = datetime.fromisoformat(raw.replace("Z", "+00:00"))
        except ValueError:
            try:
                value = parsedate_to_datetime(raw)
            except (TypeError, ValueError, OverflowError):
                return None
        if value.tzinfo is None or value.utcoffset() is None:
            return None
        return value.astimezone(timezone.utc)

    def _match_symbols(self, text: str) -> tuple[tuple[str, ...], Decimal]:
        matches: dict[str, bool] = {}
        for symbol, pattern, is_ticker in self._symbol_patterns:
            if pattern.search(text):
                matches[symbol] = matches.get(symbol, False) or is_ticker
        if not matches:
            return (), Decimal("0")
        confidence = Decimal("0.99") if any(matches.values()) else Decimal("0.90")
        return tuple(sorted(matches)), confidence

    @staticmethod
    def _classify(text: str) -> NewsEventCategory:
        normalized = text.casefold()
        rules = (
            (("dividend", "cash distribution", "coupon"), NewsEventCategory.DIVIDEND),
            (("earnings", "net profit", "financial results", "quarterly results"), NewsEventCategory.EARNINGS),
            (("trading suspension", "suspend trading", "halt trading"), NewsEventCategory.TRADING_SUSPENSION),
            (("capital increase", "capital reduction", "share split", "stock split"), NewsEventCategory.CAPITAL_CHANGE),
            (("acquisition", "merger", "tender offer", "buyout"), NewsEventCategory.CORPORATE_ACTION),
            (("central bank", "interest rate", "inflation", "monetary policy"), NewsEventCategory.MACROECONOMIC),
            (("regulator", "regulatory", "financial regulatory authority"), NewsEventCategory.REGULATORY),
            (("lawsuit", "court", "litigation"), NewsEventCategory.LITIGATION),
            (("management", "board of directors", "chief executive"), NewsEventCategory.MANAGEMENT),
        )
        for keywords, category in rules:
            if any(keyword in normalized for keyword in keywords):
                return category
        return NewsEventCategory.UNKNOWN
