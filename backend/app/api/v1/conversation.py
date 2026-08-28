"""The conversation turn endpoint — the only door into the guided chat.

Stateless by construction: the client returns the signed envelope it was given,
and the budget (turn count) lives *inside* that signature, so it cannot be reset
by editing a field. Forging it would mean forging the HMAC.

Who decides what:

- the **server** decides whether the conversation is complete, never the client;
- the **access token** decides whether the address is verified, never the body;
- the **extractor** proposes facts, and only typed ones survive.

An unverified visitor can converse. They just cannot finish — completeness needs
the verified address, which lives in the token and never in the envelope.
"""

from __future__ import annotations

from fastapi import APIRouter, Header, HTTPException, Request, status
from pydantic import BaseModel, Field

from app.services.conversation import (
    MAX_MESSAGE_CHARS,
    ConversationFacts,
    EnvelopeTooLarge,
    NextStep,
    derive_next_step,
    is_complete,
    merge_facts,
    message_within_budget,
    missing_facts,
    open_envelope,
    seal_envelope,
    turns_exhausted,
)
from app.services.extraction import FactExtractor, redact_email
from app.services.prompt_guard import scan
from app.services.report_gemini import ModelResponseInvalid, ModelUnavailable
from app.services.tokens import InvalidToken, verify_access_token

router = APIRouter(prefix="/contact/conversation", tags=["contact"])


class TurnRequest(BaseModel):
    message: str = Field(min_length=1, max_length=MAX_MESSAGE_CHARS * 4)
    #: The envelope from the previous turn. Absent on the first one.
    envelope: str | None = None
    #: The language the visitor is being spoken to in. Defaulted rather than
    #: required: a client deployed before this field existed must keep working,
    #: and the two projects do not ship at the same instant.
    lang: str = "es"


class TurnResponse(BaseModel):
    reply: str
    envelope: str
    complete: bool
    exhausted: bool
    missing: list[str]
    #: What to ask for next. The server decides the script order — see
    #: `derive_next_step`. The client renders this; it does not compute it.
    next_step: NextStep
    blocked: bool = False


def _secret(request: Request) -> str:
    settings = request.app.state.settings

    if not settings.contact_token_secret.get_secret_value():
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail="The contact flow is not configured on this deployment.",
        )

    return settings.contact_token_secret.get_secret_value()


def _verified_email(authorization: str | None, secret: str) -> str | None:
    """The verified address, or None. A malformed header is not fatal: an
    unverified visitor is still allowed to talk, they just cannot finish."""
    if not authorization:
        return None

    token = authorization.removeprefix("Bearer ").strip()

    if not token:
        return None

    try:
        return verify_access_token(token, secret=secret)
    except InvalidToken:
        return None


