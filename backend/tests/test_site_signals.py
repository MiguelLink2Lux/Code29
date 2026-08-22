"""Signal extraction: only measured facts, never inference.

The report writer downstream is only as honest as this module. If a signal is
guessed here, the model presents the guess to a stranger as a finding about
their business — so absent data must read absent.
"""

import httpx
import pytest

from app.services.site_analysis import (
    FetchOutcome,
    analyse_site,
    extract_signals,
)

PUBLIC_IP = "93.184.216.34"

FIXTURE = """<!doctype html>
<html lang="es-ES">
<head>
  <title>  Acme Corp — Soluciones industriales
  </title>
  <meta name="description" content="Fabricamos maquinaria desde 1975.">
  <meta name="viewport" content="width=device-width, initial-scale=1">
  <meta name="generator" content="WordPress 6.4.2">
  <meta property="og:title" content="Acme Corp">
  <link rel="canonical" href="https://acme.example/">
  <link rel="stylesheet" href="/wp-content/themes/acme/style.css">
  <link rel="stylesheet" href="/css/print.css">
</head>
<body>
  <img src="/logo.png" alt="Acme">
  <img src='/hero.jpg' alt="Hero">
  <script src="/wp-includes/js/jquery.js"></script>
  <script>console.log('inline, not a resource')</script>
</body>
</html>
"""


def public_resolver(host: str) -> list[str]:
    return [PUBLIC_IP]


def outcome_for(body: str, **overrides: object) -> FetchOutcome:
    defaults: dict[str, object] = {
        "requested_url": "https://acme.example/",
        "final_url": "https://acme.example/",
        "status_code": 200,
        "headers": {},
        "body": body,
        "reachable": True,
        "https": True,
    }
    defaults.update(overrides)

    return FetchOutcome(**defaults)  # type: ignore[arg-type]


class TestContentSignals:
    def test_extracts_the_title_and_collapses_its_whitespace(self) -> None:
        signals = extract_signals(outcome_for(FIXTURE))
        assert signals.title == "Acme Corp — Soluciones industriales"

    def test_extracts_description_canonical_viewport_lang_and_open_graph(self) -> None:
        signals = extract_signals(outcome_for(FIXTURE))

        assert signals.meta_description == "Fabricamos maquinaria desde 1975."
        assert signals.canonical_url == "https://acme.example/"
        assert signals.viewport_declared is True
        assert signals.lang_declared == "es-ES"
        assert signals.open_graph_present is True

    def test_counts_referenced_resources_but_not_inline_scripts(self) -> None:
        signals = extract_signals(outcome_for(FIXTURE))

        assert signals.script_count == 1
        assert signals.stylesheet_count == 2
        assert signals.image_count == 2

    def test_measures_the_html_weight(self) -> None:
        signals = extract_signals(outcome_for(FIXTURE))
        assert signals.html_bytes == len(FIXTURE.encode("utf-8"))

    def test_a_bare_page_reports_absence_rather_than_guessing(self) -> None:
        signals = extract_signals(outcome_for("<html><body>hola</body></html>"))

        assert signals.title is None
        assert signals.meta_description is None
        assert signals.canonical_url is None
        assert signals.lang_declared is None
        assert signals.viewport_declared is False
        assert signals.open_graph_present is False
        assert signals.generator is None
        assert signals.script_count == 0

    @pytest.mark.parametrize(
        "body",
        [
            "<HTML><HEAD><TITLE>Upper</TITLE></HEAD></HTML>",
            "<html><head><title>Upper</title>",
            "<html><head ><title >Upper</title >",
        ],
    )
    def test_tolerates_sloppy_markup(self, body: str) -> None:
        # Real home pages are not well-formed; a parser strictness bug here
        # would silently report "no title" for a site that has one.
        assert extract_signals(outcome_for(body)).title == "Upper"

    def test_reads_single_quoted_attributes(self) -> None:
        body = "<html><head><meta name='description' content='Con comillas simples'></head></html>"
        assert extract_signals(outcome_for(body)).meta_description == "Con comillas simples"


class TestFrameworkDetection:
    def test_prefers_the_self_declared_generator(self) -> None:
        signals = extract_signals(outcome_for(FIXTURE))

        assert signals.generator == "WordPress 6.4.2"
        assert signals.framework_hint == "WordPress"

    @pytest.mark.parametrize(
        ("marker", "expected"),
        [
            ('<astro-island uid="x">', "Astro"),
            ('<script id="__NEXT_DATA__" type="application/json">', "Next.js"),
            ('<link href="/_nuxt/entry.css">', "Nuxt"),
            ('<div data-reactroot="">', "React"),
            ('<app-root ng-version="17.0.0">', "Angular"),
            ('<script src="https://cdn.shopify.com/s/files/app.js">', "Shopify"),
            ('<link href="/wp-content/themes/x/style.css">', "WordPress"),
        ],
    )
    def test_falls_back_to_body_markers(self, marker: str, expected: str) -> None:
        assert extract_signals(
            outcome_for(f"<html><body>{marker}</body></html>")
        ).framework_hint == (expected)

    def test_falls_back_to_the_powered_by_header(self) -> None:
        signals = extract_signals(outcome_for("<html></html>", headers={"x-powered-by": "Express"}))
        assert signals.framework_hint == "Express"

    def test_reports_nothing_when_there_is_no_evidence(self) -> None:
        assert (
            extract_signals(outcome_for("<html><body>plain</body></html>")).framework_hint is None
        )


