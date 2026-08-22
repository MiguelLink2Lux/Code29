"""Fetch a lead's home page and extract objective technical signals.

Two rules shape this module:

1. **Never trust the URL, at any hop.** A guard applied only to what the visitor
   typed is defeated by a single redirect, so redirects are followed manually and
   every `Location` goes through the same guard. A client with
   `follow_redirects=True` would silently undo that.
2. **Degrade, do not fail.** A lead's site being slow, broken or absent is a
   fact about the lead, not an error of ours: the analysis returns partial
   signals with a reason and the chat carries on. The one exception is a URL the
   guard rejects — that is a policy violation and it propagates.

Everything reported here is measured. Nothing is inferred, so the report writer
downstream cannot be fed a guess dressed as a fact.
"""

from __future__ import annotations

import re
from dataclasses import dataclass, field

import httpx
from pydantic import BaseModel, Field

from app.services.url_guard import Resolver, UrlRejected, UrlUnresolvable, guard_url, resolve_host

MAX_REDIRECT_HOPS = 3
MAX_RESPONSE_BYTES = 512 * 1024
REQUEST_TIMEOUT_SECONDS = 6.0

REDIRECT_STATUS = frozenset({301, 302, 303, 307, 308})

USER_AGENT = "Code29-SiteAnalyzer/1.0 (+https://code29.dev)"

# Response headers worth reporting, and what each one means when absent.
SECURITY_HEADERS = (
    "strict-transport-security",
    "content-security-policy",
    "x-content-type-options",
    "x-frame-options",
    "referrer-policy",
    "permissions-policy",
)

# Closing tags in the wild carry stray whitespace (`</title >`); requiring the
# exact form silently reported "no title" for pages that have one.
_TITLE = re.compile(r"<title[^>]*>(.*?)</title\s*>", re.IGNORECASE | re.DOTALL)
_META = re.compile(r"<meta\s+([^>]+?)/?>", re.IGNORECASE)
_LINK = re.compile(r"<link\s+([^>]+?)/?>", re.IGNORECASE)
_ATTR = re.compile(r"([a-zA-Z-]+)\s*=\s*(\"([^\"]*)\"|'([^']*)'|([^\s\"'>]+))")
_SCRIPT_SRC = re.compile(r"<script[^>]+\bsrc\s*=", re.IGNORECASE)
_IMG_SRC = re.compile(r"<img[^>]+\bsrc\s*=", re.IGNORECASE)
_STYLESHEET = re.compile(r"<link[^>]+stylesheet", re.IGNORECASE)

# Framework fingerprints, ordered: the first match wins.
_FRAMEWORK_MARKERS: tuple[tuple[str, str], ...] = (
    ("astro-island", "Astro"),
    ("data-astro-cid", "Astro"),
    ("__NEXT_DATA__", "Next.js"),
    ("/_next/static", "Next.js"),
    ("__NUXT__", "Nuxt"),
    ("/_nuxt/", "Nuxt"),
    ("data-reactroot", "React"),
    ("ng-version", "Angular"),
    ("data-svelte", "Svelte"),
    ("wp-content", "WordPress"),
    ("wp-includes", "WordPress"),
    ("Shopify.theme", "Shopify"),
    ("cdn.shopify.com", "Shopify"),
    ("wix-warmup-data", "Wix"),
    ("squarespace", "Squarespace"),
    ("webflow", "Webflow"),
    ("drupal-settings-json", "Drupal"),
)


@dataclass
class FetchOutcome:
    """What a single home-page fetch attempt actually produced."""

    requested_url: str
    final_url: str | None = None
    status_code: int | None = None
    headers: dict[str, str] = field(default_factory=dict)
    body: str = ""
    reachable: bool = False
    reason: str | None = None
    truncated: bool = False
    https: bool = False
    redirect_hops: int = 0


