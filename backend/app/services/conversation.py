"""Conversation state for a serverless backend: signed, carried by the client.

The backend has no persistent process and no store — ADR 0006 chose that
deliberately — yet the contact flow now holds a multi-turn conversation. The
state therefore travels with the client inside an HMAC-signed envelope, using
the same signing primitives as the access token so there is one crypto path in
the codebase rather than two.

What the envelope carries is as important as the signature:

- **Facts only.** No transcript, because the generation stage is forbidden from
  seeing visitor prose (ADR 0007), and no email, because the verified address
  lives in the access token. Model requests are built from these facts, so
  anything in here can reach the model.
- **The turn counter, inside the signature.** A client able to reset it could
  loop the conversation indefinitely at our expense.

Accepted trade-offs, identical to the ones ADR 0006 already took: a conversation
cannot be revoked before its envelope expires, and there is no per-address rate
limit without a store.
"""

from __future__ import annotations

import base64
import hmac
import json
import time
from typing import Literal

from pydantic import BaseModel

from app.services.tokens import InvalidToken, _b64decode, _b64encode, _sign

ENVELOPE_PURPOSE = "contact-conversation"

# Long enough to think between answers, short enough that an abandoned envelope
# stops being usable within the same working session.
ENVELOPE_TTL_SECONDS = 1800

# Five facts need a handful of turns; more than this is a loop, not a
# conversation. Raised from 12 when the script grew the four grouped questions
# the canon needs (COD-65): the ceiling exists to bound cost, so it moves with
# the script deliberately, never as a side effect.
MAX_TURNS = 16

# One answer, not a pasted document. Also bounds what reaches the model.
MAX_MESSAGE_CHARS = 1000

# Envelopes ride in a request; facts are short, so anything near this is abuse.
MAX_ENVELOPE_BYTES = 4096

# An explicit "we have no website" / "no dedicated team". Held, not missing:
# silence and refusal mean different things, and only one may end the flow.
DECLINED = "__declined__"

# The four facts the envelope tracks. The fifth — the verified email — is the
# access token, on purpose.
#: In ask order, and the order is the point: the conversation opens on what the
#: visitor is building, so that is the first gap. Asking the name first made the
#: opening move a form field — one word, leading nowhere — and left the model
#: asking for it again on the very next turn.
REQUIRED_FACTS = ("company", "contact_name", "website", "team")

#: The ground the report is about, asked once the required facts are held.
#:
#: The emailed report assesses ten points, and the four required facts feed none
#: of them: seven were unreachable by construction and the rest arrived only by
#: chance (COD-65). These four questions are grouped rather than atomised — one
#: open question about how code reaches production yields more than three closed
#: ones, and eight separate fields would be the form this design refuses to be.
#:
#: Optional on purpose. They are never in `missing_facts` and never gate
#: `is_complete`: a visitor who will not describe their pipeline still finishes
#: and still gets their report.
OPTIONAL_FACTS = ("delivery", "context_home", "ai_practice", "governance")


class EnvelopeTooLarge(InvalidToken):
    """Envelope exceeds the size cap.

    A subclass so the endpoint can answer 413 while every failure in this module
    stays a kind of InvalidToken — nothing escapes as a bare ValueError.
    """


class ConversationFacts(BaseModel):
    """What the bot has established. Deliberately has no email and no transcript."""

    contact_name: str | None = None
    company: str | None = None
    website: str | None = None
    team: str | None = None

    #: The optional ground — see `OPTIONAL_FACTS`. Free text, like the rest: the
    #: visitor describes their practice, the report decides what it evidences.
    #: How code reaches production — review, tests, deploy, rollback.
    delivery: str | None = None
    #: Where the project's context lives — requirements, decisions, task tracker.
    context_home: str | None = None
    #: How the team uses AI day to day, and whether it has been trained for it.
    ai_practice: str | None = None
    #: Rules over data, secrets and third-party dependencies.
    governance: str | None = None


class ConversationState(BaseModel):
    """An opened envelope: the facts held, turns spent, and whether it is blocked."""

    facts: ConversationFacts
    turns: int
    #: Set when a prompt-injection attempt ended the conversation. Inside the
    #: signature, so a client cannot clear it — but see `seal_envelope`: this
    #: blocks a conversation, never a person.
    blocked: bool = False


def _clean(value: str | None) -> str | None:
    """Trimmed value, or None when there is nothing there."""
    if value is None:
        return None

    stripped = value.strip()

    return stripped or None


def seal_envelope(
    facts: ConversationFacts,
    *,
    turns: int,
    secret: str,
    at: float | None = None,
    blocked: bool = False,
) -> str:
    """Sign the conversation state. Format matches the access token: payload.signature.

    `blocked` goes inside the signature for the same reason the turn counter does:
    a flag the client can edit is not a control. Note the bound of what that buys
    — this ends *this conversation*, and a visitor who drops the envelope starts a
    clean one. There is no store to remember a person by (ADR 0006), so per-visitor
    blocking is not available at any price short of a different architecture.
    """
    issued_at = time.time() if at is None else at
    payload = {
        "facts": facts.model_dump(exclude_none=True),
        "turns": int(turns),
        "blocked": bool(blocked),
        "exp": int(issued_at + ENVELOPE_TTL_SECONDS),
        "purpose": ENVELOPE_PURPOSE,
    }
    raw = json.dumps(payload, separators=(",", ":"), sort_keys=True).encode("utf-8")

    envelope = f"{_b64encode(raw)}.{_b64encode(_sign(raw, secret))}"

    # Checked before returning: an envelope we cannot carry is a bug on our side,
    # not something to discover on the next request.
    if len(envelope.encode("utf-8")) > MAX_ENVELOPE_BYTES:
        raise EnvelopeTooLarge("conversation state exceeds the envelope size cap")

    return envelope


