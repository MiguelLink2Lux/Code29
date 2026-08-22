"""Fetching a lead's home page: redirects, size cap and timeouts.

A guard that only checks the URL the visitor typed is defeated by one redirect,
so every hop is re-validated. All traffic here goes through httpx.MockTransport:
no test opens a socket.
"""

import httpx
import pytest

from app.services.site_analysis import (
    MAX_REDIRECT_HOPS,
    MAX_RESPONSE_BYTES,
    FetchOutcome,
    fetch_home,
)
from app.services.url_guard import UrlRejected

PUBLIC_IP = "93.184.216.34"


def public_resolver(host: str) -> list[str]:
    return [PUBLIC_IP]


def private_for(*private_hosts: str):
    """Resolver where the named hosts answer privately and everything else is public."""

    def _resolve(host: str) -> list[str]:
        return ["10.0.0.1"] if host in private_hosts else [PUBLIC_IP]

    return _resolve


class Recorder:
    """MockTransport handler that records every request it is asked to make."""

    def __init__(self, responses: dict[str, httpx.Response] | None = None) -> None:
        self.requests: list[httpx.Request] = []
        self.responses = responses or {}

    def __call__(self, request: httpx.Request) -> httpx.Response:
        self.requests.append(request)
        key = str(request.url)

        if key in self.responses:
            return self.responses[key]

        return httpx.Response(200, text="<html><title>ok</title></html>")

    @property
    def urls(self) -> list[str]:
        return [str(request.url) for request in self.requests]


def client_for(recorder: Recorder) -> httpx.AsyncClient:
    return httpx.AsyncClient(transport=httpx.MockTransport(recorder))


@pytest.mark.anyio
class TestRedirects:
    async def test_follows_a_public_redirect(self) -> None:
        recorder = Recorder(
            {
                "https://example.com/": httpx.Response(
                    302, headers={"location": "https://example.com/home"}
                ),
                "https://example.com/home": httpx.Response(200, text="<html>final</html>"),
            }
        )

        async with client_for(recorder) as client:
            outcome = await fetch_home(
                "https://example.com/", client=client, resolve=public_resolver
            )

        assert outcome.final_url == "https://example.com/home"
        assert outcome.status_code == 200
        assert "final" in outcome.body

    async def test_refuses_a_redirect_to_a_private_host_without_following_it(self) -> None:
        recorder = Recorder(
            {"https://example.com/": httpx.Response(302, headers={"location": "http://10.0.0.1/"})}
        )

        async with client_for(recorder) as client:
            with pytest.raises(UrlRejected):
                await fetch_home("https://example.com/", client=client, resolve=public_resolver)

        # The decisive assertion: the internal address was never requested.
        assert recorder.urls == ["https://example.com/"]

    async def test_refuses_a_redirect_to_a_public_name_resolving_privately(self) -> None:
        recorder = Recorder(
            {
                "https://example.com/": httpx.Response(
                    302, headers={"location": "https://intranet.example.com/"}
                )
            }
        )

        async with client_for(recorder) as client:
            with pytest.raises(UrlRejected):
                await fetch_home(
                    "https://example.com/",
                    client=client,
                    resolve=private_for("intranet.example.com"),
                )

        assert recorder.urls == ["https://example.com/"]

    async def test_refuses_a_redirect_to_a_non_http_scheme(self) -> None:
        recorder = Recorder(
            {
                "https://example.com/": httpx.Response(
                    302, headers={"location": "file:///etc/passwd"}
                )
            }
        )

        async with client_for(recorder) as client:
            with pytest.raises(UrlRejected):
                await fetch_home("https://example.com/", client=client, resolve=public_resolver)

        assert recorder.urls == ["https://example.com/"]

    async def test_resolves_a_relative_location_against_the_current_url(self) -> None:
        recorder = Recorder(
            {
                "https://example.com/old": httpx.Response(301, headers={"location": "/new"}),
                "https://example.com/new": httpx.Response(200, text="<html>new</html>"),
            }
        )

        async with client_for(recorder) as client:
            outcome = await fetch_home(
                "https://example.com/old", client=client, resolve=public_resolver
            )

        assert outcome.final_url == "https://example.com/new"

    async def test_stops_after_the_hop_limit(self) -> None:
        # Each hop points at the next: one more than the limit allows.
        responses = {
            f"https://example.com/{hop}": httpx.Response(
                302, headers={"location": f"https://example.com/{hop + 1}"}
            )
            for hop in range(MAX_REDIRECT_HOPS + 2)
        }
        recorder = Recorder(responses)

        async with client_for(recorder) as client:
            outcome = await fetch_home(
                "https://example.com/0", client=client, resolve=public_resolver
            )

        assert outcome.reachable is False
        assert outcome.reason == "too_many_redirects"
        assert len(recorder.requests) <= MAX_REDIRECT_HOPS + 1

    async def test_a_redirect_without_a_location_is_not_a_crash(self) -> None:
        recorder = Recorder({"https://example.com/": httpx.Response(302)})

        async with client_for(recorder) as client:
            outcome = await fetch_home(
                "https://example.com/", client=client, resolve=public_resolver
            )

        assert outcome.reachable is False
        assert outcome.reason == "redirect_without_location"


