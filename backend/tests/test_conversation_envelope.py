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
    ConversationFacts,
    EnvelopeTooLarge,
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
