"""Conversation state travels signed, because serverless has nowhere to keep it.

The backend has no persistent process and no store — that is ADR 0006's decision,
not an oversight. A multi-turn conversation still needs state, so it rides in an
HMAC-signed envelope the client carries between turns.

Two properties carry the weight, and both are asserted here rather than trusted:

- The envelope holds **facts only**. Never the raw transcript, and never the
  email: the verified address lives in the access token, so a model call built
  from the envelope cannot leak it.
- The **turn counter is inside the signature**. A client that could reset it
  could loop the conversation forever at our expense.
"""

import json
import time

import pytest

from app.services.conversation import (
    DECLINED,
    MAX_ENVELOPE_BYTES,
    MAX_MESSAGE_CHARS,
    MAX_TURNS,
    REQUIRED_FACTS,
    ConversationFacts,
    EnvelopeTooLarge,
    derive_next_step,
    is_complete,
    merge_facts,
    message_within_budget,
    open_envelope,
    seal_envelope,
    turns_exhausted,
)
from app.services.tokens import InvalidToken, _b64encode, issue_access_token

SECRET = "conversation-secret-of-at-least-32-chars!"

FACTS = ConversationFacts(
    contact_name="Ada Lovelace",
    company="Analytical Engines",
    website="https://analyticalengines.example",
    team="4 developers, no dedicated QA",
)


class TestRoundTrip:
    def test_round_trips_facts(self) -> None:
        state = open_envelope(seal_envelope(FACTS, turns=1, secret=SECRET), secret=SECRET)

        assert state.facts == FACTS
        assert state.turns == 1

    def test_round_trips_an_empty_conversation(self) -> None:
        # The first turn seals nothing but the counter.
        state = open_envelope(
            seal_envelope(ConversationFacts(), turns=0, secret=SECRET), secret=SECRET
        )

        assert state.facts == ConversationFacts()
        assert state.turns == 0

    def test_preserves_an_explicit_refusal(self) -> None:
        facts = ConversationFacts(contact_name="Ada", website=DECLINED)

        state = open_envelope(seal_envelope(facts, turns=2, secret=SECRET), secret=SECRET)

        assert state.facts.website == DECLINED


class TestRejection:
    def test_rejects_tampered_payload(self) -> None:
        envelope = seal_envelope(FACTS, turns=1, secret=SECRET)
        payload, signature = envelope.split(".", 1)

        with pytest.raises(InvalidToken):
            open_envelope(f"{payload}x.{signature}", secret=SECRET)

    def test_rejects_another_secret(self) -> None:
        envelope = seal_envelope(FACTS, turns=1, secret="another-secret-thirty-two-chars-ok!!")

        with pytest.raises(InvalidToken):
            open_envelope(envelope, secret=SECRET)

    def test_rejects_expired(self) -> None:
        stale = seal_envelope(FACTS, turns=1, secret=SECRET, at=time.time() - 3600)

        with pytest.raises(InvalidToken):
            open_envelope(stale, secret=SECRET)

    def test_rejects_an_access_token_reused_as_an_envelope(self) -> None:
        # Same signing key, different purpose: a report token must not buy turns.
        token = issue_access_token("ada@example.com", secret=SECRET)

        with pytest.raises(InvalidToken):
            open_envelope(token, secret=SECRET)

    @pytest.mark.parametrize("candidate", ["", "nodot", "a.b.c", "...", "!!!.???"])
    def test_rejects_malformed(self, candidate: str) -> None:
        with pytest.raises(InvalidToken):
            open_envelope(candidate, secret=SECRET)

    def test_rejects_oversized_on_the_way_in(self) -> None:
        # A client can post arbitrary bytes; the cap is checked before any parse.
        with pytest.raises(EnvelopeTooLarge):
            open_envelope("x" * (MAX_ENVELOPE_BYTES + 1), secret=SECRET)

    def test_refuses_to_seal_something_oversized(self) -> None:
        bloated = ConversationFacts(team="x" * (MAX_ENVELOPE_BYTES * 2))

        with pytest.raises(EnvelopeTooLarge):
            seal_envelope(bloated, turns=1, secret=SECRET)

    def test_oversize_is_a_kind_of_invalid_token(self) -> None:
        # The endpoint maps it to 413, but nothing may escape as a bare ValueError.
        assert issubclass(EnvelopeTooLarge, InvalidToken)


class TestTurnCounter:
    def test_turn_counter_cannot_be_reset_by_client(self) -> None:
        envelope = seal_envelope(FACTS, turns=MAX_TURNS - 1, secret=SECRET)
        payload, signature = envelope.split(".", 1)

        # Rewrite the counter and re-encode WITHOUT re-signing: this is exactly
        # what a client trying to buy more turns would do.
        decoded = json.loads(
            __import__("base64").urlsafe_b64decode(payload + "=" * (-len(payload) % 4))
        )
        decoded["turns"] = 0
        forged = f"{_b64encode(json.dumps(decoded).encode())}.{signature}"

        with pytest.raises(InvalidToken):
            open_envelope(forged, secret=SECRET)

    def test_turns_exhausted_at_the_cap(self) -> None:
        assert turns_exhausted(MAX_TURNS) is True
        assert turns_exhausted(MAX_TURNS - 1) is False

    def test_the_cap_is_a_real_budget(self) -> None:
        # A cap so high it never fires is not a budget; one so low it cuts a
        # normal conversation is a defect. Five facts need a handful of turns.
        assert 6 <= MAX_TURNS <= 20


