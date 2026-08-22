"""POST /api/v1/contact/site-analysis — the authorisation and error contract.

Two properties matter more than the payload shape:

* Nothing is fetched before the caller proves it holds a verified-email token.
  Otherwise the endpoint is an open outbound-request proxy.
* A broken third-party site is never our 500. A rejected URL is a 400, an
  unreachable one is a 200 with partial signals.
"""

import logging

import httpx
import pytest
from fastapi.testclient import TestClient

from app.api.v1.site_analysis import (
    AccessTokenVerifier,
    FlowNotConfigured,
    InvalidAccessToken,
    get_access_token_verifier,
    get_site_analyser,
)
from app.main import create_app
from app.services.site_analysis import SiteSignals
from app.services.url_guard import UrlRejected

VERIFIED_EMAIL = "ada@example.com"
BEARER = {"Authorization": "Bearer valid-token"}


class StubVerifier:
    """Stands in for the Phase A token service, which is not merged yet."""

    def __init__(self, *, email: str = VERIFIED_EMAIL, error: Exception | None = None) -> None:
        self.email = email
        self.error = error
        self.seen: list[str] = []

    def verified_email(self, token: str) -> str:
        self.seen.append(token)

        if self.error is not None:
            raise self.error

        return self.email


class StubAnalyser:
    def __init__(self, result: SiteSignals | Exception) -> None:
        self.result = result
        self.calls: list[str] = []

    async def __call__(self, url: str) -> SiteSignals:
        self.calls.append(url)

        if isinstance(self.result, Exception):
            raise self.result

        return self.result


def build_client(
    *,
    verifier: AccessTokenVerifier | None = None,
    analyser: StubAnalyser | None = None,
) -> TestClient:
    app = create_app()

    if verifier is not None:
        app.dependency_overrides[get_access_token_verifier] = lambda: verifier
    if analyser is not None:
        app.dependency_overrides[get_site_analyser] = lambda: analyser

    return TestClient(app)


AVAILABLE = SiteSignals(
    requested_url="https://acme.example/",
    final_url="https://acme.example/",
    available=True,
    status_code=200,
    https=True,
    title="Acme Corp",
)


class TestAuthorisation:
    def test_without_a_token_it_is_401_and_nothing_is_fetched(self) -> None:
        analyser = StubAnalyser(AVAILABLE)
        client = build_client(verifier=StubVerifier(), analyser=analyser)

        response = client.post(
            "/api/v1/contact/site-analysis", json={"url": "https://acme.example"}
        )

        assert response.status_code == 401
        assert analyser.calls == []

    @pytest.mark.parametrize(
        "header",
        [
            {"Authorization": "valid-token"},
            {"Authorization": "Basic valid-token"},
            {"Authorization": "Bearer"},
            {"Authorization": "Bearer   "},
            {"Authorization": ""},
        ],
    )
    def test_a_malformed_authorization_header_is_401(self, header: dict[str, str]) -> None:
        analyser = StubAnalyser(AVAILABLE)
        client = build_client(verifier=StubVerifier(), analyser=analyser)

        response = client.post(
            "/api/v1/contact/site-analysis",
            json={"url": "https://acme.example"},
            headers=header,
        )

        assert response.status_code == 401
        assert analyser.calls == []

    def test_a_rejected_token_is_401_and_nothing_is_fetched(self) -> None:
        analyser = StubAnalyser(AVAILABLE)
        client = build_client(
            verifier=StubVerifier(error=InvalidAccessToken("expired")), analyser=analyser
        )

        response = client.post(
            "/api/v1/contact/site-analysis",
            json={"url": "https://acme.example"},
            headers=BEARER,
        )

        assert response.status_code == 401
        assert analyser.calls == []

    def test_an_unconfigured_flow_is_503(self) -> None:
        analyser = StubAnalyser(AVAILABLE)
        client = build_client(
            verifier=StubVerifier(error=FlowNotConfigured("no secret")), analyser=analyser
        )

        response = client.post(
            "/api/v1/contact/site-analysis",
            json={"url": "https://acme.example"},
            headers=BEARER,
        )

        assert response.status_code == 503
        assert analyser.calls == []

    def test_the_default_verifier_refuses_everything(self) -> None:
        # Nothing is wired until Phase A lands, and the safe default is refusal.
        client = build_client(analyser=StubAnalyser(AVAILABLE))

        response = client.post(
            "/api/v1/contact/site-analysis",
            json={"url": "https://acme.example"},
            headers=BEARER,
        )

        assert response.status_code == 503


