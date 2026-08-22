"""The URL guard is the security boundary of the site-analysis feature.

The backend fetches a URL a stranger typed into a chat box. Without this guard
that is a server-side request forgery primitive: an attacker names an internal
address and the backend reads it for them — the cloud metadata endpoint being
the classic prize.

Every case below is a way that has worked in the wild. DNS resolution is
injected, so no test performs real network I/O.
"""

import pytest

from app.services.url_guard import (
    ALLOWED_PORTS,
    UrlRejected,
    UrlUnresolvable,
    guard_url,
)

PUBLIC_IP = "93.184.216.34"


def resolving_to(*addresses: str):
    """A resolver stub that answers every host with the given addresses."""

    def _resolve(host: str) -> list[str]:
        return list(addresses)

    return _resolve


def failing_resolver(host: str) -> list[str]:
    raise UrlUnresolvable(host)


class TestScheme:
    @pytest.mark.parametrize(
        "url",
        [
            "file:///etc/passwd",
            "ftp://example.com/",
            "gopher://example.com/",
            "data:text/plain,hello",
            "dict://example.com:11211/",
            "//example.com/",
        ],
    )
    def test_rejects_non_http_schemes(self, url: str) -> None:
        # gopher:// and dict:// are classic SSRF pivots into Redis/memcached.
        with pytest.raises(UrlRejected):
            guard_url(url, resolve=resolving_to(PUBLIC_IP))

    @pytest.mark.parametrize("url", ["http://example.com/", "https://example.com/"])
    def test_accepts_http_and_https(self, url: str) -> None:
        assert guard_url(url, resolve=resolving_to(PUBLIC_IP))


class TestCredentials:
    @pytest.mark.parametrize(
        "url",
        [
            "http://user:pass@example.com/",
            "http://user@example.com/",
            "https://admin:hunter2@example.com/admin",
        ],
    )
    def test_rejects_embedded_credentials(self, url: str) -> None:
        # Credentials in the URL let an attacker aim the backend at an
        # authenticated internal endpoint using its network position.
        with pytest.raises(UrlRejected):
            guard_url(url, resolve=resolving_to(PUBLIC_IP))


class TestHostShape:
    @pytest.mark.parametrize(
        "url",
        ["", "   ", "not-a-url", "http://", "http:///path", "https://:443/", "http://[/"],
    )
    def test_rejects_unparseable_or_hostless_urls(self, url: str) -> None:
        with pytest.raises(UrlRejected):
            guard_url(url, resolve=resolving_to(PUBLIC_IP))


class TestResolvedAddress:
    @pytest.mark.parametrize(
        ("label", "address"),
        [
            ("ipv4 loopback", "127.0.0.1"),
            ("ipv4 loopback range", "127.53.1.9"),
            ("ipv6 loopback", "::1"),
            # `::ffff:127.0.0.1`.is_loopback is False in the stdlib: the mapped
            # v4 address must be unwrapped explicitly or loopback slips through.
            ("ipv4-mapped ipv6 loopback", "::ffff:127.0.0.1"),
            ("ipv4-mapped ipv6 private", "::ffff:10.0.0.1"),
            ("rfc1918 10/8", "10.0.0.1"),
            ("rfc1918 172.16/12", "172.16.0.1"),
            ("rfc1918 192.168/16", "192.168.1.1"),
            ("carrier-grade nat", "100.64.0.1"),
            ("link-local", "169.254.1.1"),
            ("cloud metadata", "169.254.169.254"),
            ("ipv6 link-local", "fe80::1"),
            ("ipv6 unique local", "fd00::1"),
            # ipaddress reports is_global=True for multicast, so a guard built
            # on that predicate alone would wave this through.
            ("multicast", "224.0.0.1"),
            ("ipv6 multicast", "ff02::1"),
            ("unspecified", "0.0.0.0"),
            ("ipv6 unspecified", "::"),
            ("reserved", "240.0.0.1"),
            # is_private=False but not routable either: the IANA
            # special-purpose registries are what catch these.
            ("documentation range", "192.0.2.1"),
            ("benchmarking range", "198.18.0.1"),
        ],
    )
    def test_rejects_non_public_addresses(self, label: str, address: str) -> None:
        with pytest.raises(UrlRejected):
            guard_url("http://internal.example.com/", resolve=resolving_to(address))

    def test_rejects_a_public_hostname_that_resolves_privately(self) -> None:
        # The whole point of resolving at request time: the hostname looks
        # innocent, the answer does not.
        with pytest.raises(UrlRejected):
            guard_url("https://totally-legit.example.com/", resolve=resolving_to("10.1.2.3"))

    def test_rejects_when_any_answer_is_private(self) -> None:
        # Defence in depth: a mixed answer set means the connect could land on
        # the private one, so the whole target is refused.
        with pytest.raises(UrlRejected):
            guard_url("http://example.com/", resolve=resolving_to(PUBLIC_IP, "127.0.0.1"))

    def test_rejects_an_empty_answer_set(self) -> None:
        with pytest.raises(UrlRejected):
            guard_url("http://example.com/", resolve=resolving_to())

    @pytest.mark.parametrize(
        "address", [PUBLIC_IP, "2606:2800:220:1:248:1893:25c8:1946", "1.1.1.1"]
    )
    def test_accepts_public_addresses(self, address: str) -> None:
        assert guard_url("http://example.com/", resolve=resolving_to(address))

    def test_accepts_a_literal_public_ip(self) -> None:
        assert guard_url(f"http://{PUBLIC_IP}/", resolve=resolving_to(PUBLIC_IP))

    def test_literal_private_ip_is_rejected_without_consulting_dns(self) -> None:
        def exploding_resolver(host: str) -> list[str]:
            raise AssertionError("a literal IP must not be resolved")

        with pytest.raises(UrlRejected):
            guard_url("http://127.0.0.1:80/", resolve=exploding_resolver)