class TestMessageBudget:
    def test_accepts_a_normal_message(self) -> None:
        assert message_within_budget("Somos cuatro devs y no tenemos QA") is True

    def test_rejects_an_oversized_message(self) -> None:
        assert message_within_budget("x" * (MAX_MESSAGE_CHARS + 1)) is False

    def test_the_limit_leaves_room_for_a_real_answer(self) -> None:
        assert 200 <= MAX_MESSAGE_CHARS <= 4000


class TestFactMerge:
    def test_merge_keeps_first_non_empty(self) -> None:
        held = ConversationFacts(contact_name="Ada", company="Analytical Engines")
        delta = ConversationFacts(contact_name="Someone Else", website="https://example.com")

        merged = merge_facts(held, delta)

        # A later turn must not overwrite something already established: the
        # extractor re-reading the transcript would otherwise rewrite history.
        assert merged.contact_name == "Ada"
        assert merged.company == "Analytical Engines"
        assert merged.website == "https://example.com"

    def test_merge_ignores_blank_and_whitespace_deltas(self) -> None:
        held = ConversationFacts(contact_name="Ada")
        merged = merge_facts(held, ConversationFacts(contact_name=None, company="   "))

        assert merged.contact_name == "Ada"
        assert merged.company is None

    def test_merge_does_not_mutate_its_inputs(self) -> None:
        held = ConversationFacts(contact_name="Ada")
        merge_facts(held, ConversationFacts(company="Analytical Engines"))

        assert held.company is None

    def test_a_refusal_can_fill_an_empty_slot(self) -> None:
        merged = merge_facts(ConversationFacts(), ConversationFacts(website=DECLINED))

        assert merged.website == DECLINED

    def test_a_refusal_does_not_overwrite_a_real_answer(self) -> None:
        held = ConversationFacts(website="https://example.com")

        merged = merge_facts(held, ConversationFacts(website=DECLINED))

        assert merged.website == "https://example.com"


class TestCompletion:
    def test_missing_fact_blocks_completion(self) -> None:
        without_team = ConversationFacts(
            contact_name="Ada", company="AE", website="https://example.com"
        )

        assert is_complete(without_team, email_verified=True) is False

    def test_all_five_held_completes(self) -> None:
        assert is_complete(FACTS, email_verified=True) is True

    def test_an_unverified_email_blocks_completion(self) -> None:
        # The fifth fact is the verified address, and it lives in the access
        # token — never in the envelope.
        assert is_complete(FACTS, email_verified=False) is False

    def test_declined_website_counts_as_held(self) -> None:
        declined = ConversationFacts(
            contact_name="Ada", company="AE", website=DECLINED, team="2 devs"
        )

        assert is_complete(declined, email_verified=True) is True

    def test_declined_team_counts_as_held(self) -> None:
        declined = ConversationFacts(
            contact_name="Ada", company="AE", website="https://example.com", team=DECLINED
        )

        assert is_complete(declined, email_verified=True) is True

    def test_a_silent_absence_is_not_a_refusal(self) -> None:
        # Spec: an explicit refusal counts as held, silence does not.
        silent = ConversationFacts(contact_name="Ada", company="AE", website="https://example.com")

        assert is_complete(silent, email_verified=True) is False

    def test_missing_fields_are_reported_for_the_next_question(self) -> None:
        from app.services.conversation import missing_facts

        held = ConversationFacts(contact_name="Ada", company="AE")

        assert set(missing_facts(held)) == {"website", "team"}


class TestNoPii:
    def test_envelope_never_carries_an_email(self) -> None:
        # The model request is built from the envelope, so an address in here
        # would reach the model no matter how careful the caller is.
        envelope = seal_envelope(
            ConversationFacts(
                contact_name="Ada Lovelace",
                company="Analytical Engines",
                website="https://example.com",
                team="4 devs",
            ),
            turns=3,
            secret=SECRET,
        )

        payload = __import__("base64").urlsafe_b64decode(
            envelope.split(".")[0] + "=" * (-len(envelope.split(".")[0]) % 4)
        )

        assert b"@" not in payload

    def test_the_facts_model_has_no_email_field(self) -> None:
        assert "email" not in ConversationFacts.model_fields

    def test_the_facts_model_has_no_transcript_field(self) -> None:
        # Raw visitor text must never be carried: it is what the generation
        # stage is forbidden from seeing.
        for forbidden in ("transcript", "messages", "history"):
            assert forbidden not in ConversationFacts.model_fields