def open_envelope(
    envelope: str,
    *,
    secret: str,
    at: float | None = None,
) -> ConversationState:
    """Return the state an envelope carries, or raise InvalidToken. Nothing else."""
    # Size first: a client can post arbitrary bytes, and parsing them is work we
    # have not agreed to do.
    if len(envelope.encode("utf-8")) > MAX_ENVELOPE_BYTES:
        raise EnvelopeTooLarge("envelope exceeds the size cap")

    try:
        encoded_payload, encoded_signature = envelope.split(".")
        raw = _b64decode(encoded_payload)
        signature = _b64decode(encoded_signature)
    except (ValueError, TypeError, base64.binascii.Error) as error:
        raise InvalidToken("malformed envelope") from error

    if not hmac.compare_digest(_sign(raw, secret), signature):
        raise InvalidToken("bad envelope signature")

    try:
        payload = json.loads(raw)
        facts = ConversationFacts.model_validate(payload["facts"])
        turns = int(payload["turns"])
        # Defaulted, not required: envelopes sealed before this field existed are
        # still in flight when the backend ships, and they are not blocked.
        blocked = bool(payload.get("blocked", False))
        expires_at = int(payload["exp"])
        purpose = str(payload["purpose"])
    except (ValueError, KeyError, TypeError) as error:
        raise InvalidToken("malformed envelope payload") from error

    # Same secret signs the access token: without this check a report token
    # would open as a conversation.
    if purpose != ENVELOPE_PURPOSE:
        raise InvalidToken("wrong purpose")

    now = time.time() if at is None else at
    if expires_at < now:
        raise InvalidToken("expired envelope")

    return ConversationState(facts=facts, turns=turns, blocked=blocked)


def merge_facts(held: ConversationFacts, delta: ConversationFacts) -> ConversationFacts:
    """Fill empty slots from `delta`; never overwrite something already held.

    The extractor re-reads the conversation each turn, so an established fact
    must not be rewritten by a later, worse reading of the same exchange.
    """
    merged: dict[str, str | None] = {}

    for field in ConversationFacts.model_fields:
        current = _clean(getattr(held, field))
        merged[field] = current if current is not None else _clean(getattr(delta, field))

    return ConversationFacts(**merged)


def missing_facts(facts: ConversationFacts) -> list[str]:
    """Facts still unheld, in ask order — what the next question should target.

    Required facts only. The optional ground is deliberately absent: this list
    is what the client gates the report request on, so a fact nobody has to
    answer must never appear in it.
    """
    return [field for field in REQUIRED_FACTS if _clean(getattr(facts, field)) is None]


def unanswered_ground(facts: ConversationFacts) -> list[str]:
    """The optional ground still unheld, in ask order. Never blocks anything."""
    return [field for field in OPTIONAL_FACTS if _clean(getattr(facts, field)) is None]


def is_complete(facts: ConversationFacts, *, email_verified: bool) -> bool:
    """True when all five facts are held: the four here plus the verified address.

    An explicit refusal counts as held; silence does not.
    """
    return email_verified and not missing_facts(facts)


NextStep = Literal["message", "email", "code", "closing", "blocked"]


def derive_next_step(
    facts: ConversationFacts,
    *,
    email_verified: bool,
    turns: int,
    blocked: bool,
) -> NextStep:
    """What the visitor should be asked for next. The one authority on the script.

    This exists because the order used to be split three ways — the server owned
    `missing`, the model owned which fact to ask about, and a Vue computed owned
    which field appeared. The three disagreed, and the symptom was that the email
    address was requested *last*: the component only switched to it once nothing
    else was outstanding. Now the order is decided in one place, and the client
    renders what it is told.

    Derived on every turn rather than sealed into the envelope: a step sealed
    before the access token existed would be stale the moment the address was
    verified, which is precisely the trap `complete` already fell into.
    """
    if blocked:
        return "blocked"

    # Second, never last. The opening turn belongs to the visitor's own account of
    # their business — asking for an address before they have said anything is the
    # questionnaire behaviour this replaces — but from the next turn on, the
    # address is what the whole conversation is for: without it there is nobody to
    # send the report to.
    if not email_verified:
        return "message" if turns == 0 else "email"

    if missing_facts(facts):
        return "message"

    # The optional ground is worth a turn only while there are turns to spend.
    # With the budget gone, an unanswered question is not a reason to keep the
    # visitor talking: the conversation closes with what it has.
    if unanswered_ground(facts) and not turns_exhausted(turns):
        return "message"

    return "closing"


def turns_exhausted(turns: int) -> bool:
    """True when the budget is spent. Not an error: the bot closes with what it has."""
    return turns >= MAX_TURNS


def message_within_budget(message: str) -> bool:
    """True when a visitor message fits the per-message cap."""
    return len(message) <= MAX_MESSAGE_CHARS