@router.post(
    "/turn",
    response_model=TurnResponse,
    summary="Advance the guided conversation by one turn",
)
async def take_turn(
    payload: TurnRequest, request: Request, authorization: str | None = Header(default=None)
) -> TurnResponse:
    secret = _secret(request)
    message = payload.message.strip()

    if not message:
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY, detail="The message is empty."
        )

    if not message_within_budget(message):
        # 413 rather than 422: the payload is well-formed, just too expensive.
        raise HTTPException(
            status_code=status.HTTP_413_REQUEST_ENTITY_TOO_LARGE,
            detail=f"Messages are limited to {MAX_MESSAGE_CHARS} characters.",
        )

    held = ConversationFacts()
    turns = 0

    if payload.envelope:
        try:
            state = open_envelope(payload.envelope, secret=secret)
        except EnvelopeTooLarge as error:
            raise HTTPException(
                status_code=status.HTTP_413_REQUEST_ENTITY_TOO_LARGE,
                detail="The conversation state is too large.",
            ) from error
        except InvalidToken as error:
            # Terse on purpose: a forger learns nothing about why.
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="That conversation is no longer valid. Start a new one.",
            ) from error

        held, turns = state.facts, state.turns

        # A blocked conversation is over. Refused here, before anything else is
        # spent on it — and terse, because a forger learns nothing from 403.
        if state.blocked:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="That conversation is closed.",
            )

    email = _verified_email(authorization, secret)

    # Before the extractor, not after: a guard that runs late is a guard we paid
    # a model call to consult. Zero tolerance is in the response — there is no
    # warning and no second chance — never in the threshold, which is why an
    # engineering team can talk about its own prompts without losing the chat.
    if scan(message):
        return _blocked_turn(held, turns=turns, secret=secret, email=email)

    # Budget spent: close with what we have rather than looping. Not an error —
    # a partial report is worth more than a conversation that never ends.
    if turns_exhausted(turns):
        return TurnResponse(
            reply="Con esto tengo suficiente para preparar tu informe.",
            envelope=seal_envelope(held, turns=turns, secret=secret),
            complete=True,
            exhausted=True,
            missing=_missing(held, email),
            # Exhausted beats closing: the budget lives inside the signature, and
            # a closing invitation must never become a way to outlive it.
            next_step=derive_next_step(
                held, email_verified=email is not None, turns=turns, blocked=False
            ),
        )

    extractor: FactExtractor = request.app.state.fact_extractor

    # Redacted HERE, not inside the extractor: defence in depth. The extractor
    # redacts too, but this guarantees no implementation of that port — present
    # or future, ours or mistaken — can ever be handed an address.
    redacted, _ = redact_email(message)

    try:
        result = await extractor.extract(redacted, held, payload.lang)
    except (ModelUnavailable, ModelResponseInvalid) as error:
        # The model is a dependency like any other: its failure is a 502, never
        # a 500, and never a silent fallback that fabricates a reply.
        raise HTTPException(
            status_code=status.HTTP_502_BAD_GATEWAY,
            detail="No he podido procesar tu mensaje. Inténtalo de nuevo.",
        ) from error
    except ValueError as error:
        raise HTTPException(
            status_code=status.HTTP_413_REQUEST_ENTITY_TOO_LARGE, detail=str(error)
        ) from error

    facts = merge_facts(held, result.delta)
    turns += 1

    # The second net. The guard already refused the obvious shapes without paying
    # for a model call; this catches phrasing a regex cannot see. Advisory by
    # design — the model is the component under attack, so its own report can
    # never be the only control.
    if result.injection:
        return _blocked_turn(facts, turns=turns, secret=secret, email=email)

    return TurnResponse(
        reply=result.reply,
        envelope=seal_envelope(facts, turns=turns, secret=secret),
        complete=is_complete(facts, email_verified=email is not None),
        exhausted=turns_exhausted(turns),
        missing=_missing(facts, email),
        next_step=derive_next_step(
            facts, email_verified=email is not None, turns=turns, blocked=False
        ),
    )


def _blocked_turn(
    facts: ConversationFacts, *, turns: int, secret: str, email: str | None
) -> TurnResponse:
    """End the conversation. The flag is sealed, so the client cannot clear it.

    What this does NOT do is block the person: there is no store to remember one
    by (ADR 0006), so a visitor who drops the envelope starts a clean
    conversation. That bound is specified behaviour, not an oversight — see the
    spec of this cycle. The reply says nothing about what was detected: an
    attacker who learns which phrasing tripped the guard learns how to word the
    next attempt.
    """
    return TurnResponse(
        reply="No puedo continuar esta conversación.",
        envelope=seal_envelope(facts, turns=turns, secret=secret, blocked=True),
        complete=False,
        exhausted=False,
        missing=_missing(facts, email),
        next_step="blocked",
        blocked=True,
    )


def _missing(facts: ConversationFacts, email: str | None) -> list[str]:
    """What the conversation still needs, with the address named explicitly."""
    missing = missing_facts(facts)

    if email is None:
        missing.append("email")

    return missing