@pytest.mark.anyio
class TestSizeCap:
    async def test_reads_no_more_than_the_cap_and_flags_truncation(self) -> None:
        oversized = "<html>" + ("a" * (MAX_RESPONSE_BYTES * 2))
        recorder = Recorder({"https://example.com/": httpx.Response(200, text=oversized)})

        async with client_for(recorder) as client:
            outcome = await fetch_home(
                "https://example.com/", client=client, resolve=public_resolver
            )

        assert outcome.truncated is True
        assert len(outcome.body.encode("utf-8", "ignore")) <= MAX_RESPONSE_BYTES
        # Spec: analysis proceeds on what was read.
        assert outcome.reachable is True

    async def test_a_page_under_the_cap_is_not_flagged(self) -> None:
        recorder = Recorder(
            {"https://example.com/": httpx.Response(200, text="<html>small</html>")}
        )

        async with client_for(recorder) as client:
            outcome = await fetch_home(
                "https://example.com/", client=client, resolve=public_resolver
            )

        assert outcome.truncated is False
        assert outcome.body == "<html>small</html>"


@pytest.mark.anyio
class TestDegradation:
    @pytest.mark.parametrize(
        ("error", "expected_reason"),
        [
            (httpx.ConnectTimeout("slow"), "timeout"),
            (httpx.ReadTimeout("slow"), "timeout"),
            (httpx.ConnectError("refused"), "connection_failed"),
            (httpx.RemoteProtocolError("garbage"), "connection_failed"),
        ],
    )
    async def test_transport_failures_degrade_instead_of_raising(
        self, error: Exception, expected_reason: str
    ) -> None:
        def failing(request: httpx.Request) -> httpx.Response:
            raise error

        async with httpx.AsyncClient(transport=httpx.MockTransport(failing)) as client:
            outcome = await fetch_home(
                "https://example.com/", client=client, resolve=public_resolver
            )

        assert outcome.reachable is False
        assert outcome.reason == expected_reason
        assert outcome.body == ""

    async def test_an_unresolvable_host_degrades(self) -> None:
        from app.services.url_guard import UrlUnresolvable

        def failing_resolver(host: str) -> list[str]:
            raise UrlUnresolvable(host)

        recorder = Recorder()

        async with client_for(recorder) as client:
            outcome = await fetch_home(
                "https://no-such-domain.example/", client=client, resolve=failing_resolver
            )

        assert outcome.reachable is False
        assert outcome.reason == "dns_failure"
        assert recorder.requests == []

    async def test_a_server_error_is_still_reachable(self) -> None:
        # A 500 from the lead's site is a signal, not a failure of ours.
        recorder = Recorder({"https://example.com/": httpx.Response(500, text="boom")})

        async with client_for(recorder) as client:
            outcome = await fetch_home(
                "https://example.com/", client=client, resolve=public_resolver
            )

        assert outcome.reachable is True
        assert outcome.status_code == 500

    async def test_a_blocked_url_raises_rather_than_degrading(self) -> None:
        # Policy violation and unreachable site are different outcomes: one is a
        # 400 to the caller, the other a 200 with partial signals.
        recorder = Recorder()

        async with client_for(recorder) as client:
            with pytest.raises(UrlRejected):
                await fetch_home("http://169.254.169.254/", client=client, resolve=public_resolver)

        assert recorder.requests == []


@pytest.mark.anyio
class TestOutcomeShape:
    async def test_records_the_scheme_actually_used(self) -> None:
        recorder = Recorder({"http://example.com/": httpx.Response(200, text="<html></html>")})

        async with client_for(recorder) as client:
            outcome = await fetch_home(
                "http://example.com/", client=client, resolve=public_resolver
            )

        assert isinstance(outcome, FetchOutcome)
        assert outcome.https is False

    async def test_https_is_recorded_from_the_final_hop(self) -> None:
        recorder = Recorder(
            {
                "http://example.com/": httpx.Response(
                    301, headers={"location": "https://example.com/"}
                ),
                "https://example.com/": httpx.Response(200, text="<html></html>"),
            }
        )

        async with client_for(recorder) as client:
            outcome = await fetch_home(
                "http://example.com/", client=client, resolve=public_resolver
            )

        assert outcome.https is True