class TestPort:
    @pytest.mark.parametrize("port", sorted(ALLOWED_PORTS))
    def test_accepts_web_ports(self, port: int) -> None:
        assert guard_url(f"http://example.com:{port}/", resolve=resolving_to(PUBLIC_IP))

    @pytest.mark.parametrize("port", [22, 25, 3306, 5432, 6379, 8000, 8080, 9200, 11211])
    def test_rejects_other_ports(self, port: int) -> None:
        # A company home page lives on 80/443. Allowing arbitrary ports turns
        # the endpoint into a port scanner with the backend's network position.
        with pytest.raises(UrlRejected):
            guard_url(f"http://example.com:{port}/", resolve=resolving_to(PUBLIC_IP))


class TestUnresolvable:
    def test_dns_failure_is_unresolvable_not_rejected(self) -> None:
        # A typo'd domain is an unreachable site, not an attack: the caller
        # degrades to partial signals instead of returning a 400.
        with pytest.raises(UrlUnresolvable):
            guard_url("http://no-such-domain.example/", resolve=failing_resolver)


class TestNormalisation:
    def test_returns_the_url_it_validated(self) -> None:
        assert guard_url("https://example.com/path?q=1", resolve=resolving_to(PUBLIC_IP)) == (
            "https://example.com/path?q=1"
        )

    def test_adds_a_scheme_free_bare_host_as_https(self) -> None:
        # Visitors type "example.com". Assuming https is the safe default and
        # keeps the guard from rejecting an honest answer on a technicality.
        assert guard_url("example.com", resolve=resolving_to(PUBLIC_IP)) == "https://example.com"

    def test_strips_surrounding_whitespace(self) -> None:
        assert guard_url("  https://example.com/  ", resolve=resolving_to(PUBLIC_IP)) == (
            "https://example.com/"
        )

    def test_rejection_carries_a_machine_readable_reason(self) -> None:
        with pytest.raises(UrlRejected) as excinfo:
            guard_url("http://10.0.0.1/", resolve=resolving_to("10.0.0.1"))

        assert excinfo.value.reason == "private_address"


class TestDefaultResolver:
    def test_uses_the_system_resolver(self, monkeypatch: pytest.MonkeyPatch) -> None:
        import socket

        from app.services import url_guard

        calls: list[str] = []

        def fake_getaddrinfo(host: str, *args: object, **kwargs: object) -> list[tuple]:
            calls.append(host)
            return [(socket.AF_INET, socket.SOCK_STREAM, 6, "", (PUBLIC_IP, 443))]

        monkeypatch.setattr(url_guard.socket, "getaddrinfo", fake_getaddrinfo)

        assert url_guard.resolve_host("example.com") == [PUBLIC_IP]
        assert calls == ["example.com"]

    def test_translates_a_resolver_error(self, monkeypatch: pytest.MonkeyPatch) -> None:
        import socket

        from app.services import url_guard

        def failing(host: str, *args: object, **kwargs: object) -> list[tuple]:
            raise socket.gaierror("nope")

        monkeypatch.setattr(url_guard.socket, "getaddrinfo", failing)

        with pytest.raises(UrlUnresolvable):
            url_guard.resolve_host("example.com")
