"""Site-analysis endpoint: fetch a lead's home page behind the SSRF guard.

Authorisation comes first and unconditionally. Without it this route is an open
outbound-request proxy wearing the backend's network identity, so the token is
verified before the URL is even looked at — let alone requested.

The token service itself lands with the email-verification work; here it is a
`Protocol` with a refusing default, so this phase ships and deploys on its own
and the real verifier is wired in by injection, not by editing this module.
"""

from __future__ import annotations

import logging
from typing import Annotated, Protocol

import httpx
from fastapi import APIRouter, Depends, Header, HTTPException, status
from pydantic import BaseModel, Field

from app.services.site_analysis import (
    REQUEST_TIMEOUT_SECONDS,
    SiteSignals,
    analyse_site,
)
from app.services.url_guard import UrlRejected

logger = logging.getLogger(__name__)

router = APIRouter()

MAX_URL_LENGTH = 2048


class InvalidAccessToken(Exception):
    """The token is missing, malformed, forged or expired."""


class FlowNotConfigured(Exception):
    """The contact flow has no usable configuration, so nothing can be authorised."""


class AccessTokenVerifier(Protocol):
    def verified_email(self, token: str) -> str:
        """Return the verified address a token stands for, or raise."""
        ...


class UnconfiguredVerifier:
    """Default verifier: refuses everything.

    Failing closed is the only safe default for a route that makes outbound
    requests on behalf of an anonymous caller.
    """

    def verified_email(self, token: str) -> str:
        raise FlowNotConfigured("no access token verifier is configured")


class SiteAnalysisRequest(BaseModel):
    url: str = Field(min_length=1, max_length=MAX_URL_LENGTH)


class SiteAnalysisRejectedDetail(BaseModel):
    reason: str
    message: str


class SiteAnalysisRejected(BaseModel):
    """FastAPI nests HTTPException payloads under `detail`; the schema says so."""

    detail: SiteAnalysisRejectedDetail


def get_access_token_verifier() -> AccessTokenVerifier:
    """Injection point for the token service; overridden in tests and on wiring."""
    return UnconfiguredVerifier()


async def _analyse_with_a_fresh_client(url: str) -> SiteSignals:
    timeout = httpx.Timeout(REQUEST_TIMEOUT_SECONDS)

    # follow_redirects stays False: the hop loop in analyse_site re-validates
    # every Location, and letting httpx follow them would bypass the guard.
    async with httpx.AsyncClient(timeout=timeout, follow_redirects=False) as client:
        return await analyse_site(url, client=client)


def get_site_analyser():
    """Injection point for the analyser, so tests never touch the network."""
    return _analyse_with_a_fresh_client


def _bearer_token(header: str | None) -> str:
    if not header:
        raise InvalidAccessToken("missing authorization header")

    scheme, _, token = header.partition(" ")

    if scheme.lower() != "bearer" or not token.strip():
        raise InvalidAccessToken("malformed authorization header")

    return token.strip()


def _host_of(url: str) -> str:
    """Host only: a full URL may carry identifying query parameters."""
    try:
        return httpx.URL(url if "://" in url else f"https://{url}").host or "unknown"
    except (httpx.InvalidURL, ValueError, TypeError):
        return "unparseable"


@router.post(
    "/contact/site-analysis",
    response_model=SiteSignals,
    responses={400: {"model": SiteAnalysisRejected}},
    summary="Analyse a lead's home page for objective technical signals",
)
async def analyse(
    payload: SiteAnalysisRequest,
    verifier: Annotated[AccessTokenVerifier, Depends(get_access_token_verifier)],
    analyser: Annotated[object, Depends(get_site_analyser)],
    authorization: Annotated[str | None, Header()] = None,
) -> SiteSignals:
    try:
        token = _bearer_token(authorization)
        verifier.verified_email(token)
    except InvalidAccessToken:
        # Deliberately terse: an attacker learns nothing about why.
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="A verified email token is required.",
        ) from None
    except FlowNotConfigured:
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail="The contact flow is not configured.",
        ) from None

    url = payload.url.strip()

    if not url:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail={"reason": "empty_url", "message": "A URL is required."},
        )

    host = _host_of(url)

    try:
        signals = await analyser(url)  # type: ignore[operator]
    except UrlRejected as rejected:
        logger.info("site analysis blocked host=%s reason=%s", host, rejected.reason)
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail={
                "reason": rejected.reason,
                "message": "That address cannot be analysed.",
            },
        ) from None
    except Exception:
        # A bug in our own client must not read as the lead's site being broken.
        logger.exception("site analysis failed unexpectedly host=%s", host)
        raise HTTPException(
            status_code=status.HTTP_502_BAD_GATEWAY,
            detail="The site could not be analysed right now.",
        ) from None

    logger.info(
        "site analysis complete host=%s available=%s reason=%s",
        host,
        signals.available,
        signals.unavailable_reason,
    )

    return signals