class TestSecurityHeaders:
    def test_maps_each_header_to_whether_it_was_actually_present(self) -> None:
        signals = extract_signals(
            outcome_for(
                "<html></html>",
                headers={
                    "strict-transport-security": "max-age=63072000",
                    "content-security-policy": "default-src 'self'",
                    "server": "nginx",
                },
            )
        )

        assert signals.security_headers["strict-transport-security"] is True
        assert signals.security_headers["content-security-policy"] is True
        assert signals.security_headers["x-content-type-options"] is False
        assert signals.security_headers["referrer-policy"] is False
        assert signals.server == "nginx"

    def test_every_known_header_appears_in_the_map(self) -> None:
        # A missing key would render as "unknown" downstream instead of "absent".
        signals = extract_signals(outcome_for("<html></html>"))
        assert all(value is False for value in signals.security_headers.values())
        assert len(signals.security_headers) >= 6


class TestUnavailableSite:
    def test_carries_the_reason_and_invents_nothing(self) -> None:
        signals = extract_signals(
            FetchOutcome(requested_url="https://down.example/", reason="timeout")
        )

        assert signals.available is False
        assert signals.unavailable_reason == "timeout"
        assert signals.title is None
        assert signals.https is False
        assert signals.status_code is None
        assert signals.security_headers == {}
        assert signals.robots_txt_present is None

    def test_a_truncated_body_still_yields_what_was_read(self) -> None:
        signals = extract_signals(
            outcome_for("<html><head><title>Big</title></head>", truncated=True)
        )

        assert signals.available is True
        assert signals.truncated is True
        assert signals.title == "Big"


@pytest.mark.anyio
class TestProbes:
    async def test_reports_robots_and_sitemap_presence_from_their_status(self) -> None:
        def handler(request: httpx.Request) -> httpx.Response:
            if request.url.path == "/robots.txt":
                return httpx.Response(200, text="User-agent: *")
            if request.url.path == "/sitemap.xml":
                return httpx.Response(404)
            return httpx.Response(200, text=FIXTURE)

        async with httpx.AsyncClient(transport=httpx.MockTransport(handler)) as client:
            signals = await analyse_site(
                "https://acme.example/", client=client, resolve=public_resolver
            )

        assert signals.robots_txt_present is True
        # Absent, not unknown: the probe completed and the file was not there.
        assert signals.sitemap_present is False

    async def test_probes_the_origin_reached_after_a_redirect(self) -> None:
        seen: list[str] = []

        def handler(request: httpx.Request) -> httpx.Response:
            seen.append(str(request.url))
            if str(request.url) == "https://acme.example/":
                return httpx.Response(301, headers={"location": "https://www.acme.example/es/"})
            return httpx.Response(200, text=FIXTURE)

        async with httpx.AsyncClient(transport=httpx.MockTransport(handler)) as client:
            await analyse_site("https://acme.example/", client=client, resolve=public_resolver)

        # robots.txt lives at the origin actually served, not the one typed.
        assert "https://www.acme.example/robots.txt" in seen
        assert "https://www.acme.example/sitemap.xml" in seen

    async def test_a_failing_probe_is_unknown_not_absent(self) -> None:
        def handler(request: httpx.Request) -> httpx.Response:
            if request.url.path == "/":
                return httpx.Response(200, text=FIXTURE)
            raise httpx.ConnectError("probe refused")

        async with httpx.AsyncClient(transport=httpx.MockTransport(handler)) as client:
            signals = await analyse_site(
                "https://acme.example/", client=client, resolve=public_resolver
            )

        assert signals.robots_txt_present is None
        assert signals.sitemap_present is None

    async def test_no_probes_are_attempted_for_an_unreachable_site(self) -> None:
        attempts: list[str] = []

        def handler(request: httpx.Request) -> httpx.Response:
            attempts.append(str(request.url))
            raise httpx.ConnectTimeout("down")

        async with httpx.AsyncClient(transport=httpx.MockTransport(handler)) as client:
            signals = await analyse_site(
                "https://down.example/", client=client, resolve=public_resolver
            )

        assert signals.available is False
        assert len(attempts) == 1