class SiteSignals(BaseModel):
    """Measured facts about a home page. Absent data is reported absent."""

    requested_url: str
    final_url: str | None = None
    available: bool = False
    unavailable_reason: str | None = None
    status_code: int | None = None
    https: bool = False
    redirect_hops: int = 0
    security_headers: dict[str, bool] = Field(default_factory=dict)
    title: str | None = None
    meta_description: str | None = None
    canonical_url: str | None = None
    viewport_declared: bool = False
    lang_declared: str | None = None
    open_graph_present: bool = False
    generator: str | None = None
    framework_hint: str | None = None
    server: str | None = None
    html_bytes: int = 0
    truncated: bool = False
    script_count: int = 0
    stylesheet_count: int = 0
    image_count: int = 0
    robots_txt_present: bool | None = None
    sitemap_present: bool | None = None


def _timeout_extensions() -> dict[str, object]:
    # The cap belongs to the fetcher, not to whoever built the client: a caller
    # passing an untimed client must not be able to hang a serverless function.
    return {
        "timeout": {
            "connect": REQUEST_TIMEOUT_SECONDS,
            "read": REQUEST_TIMEOUT_SECONDS,
            "write": REQUEST_TIMEOUT_SECONDS,
            "pool": REQUEST_TIMEOUT_SECONDS,
        }
    }


async def _read_capped(response: httpx.Response) -> tuple[str, bool]:
    """Read at most MAX_RESPONSE_BYTES, reporting whether the body was cut short."""
    chunks: list[bytes] = []
    total = 0
    truncated = False

    async for chunk in response.aiter_bytes():
        remaining = MAX_RESPONSE_BYTES - total

        if len(chunk) >= remaining:
            chunks.append(chunk[:remaining])
            truncated = True
            break

        chunks.append(chunk)
        total += len(chunk)

    return b"".join(chunks).decode("utf-8", errors="replace"), truncated


async def fetch_home(
    raw_url: str,
    *,
    client: httpx.AsyncClient,
    resolve: Resolver = resolve_host,
) -> FetchOutcome:
    """Fetch a home page, re-validating every redirect hop.

    Raises:
        UrlRejected: the URL — or a hop it redirects to — violates policy.
    """
    try:
        current = guard_url(raw_url, resolve=resolve)
    except UrlUnresolvable:
        return FetchOutcome(requested_url=raw_url, reason="dns_failure")

    outcome = FetchOutcome(requested_url=raw_url)

    for hop in range(MAX_REDIRECT_HOPS + 1):
        outcome.redirect_hops = hop
        request = client.build_request(
            "GET",
            current,
            headers={"User-Agent": USER_AGENT, "Accept": "text/html,*/*;q=0.8"},
            extensions=_timeout_extensions(),
        )

        try:
            response = await client.send(request, stream=True)
        except httpx.TimeoutException:
            outcome.reason = "timeout"
            return outcome
        except httpx.HTTPError:
            # Connection refused, TLS failure, protocol garbage: all facts about
            # the lead's site, none of them our failure.
            outcome.reason = "connection_failed"
            return outcome

        try:
            if response.status_code in REDIRECT_STATUS:
                location = response.headers.get("location")

                if not location:
                    outcome.reason = "redirect_without_location"
                    return outcome

                target = str(httpx.URL(current).join(location))

                try:
                    # UrlRejected propagates: a redirect into private space is an
                    # attack signature, and it must never be requested.
                    current = guard_url(target, resolve=resolve)
                except UrlUnresolvable:
                    outcome.reason = "dns_failure"
                    return outcome

                continue

            body, truncated = await _read_capped(response)
        finally:
            await response.aclose()

        outcome.final_url = str(response.url)
        outcome.status_code = response.status_code
        outcome.headers = {name.lower(): value for name, value in response.headers.items()}
        outcome.body = body
        outcome.truncated = truncated
        outcome.reachable = True
        outcome.https = str(response.url).startswith("https://")
        return outcome

    outcome.reason = "too_many_redirects"
    return outcome


def _attributes(fragment: str) -> dict[str, str]:
    return {
        match.group(1).lower(): (match.group(3) or match.group(4) or match.group(5) or "")
        for match in _ATTR.finditer(fragment)
    }