class TestBlocked:
    """A blocked conversation is blocked inside the signature, or not at all.

    Zero tolerance is about the response, and the response is worth nothing if the
    client can undo it. The flag therefore rides where the turn counter rides: a
    client that edits it invalidates the HMAC and loses the whole envelope.

    What this does NOT buy is worth stating, because it will be read as a defect
    otherwise: the block is per **conversation**, not per visitor. Dropping the
    envelope — reloading the tab — starts a clean one. The backend keeps no store
    (ADR 0006), so nothing can remember a person. Signing stops tampering, never
    restarting. That limit is specified behaviour, not an oversight.
    """

    def test_round_trips_blocked(self) -> None:
        state = open_envelope(
            seal_envelope(FACTS, turns=2, secret=SECRET, blocked=True), secret=SECRET
        )

        assert state.blocked is True

    def test_a_conversation_is_open_unless_it_was_blocked(self) -> None:
        state = open_envelope(seal_envelope(FACTS, turns=2, secret=SECRET), secret=SECRET)

        assert state.blocked is False

    def test_an_envelope_sealed_before_this_change_opens_unblocked(self) -> None:
        # Frontend and backend are separate deployments and do not ship at the
        # same instant. An in-flight envelope must degrade, not 500.
        legacy = json.dumps(
            {
                "facts": FACTS.model_dump(exclude_none=True),
                "turns": 2,
                "exp": int(time.time() + 600),
                "purpose": "contact-conversation",
            },
            separators=(",", ":"),
            sort_keys=True,
        ).encode("utf-8")
        from app.services.tokens import _sign

        envelope = f"{_b64encode(legacy)}.{_b64encode(_sign(legacy, SECRET))}"

        assert open_envelope(envelope, secret=SECRET).blocked is False

    def test_flipping_the_flag_invalidates_the_envelope(self) -> None:
        envelope = seal_envelope(FACTS, turns=2, secret=SECRET, blocked=True)
        payload, signature = envelope.split(".")
        raw = __import__("base64").urlsafe_b64decode(payload + "=" * (-len(payload) % 4))
        forged = raw.replace(b'"blocked":true', b'"blocked":fals')

        with pytest.raises(InvalidToken):
            open_envelope(f"{_b64encode(forged)}.{signature}", secret=SECRET)


class TestNextStep:
    """The server owns the script order. Nobody else gets a vote.

    This is the fix for the defect that made the chat ask for the email last: the
    order was split across a server flag, a model prompt and a Vue computed, and
    the three disagreed. One function, one authority, one truth table.
    """

    def test_the_address_is_asked_for_right_after_the_first_answer(self) -> None:
        assert (
            derive_next_step(ConversationFacts(), email_verified=False, turns=1, blocked=False)
            == "email"
        )

    def test_the_opening_turn_asks_about_the_business_not_the_address(self) -> None:
        assert (
            derive_next_step(ConversationFacts(), email_verified=False, turns=0, blocked=False)
            == "message"
        )

    def test_the_address_is_asked_for_even_when_everything_else_is_missing(self) -> None:
        # The whole point: it is second, not last.
        assert (
            derive_next_step(
                ConversationFacts(contact_name="Ada"), email_verified=False, turns=2, blocked=False
            )
            == "email"
        )

    def test_a_verified_visitor_is_never_asked_for_an_address_again(self) -> None:
        for turns in range(1, MAX_TURNS):
            assert derive_next_step(
                ConversationFacts(), email_verified=True, turns=turns, blocked=False
            ) not in ("email", "code")

    def test_a_verified_visitor_with_facts_missing_keeps_talking(self) -> None:
        assert (
            derive_next_step(
                ConversationFacts(contact_name="Ada"), email_verified=True, turns=3, blocked=False
            )
            == "message"
        )

    def test_everything_held_closes_with_an_invitation(self) -> None:
        assert derive_next_step(FACTS, email_verified=True, turns=5, blocked=False) == "closing"

    def test_blocked_beats_everything(self) -> None:
        assert derive_next_step(FACTS, email_verified=True, turns=5, blocked=True) == "blocked"

    def test_the_budget_beats_the_closing_invitation(self) -> None:
        # A closing turn must never become a way to outlive MAX_TURNS.
        assert derive_next_step(FACTS, email_verified=True, turns=MAX_TURNS, blocked=False) == (
            "closing"
        )
        assert turns_exhausted(MAX_TURNS)

    def test_the_budget_covers_a_worst_case_conversation_including_the_closing(self) -> None:
        """The closing turn is new spending. Assert the budget absorbs it.

        Worst realistic case: the visitor volunteers one fact per turn and never
        two at once. That is the opening account of the business, then each of
        the four facts, then the closing invitation. Verification costs no turn
        here — it runs through its own endpoint.

        Asserted rather than re-tuned: MAX_TURNS is a cost ceiling, and moving it
        because a new step was added is how a ceiling stops meaning anything.
        """
        worst_case = 1 + len(REQUIRED_FACTS) + 1

        assert worst_case <= MAX_TURNS
        assert not turns_exhausted(worst_case)
