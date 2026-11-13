from __future__ import annotations

import http.client
import ipaddress
import socket
import ssl
from typing import Callable
from urllib.parse import urlsplit, urlunsplit

from app.application.market_data.calendar_source_authenticity import (
    CalendarSourceAuthenticityError,
    RetrievedCalendarSourceArtifact,
    normalize_calendar_source_origin,
)


class _PinnedHTTPSConnection(http.client.HTTPSConnection):
    """HTTPS connection pinned to a prevalidated public IP while retaining host TLS identity."""

    def __init__(
        self,
        hostname: str,
        address: str,
        *,
        timeout: float,
        context: ssl.SSLContext,
    ) -> None:
        super().__init__(hostname, port=443, timeout=timeout, context=context)
        self._pinned_address = address

    def connect(self) -> None:
        raw = socket.create_connection(
            (self._pinned_address, 443),
            timeout=self.timeout,
        )
        try:
            self.sock = self._context.wrap_socket(
                raw,
                server_hostname=self.host,
            )
        except Exception:
            raw.close()
            raise


class HTTPSCalendarSourceArtifactRetriever:
    """Direct HTTPS retrieval with TLS verification, public-IP pinning, and no redirects."""

    def __init__(
        self,
        *,
        timeout_seconds: float = 8.0,
        max_response_bytes: int = 20 * 1024 * 1024,
        resolver: Callable = socket.getaddrinfo,
        connection_factory: Callable = _PinnedHTTPSConnection,
    ) -> None:
        if timeout_seconds <= 0:
            raise ValueError("timeout_seconds must be positive")
        if max_response_bytes <= 0:
            raise ValueError("max_response_bytes must be positive")
        self._timeout = timeout_seconds
        self._max_response_bytes = max_response_bytes
        self._resolver = resolver
        self._connection_factory = connection_factory
        self._ssl_context = ssl.create_default_context()

    def retrieve(self, url: str) -> RetrievedCalendarSourceArtifact:
        origin = normalize_calendar_source_origin(url)
        parsed = urlsplit(url)
        hostname = parsed.hostname
        if hostname is None:
            raise CalendarSourceAuthenticityError("Source URL has no hostname")

        try:
            resolved = self._resolver(hostname, 443, type=socket.SOCK_STREAM)
        except OSError as error:
            raise CalendarSourceAuthenticityError("Source hostname could not be resolved") from error
        addresses = sorted({item[4][0] for item in resolved})
        if not addresses:
            raise CalendarSourceAuthenticityError("Source hostname returned no IP addresses")
        parsed_addresses = []
        for address in addresses:
            try:
                parsed_address = ipaddress.ip_address(address.split("%", 1)[0])
            except ValueError as error:
                raise CalendarSourceAuthenticityError("Source hostname resolved to an invalid IP address") from error
            if not parsed_address.is_global:
                raise CalendarSourceAuthenticityError(
                    "Source hostname resolves to a non-public IP address"
                )
            parsed_addresses.append(str(parsed_address))

        request_target = urlunsplit(("", "", parsed.path or "/", parsed.query, ""))
        connection = self._connection_factory(
            hostname,
            parsed_addresses[0],
            timeout=self._timeout,
            context=self._ssl_context,
        )
        try:
            connection.request(
                "GET",
                request_target,
                headers={
                    "Accept": "application/pdf,application/octet-stream,text/html,*/*;q=0.5",
                    "User-Agent": "EGX-Calendar-Evidence-Verifier/1.0",
                    "Connection": "close",
                },
            )
            response = connection.getresponse()
            location = response.getheader("Location")
            if response.status in {301, 302, 303, 307, 308} and location:
                redirect_urls = (location,)
            else:
                redirect_urls = ()
            content = response.read(self._max_response_bytes + 1)
            if len(content) > self._max_response_bytes:
                raise CalendarSourceAuthenticityError(
                    "Calendar source artifact exceeds the configured response-size limit"
                )
            final_url = url if not redirect_urls else url
            return RetrievedCalendarSourceArtifact(
                requested_url=url,
                final_url=final_url,
                redirect_urls=redirect_urls,
                tls_verified=True,
                status_code=response.status,
                content=content,
                content_type=response.getheader("Content-Type"),
            )
        except (OSError, ssl.SSLError, http.client.HTTPException) as error:
            raise CalendarSourceAuthenticityError(
                "Calendar source HTTPS retrieval failed"
            ) from error
        finally:
            connection.close()
