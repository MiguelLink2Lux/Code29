"""Decide whether a URL a stranger typed may be requested at all.

This is the security boundary of the site-analysis feature. The backend fetches
a URL supplied through a public chat box; unguarded, that is a server-side
request forgery primitive — the attacker picks an internal address and reads
the response through us, with the cloud metadata endpoint as the classic prize.

Policy, in order: only http/https, no embedded credentials, a hostname that
looks like a real domain or a public IP literal, only ports 80/443, and every
address the hostname resolves to must be publicly routable. Resolution happens
here, at request time, because a public-looking hostname answering with
`10.0.0.1` is exactly the trick a scheme-and-shape check misses.
"""

from __future__ import annotations

import ipaddress
import re
import socket
from collections.abc import Callable
from urllib.parse import urlsplit, urlunsplit

ALLOWED_SCHEMES = frozenset({"http", "https"})

# A company home page is served on a web port. Allowing arbitrary ports turns
# this endpoint into a port scanner wearing the backend's network identity.
ALLOWED_PORTS = frozenset({80, 443})

# Hostname labels per RFC 1123, requiring at least one dot: "localhost" and
# "not-a-url" are not addresses of a public website.
_HOSTNAME = re.compile(
    r"^(?=.{1,253}$)(?!-)[A-Za-z0-9-]{1,63}(?<!-)(\.(?!-)[A-Za-z0-9-]{1,63}(?<!-))+\.?$"
)

Resolver = Callable[[str], list[str]]


class UrlRejected(Exception):
    """The URL must not be requested. `reason` is a stable machine-readable code."""

    def __init__(self, reason: str, detail: str = "") -> None:
        super().__init__(f"{reason}: {detail}" if detail else reason)
        self.reason = reason


class UrlUnresolvable(Exception):
    """The hostname does not resolve — an unreachable site, not an attack."""


def resolve_host(host: str) -> list[str]:
    """Every address `host` currently answers with, IPv4 and IPv6 alike."""
    try:
        answers = socket.getaddrinfo(host, None, proto=socket.IPPROTO_TCP)
    except (socket.gaierror, UnicodeError, OSError) as error:
        raise UrlUnresolvable(host) from error

    # sockaddr[0] is the address for both AF_INET and AF_INET6.
    return list(dict.fromkeys(str(answer[4][0]).split("%")[0] for answer in answers))


def _is_public_address(raw: str) -> bool:
    try:
        address = ipaddress.ip_address(raw)
    except ValueError:
        return False

    # `ipaddress.IPv6Address("::ffff:127.0.0.1").is_loopback` is False, so an
    # IPv4-mapped address has to be unwrapped or loopback slips straight through.
    if isinstance(address, ipaddress.IPv6Address) and address.ipv4_mapped is not None:
        address = address.ipv4_mapped

    # `is_global` tracks the IANA special-purpose registries, so it catches what
    # a hand-rolled list forgets — carrier-grade NAT (100.64/10) and the
    # documentation ranges are `is_private=False` but `is_global=False`.
    # It is not sufficient on its own: multicast addresses report is_global=True.
    if not address.is_global or address.is_multicast:
        return False

    # Restated explicitly rather than left to is_global: these are the
    # guarantees this boundary exists for, and they must not depend on a
    # stdlib classification changing between Python releases.
    return not (
        address.is_private
        or address.is_loopback
        or address.is_link_local
        or address.is_reserved
        or address.is_unspecified
    )


def _parse(raw: str) -> tuple[str, str, int | None, str]:
    """Return (scheme, hostname, port, normalised_url) or raise UrlRejected."""
    candidate = raw.strip()

    if not candidate:
        raise UrlRejected("empty_url")

    # Protocol-relative URLs are ambiguous about scheme; require an explicit one.
    if candidate.startswith("//"):
        raise UrlRejected("bad_scheme", "protocol-relative")

    try:
        parts = urlsplit(candidate)
    except ValueError as error:
        raise UrlRejected("bad_host", "unparseable") from error

    if not parts.scheme:
        # Visitors type "example.com"; https is the safe assumption.
        candidate = f"https://{candidate}"
        try:
            parts = urlsplit(candidate)
        except ValueError as error:
            raise UrlRejected("bad_host", "unparseable") from error

    if parts.scheme.lower() not in ALLOWED_SCHEMES:
        raise UrlRejected("bad_scheme", parts.scheme.lower())

    if parts.username or parts.password or "@" in parts.netloc:
        raise UrlRejected("credentials")

    try:
        hostname = parts.hostname
        port = parts.port
    except ValueError as error:
        # A malformed port or bracketed host raises on attribute access.
        raise UrlRejected("bad_host", "unparseable") from error

    if not hostname:
        raise UrlRejected("bad_host", "missing")

    if port is not None and port not in ALLOWED_PORTS:
        raise UrlRejected("bad_port", str(port))

    return parts.scheme.lower(), hostname, port, urlunsplit(parts)


def guard_url(raw: str, *, resolve: Resolver = resolve_host) -> str:
    """Return the URL to request, or raise UrlRejected / UrlUnresolvable.

    Raises:
        UrlRejected: the URL violates policy and must never be requested.
        UrlUnresolvable: the hostname does not resolve; treat as unreachable.
    """
    _, hostname, _, normalised = _parse(raw)

    # A literal address is checked directly: resolving it would be pointless and
    # would leak the attempt to DNS.
    try:
        ipaddress.ip_address(hostname)
    except ValueError:
        pass
    else:
        if not _is_public_address(hostname):
            raise UrlRejected("private_address", hostname)
        return normalised

    if not _HOSTNAME.match(hostname):
        raise UrlRejected("bad_host", "not a domain name")

    addresses = resolve(hostname)

    if not addresses:
        raise UrlRejected("no_addresses", hostname)

    # Every answer must be public: a mixed set means the connect could still
    # land on the private one.
    for address in addresses:
        if not _is_public_address(address):
            raise UrlRejected("private_address", address)

    return normalised