class TestAnalysisOutcome:
    def test_a_valid_request_returns_the_signals(self) -> None:
        analyser = StubAnalyser(AVAILABLE)
        client = build_client(verifier=StubVerifier(), analyser=analyser)

        response = client.post(
            "/api/v1/contact/site-analysis",
            json={"url": "https://acme.example"},
            headers=BEARER,
        )

        assert response.status_code == 200
        assert response.json()["available"] is True
        assert response.json()["title"] == "Acme Corp"
        assert analyser.calls == ["https://acme.example"]

    @pytest.mark.parametrize("reason", ["private_address", "bad_scheme", "credentials", "bad_port"])
    def test_a_blocked_url_is_400_carrying_the_reason(self, reason: str) -> None:
        client = build_client(
            verifier=StubVerifier(), analyser=StubAnalyser(UrlRejected(reason, "detail"))
        )

        response = client.post(
            "/api/v1/contact/site-analysis",
            json={"url": "http://10.0.0.1/"},
            headers=BEARER,
        )

        assert response.status_code == 400
        # FastAPI nests HTTPException payloads under `detail`.
        assert response.json()["detail"]["reason"] == reason

    def test_an_unreachable_site_is_200_with_partial_signals(self) -> None:
        unavailable = SiteSignals(
            requested_url="https://down.example/",
            available=False,
            unavailable_reason="timeout",
        )
        client = build_client(verifier=StubVerifier(), analyser=StubAnalyser(unavailable))

        response = client.post(
            "/api/v1/contact/site-analysis",
            json={"url": "https://down.example"},
            headers=BEARER,
        )

        # The chat must be able to continue without a working site.
        assert response.status_code == 200
        assert response.json()["available"] is False
        assert response.json()["unavailable_reason"] == "timeout"

    def test_an_unexpected_analyser_failure_is_502_not_500(self) -> None:
        client = build_client(
            verifier=StubVerifier(), analyser=StubAnalyser(RuntimeError("client exploded"))
        )

        response = client.post(
            "/api/v1/contact/site-analysis",
            json={"url": "https://acme.example"},
            headers=BEARER,
        )

        assert response.status_code == 502

    @pytest.mark.parametrize(
        "payload",
        [{}, {"url": ""}, {"url": "   "}, {"url": "x" * 2100}, {"wrong": "field"}],
    )
    def test_a_malformed_body_is_rejected_before_any_fetch(self, payload: dict) -> None:
        analyser = StubAnalyser(AVAILABLE)
        client = build_client(verifier=StubVerifier(), analyser=analyser)

        response = client.post("/api/v1/contact/site-analysis", json=payload, headers=BEARER)

        assert response.status_code in {400, 422}
        assert analyser.calls == []


class TestLogging:
    def test_logs_carry_the_host_but_never_the_email_or_query(
        self, caplog: pytest.LogCaptureFixture
    ) -> None:
        analyser = StubAnalyser(AVAILABLE)
        client = build_client(verifier=StubVerifier(), analyser=analyser)

        with caplog.at_level(logging.INFO):
            client.post(
                "/api/v1/contact/site-analysis",
                json={"url": "https://acme.example/?utm_source=secret-campaign"},
                headers=BEARER,
            )

        logged = "\n".join(record.getMessage() for record in caplog.records)

        assert VERIFIED_EMAIL not in logged
        assert "secret-campaign" not in logged
        # The host alone is enough to debug an abuse pattern.
        assert "acme.example" in logged


@pytest.mark.anyio
class TestProductionWiring:
    """The default analyser is the one path tests always override away.

    It is also the only place where a wrong client setting would silently undo
    the redirect guard, so its construction is asserted directly.
    """

    async def test_the_real_analyser_never_lets_httpx_follow_redirects(
        self, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        from app.api.v1 import site_analysis as module

        captured: dict[str, object] = {}
        real_client = httpx.AsyncClient

        def spy(*args: object, **kwargs: object) -> httpx.AsyncClient:
            captured.update(kwargs)
            # A transport that answers everything keeps this off the network.
            return real_client(
                transport=httpx.MockTransport(
                    lambda request: httpx.Response(200, text="<html><title>t</title></html>")
                )
            )

        monkeypatch.setattr(module.httpx, "AsyncClient", spy)
        monkeypatch.setattr(
            module,
            "analyse_site",
            lambda url, client, **kw: _noop_signals(url),  # type: ignore[arg-type]
        )

        analyser = module.get_site_analyser()
        await analyser("https://acme.example/")

        # follow_redirects=True here would bypass the per-hop guard entirely.
        assert captured["follow_redirects"] is False
        assert captured["timeout"] is not None


async def _noop_signals(url: str) -> SiteSignals:
    return SiteSignals(requested_url=url, available=False, unavailable_reason="stubbed")
