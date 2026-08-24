"""Per-turn extraction: the guarantee that replaces the fixed questionnaire.

The old flow guaranteed data quality by structure — eleven steps with closed
options. A conversation cannot do that, so the guarantee moves here: whatever the
visitor writes, only typed, validated facts become facts. Nothing untyped is
kept, and the server decides when the conversation is complete.

Two rules are enforced before any model call:

- the email is stripped from the message (it lives in the access token, and
  everything sent to the model is a GDPR question);
- the message length budget is checked, so a caller cannot make us pay for an
  arbitrarily long prompt.
"""

import pytest

from app.services.conversation import ConversationFacts
from app.services.extraction import (
    ExtractionResult,
    GeminiFactExtractor,
    StubFactExtractor,
    redact_email,
)


class TestRedactEmail:
    def test_finds_and_removes_an_email(self) -> None:
        clean, email = redact_email("hola, soy ada@example.com y trabajo en AE")

        assert email == "ada@example.com"
        assert "ada@example.com" not in clean

    def test_leaves_a_marker_so_the_model_knows_one_was_given(self) -> None:
        # Removing it silently would make the model ask for the email again.
        clean, _ = redact_email("mi correo es ada@example.com")

        assert "[email]" in clean

    def test_normalises_the_address(self) -> None:
        _, email = redact_email("  ADA@Example.COM  ")

        assert email == "ada@example.com"

    def test_returns_none_when_there_is_no_email(self) -> None:
        clean, email = redact_email("trabajamos con Next.js")

        assert email is None
        assert clean == "trabajamos con Next.js"

    def test_removes_every_address_when_several_are_present(self) -> None:
        clean, email = redact_email("ada@example.com o bien ada.lovelace@corp.example")

        # The first one wins; both must disappear from what the model sees.
        assert email == "ada@example.com"
        assert "@example.com" not in clean
        assert "corp.example" not in clean

    @pytest.mark.parametrize("text", ["a@b", "@example.com", "ada@", "ada @ example.com"])
    def test_ignores_things_that_only_look_like_an_email(self, text: str) -> None:
        _, email = redact_email(text)

        assert email is None


@pytest.mark.anyio
class TestStubExtractor:
    """The deterministic extractor: what runs with no key and in every test."""

    async def test_extracts_a_website_from_the_message(self) -> None:
        result = await StubFactExtractor().extract(
            "nuestra web es analyticalengines.com", ConversationFacts()
        )

        assert result.delta.website == "analyticalengines.com"

    async def test_asks_for_what_is_still_missing(self) -> None:
        result = await StubFactExtractor().extract("hola", ConversationFacts())

        assert result.reply.strip()

    async def test_never_invents_a_fact_that_was_not_said(self) -> None:
        result = await StubFactExtractor().extract("buenas", ConversationFacts())

        assert result.delta.contact_name is None
        assert result.delta.company is None
        assert result.delta.website is None
        assert result.delta.team is None

    async def test_is_deterministic(self) -> None:
        first = await StubFactExtractor().extract("somos 4 en el equipo", ConversationFacts())
        second = await StubFactExtractor().extract("somos 4 en el equipo", ConversationFacts())

        assert first == second


class _FakeTransportResponse:
    def __init__(self, payload: dict, status_code: int = 200) -> None:
        self._payload = payload
        self.status_code = status_code
        self.is_error = status_code >= 400

    def json(self) -> dict:
        return self._payload


@pytest.mark.anyio
class TestGeminiExtractor:
    """The model extractor: it sees the visitor's text, and returns only types."""

    @staticmethod
    def _model_reply(delta: dict, reply: str = "¿Cuál es vuestra web?") -> dict:
        import json

        return {
            "candidates": [
                {"content": {"parts": [{"text": json.dumps({"facts": delta, "reply": reply})}]}}
            ]
        }

    async def test_returns_typed_facts_from_the_model(self) -> None:
        import httpx

        transport = httpx.MockTransport(
            lambda _r: httpx.Response(
                200, json=self._model_reply({"company": "Analytical Engines"})
            )
        )
        extractor = GeminiFactExtractor(api_key="k", transport=transport)

        result = await extractor.extract("trabajo en Analytical Engines", ConversationFacts())

        assert result.delta.company == "Analytical Engines"

    async def test_the_email_never_reaches_the_model(self) -> None:
        import httpx

        seen: list[httpx.Request] = []

        def handler(request: httpx.Request) -> httpx.Response:
            seen.append(request)
            return httpx.Response(200, json=self._model_reply({}))

        extractor = GeminiFactExtractor(api_key="k", transport=httpx.MockTransport(handler))

        await extractor.extract("soy ada@example.com", ConversationFacts())

        body = seen[0].content.decode()
        assert "ada@example.com" not in body

    async def test_an_unparseable_answer_is_refused_rather_than_guessed(self) -> None:
        import httpx

        from app.services.report_gemini import ModelResponseInvalid

        transport = httpx.MockTransport(
            lambda _r: httpx.Response(
                200, json={"candidates": [{"content": {"parts": [{"text": "claro que sí"}]}}]}
            )
        )
        extractor = GeminiFactExtractor(api_key="k", transport=transport)

        with pytest.raises(ModelResponseInvalid):
            await extractor.extract("hola", ConversationFacts())

    async def test_a_fact_of_the_wrong_shape_is_dropped_not_coerced(self) -> None:
        import httpx

        transport = httpx.MockTransport(
            lambda _r: httpx.Response(200, json=self._model_reply({"company": {"nested": "no"}}))
        )
        extractor = GeminiFactExtractor(api_key="k", transport=transport)

        from app.services.report_gemini import ModelResponseInvalid

        with pytest.raises(ModelResponseInvalid):
            await extractor.extract("hola", ConversationFacts())

    async def test_an_over_long_message_is_refused_before_the_call(self) -> None:
        import httpx

        called = False

        def handler(request: httpx.Request) -> httpx.Response:
            nonlocal called
            called = True
            return httpx.Response(200, json=self._model_reply({}))

        extractor = GeminiFactExtractor(api_key="k", transport=httpx.MockTransport(handler))

        with pytest.raises(ValueError, match="budget|too long"):
            await extractor.extract("x" * 5000, ConversationFacts())

        assert called is False, "we must not pay for a prompt we already know is over budget"


def test_extraction_result_carries_both_the_delta_and_the_reply() -> None:
    result = ExtractionResult(delta=ConversationFacts(company="AE"), reply="¿Y vuestra web?")

    assert result.delta.company == "AE"
    assert result.reply
