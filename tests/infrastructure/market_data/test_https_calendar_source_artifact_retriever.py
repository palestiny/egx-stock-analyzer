import pytest

from app.application.market_data.calendar_source_authenticity import (
    CalendarSourceAuthenticityError,
    normalize_calendar_source_origin,
)
from app.infrastructure.market_data.https_calendar_source_artifact_retriever import (
    HTTPSCalendarSourceArtifactRetriever,
)


class _Response:
    def __init__(self, status=200, body=b"official bytes", headers=None):
        self.status = status
        self._body = body
        self._headers = headers or {}

    def getheader(self, name):
        return self._headers.get(name)

    def read(self, size=-1):
        return self._body[:size]


class _Connection:
    def __init__(self, response):
        self.response = response
        self.requests = []
        self.closed = False

    def request(self, method, target, *, headers):
        self.requests.append((method, target, headers))

    def getresponse(self):
        return self.response

    def close(self):
        self.closed = True


def _resolver(address="93.184.216.34"):
    def resolve(host, port, *, type):
        assert host == "calendar.example.test"
        assert port == 443
        return [(2, 1, 6, "", (address, 443))]
    return resolve


def test_retriever_uses_pinned_public_ip_and_does_not_follow_redirects():
    connection = _Connection(_Response(
        status=302,
        body=b"",
        headers={"Location": "https://other.example.test/notice"},
    ))
    retriever = HTTPSCalendarSourceArtifactRetriever(
        resolver=_resolver(),
        connection_factory=lambda *args, **kwargs: connection,
    )
    result = retriever.retrieve("https://calendar.example.test/notice?id=1")
    assert result.status_code == 302
    assert result.redirect_urls == ("https://other.example.test/notice",)
    assert result.final_url == result.requested_url
    assert connection.requests[0][0] == "GET"
    assert connection.requests[0][1] == "/notice?id=1"
    assert connection.closed is True


def test_retriever_rejects_private_ip_resolution_before_connecting():
    called = False

    def factory(*args, **kwargs):
        nonlocal called
        called = True
        raise AssertionError("private address must not be connected")

    retriever = HTTPSCalendarSourceArtifactRetriever(
        resolver=_resolver("127.0.0.1"),
        connection_factory=factory,
    )
    with pytest.raises(CalendarSourceAuthenticityError, match="non-public IP"):
        retriever.retrieve("https://calendar.example.test/notice")
    assert called is False


def test_retriever_enforces_response_size_limit():
    connection = _Connection(_Response(body=b"12345"))
    retriever = HTTPSCalendarSourceArtifactRetriever(
        resolver=_resolver(),
        connection_factory=lambda *args, **kwargs: connection,
        max_response_bytes=4,
    )
    with pytest.raises(CalendarSourceAuthenticityError, match="response-size limit"):
        retriever.retrieve("https://calendar.example.test/notice")


@pytest.mark.parametrize("url", [
    "https://127.0.0.1/notice",
    "https://[2606:4700:4700::1111]/notice",
    "https://calendar.example.test./notice",
])
def test_origin_normalization_rejects_ip_literals_and_trailing_dot(url):
    with pytest.raises(CalendarSourceAuthenticityError):
        normalize_calendar_source_origin(url)