def _extract_meta(body: str) -> tuple[str | None, bool, bool, str | None]:
    """Return (description, viewport_declared, open_graph_present, generator)."""
    description: str | None = None
    generator: str | None = None
    viewport = False
    open_graph = False

    for match in _META.finditer(body):
        attributes = _attributes(match.group(1))
        name = attributes.get("name", "").lower()
        prop = attributes.get("property", "").lower()
        content = attributes.get("content", "").strip()

        if name == "description" and content:
            description = content
        elif name == "viewport":
            viewport = True
        elif name == "generator" and content:
            generator = content
        elif prop.startswith("og:"):
            open_graph = True

    return description, viewport, open_graph, generator


def _extract_canonical(body: str) -> str | None:
    for match in _LINK.finditer(body):
        attributes = _attributes(match.group(1))
        if attributes.get("rel", "").lower() == "canonical":
            return attributes.get("href") or None

    return None


def _detect_framework(body: str, headers: dict[str, str], generator: str | None) -> str | None:
    # A self-declared generator is the strongest evidence available.
    if generator:
        return generator.split(" ")[0]

    for marker, name in _FRAMEWORK_MARKERS:
        if marker.lower() in body.lower():
            return name

    powered_by = headers.get("x-powered-by")

    return powered_by or None


def _extract_lang(body: str) -> str | None:
    match = re.search(r"<html[^>]*\blang\s*=\s*[\"']?([A-Za-z-]{2,10})", body, re.IGNORECASE)

    return match.group(1) if match else None


async def _probe(url: str, *, client: httpx.AsyncClient, resolve: Resolver) -> bool | None:
    """True/False if the probe completed, None if it could not be determined."""
    try:
        guarded = guard_url(url, resolve=resolve)
    except (UrlRejected, UrlUnresolvable):
        return None

    request = client.build_request(
        "GET", guarded, headers={"User-Agent": USER_AGENT}, extensions=_timeout_extensions()
    )

    try:
        response = await client.send(request, stream=True)
    except httpx.HTTPError:
        return None

    try:
        return response.status_code == 200
    finally:
        await response.aclose()


def extract_signals(outcome: FetchOutcome) -> SiteSignals:
    """Turn a fetch outcome into measured signals. Never guesses."""
    if not outcome.reachable:
        return SiteSignals(
            requested_url=outcome.requested_url,
            available=False,
            unavailable_reason=outcome.reason,
            redirect_hops=outcome.redirect_hops,
        )

    body = outcome.body
    description, viewport, open_graph, generator = _extract_meta(body)
    title_match = _TITLE.search(body)

    return SiteSignals(
        requested_url=outcome.requested_url,
        final_url=outcome.final_url,
        available=True,
        status_code=outcome.status_code,
        https=outcome.https,
        redirect_hops=outcome.redirect_hops,
        security_headers={name: name in outcome.headers for name in SECURITY_HEADERS},
        # Collapsed, not just stripped: a title split across source lines
        # renders as one line in a browser and must read that way in the report.
        title=" ".join(title_match.group(1).split()) if title_match else None,
        meta_description=description,
        canonical_url=_extract_canonical(body),
        viewport_declared=viewport,
        lang_declared=_extract_lang(body),
        open_graph_present=open_graph,
        generator=generator,
        framework_hint=_detect_framework(body, outcome.headers, generator),
        server=outcome.headers.get("server"),
        html_bytes=len(body.encode("utf-8", errors="ignore")),
        truncated=outcome.truncated,
        script_count=len(_SCRIPT_SRC.findall(body)),
        stylesheet_count=len(_STYLESHEET.findall(body)),
        image_count=len(_IMG_SRC.findall(body)),
    )


async def analyse_site(
    raw_url: str,
    *,
    client: httpx.AsyncClient,
    resolve: Resolver = resolve_host,
) -> SiteSignals:
    """Fetch the home page, then probe robots.txt and the sitemap.

    Raises:
        UrlRejected: the URL violates policy; the caller answers 400.
    """
    outcome = await fetch_home(raw_url, client=client, resolve=resolve)
    signals = extract_signals(outcome)

    if not signals.available or not signals.final_url:
        return signals

    origin = str(httpx.URL(signals.final_url).copy_with(path="/", query=None, fragment=None))
    signals.robots_txt_present = await _probe(f"{origin}robots.txt", client=client, resolve=resolve)
    signals.sitemap_present = await _probe(f"{origin}sitemap.xml", client=client, resolve=resolve)

    return signals
