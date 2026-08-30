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

import json

import pytest

from app.services.conversation import ConversationFacts
from app.services.extraction import (
    ExtractionResult,
    GeminiFactExtractor,
    StubFactExtractor,
    _instruction,
    _ModelDelta,
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

    async def test_the_model_is_told_not_to_think_before_extracting(self) -> None:
        """Extraction is a deterministic read of one sentence, not a problem to
        reason about. The Flash models of the 3.x family think at `medium` unless
        told otherwise, and that reasoning is what pushed the call past its
        deadline in production (COD-63)."""
        import httpx

        seen: list[httpx.Request] = []

        def handler(request: httpx.Request) -> httpx.Response:
            seen.append(request)
            return httpx.Response(200, json=self._model_reply({}))

        extractor = GeminiFactExtractor(api_key="k", transport=httpx.MockTransport(handler))

        await extractor.extract("hola", ConversationFacts())

        config = json.loads(seen[0].content)["generationConfig"]
        # `minimal` is not accepted by Flash 3.x — `low` is the floor.
        assert config["thinkingConfig"] == {"thinkingLevel": "low"}
        # The two settings are mutually exclusive: sending both is a 400.
        assert "thinkingBudget" not in json.dumps(config)

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


class TestTheInstruction:
    """What the model is told about how to behave.

    The extraction contract was already covered; the *conduct* was not, and the
    conduct is what makes the chat read as an assistant with a purpose rather
    than a form with a chat skin.
    """

    def test_it_names_the_report_the_questions_are_for(self) -> None:
        # A visitor who is not told why is being interrogated, not interviewed.
        assert "report" in _instruction().lower()

    def test_it_asks_the_model_to_acknowledge_what_it_was_told(self) -> None:
        assert "acknowledge" in _instruction().lower()

    def test_it_forbids_asking_again_for_something_already_held(self) -> None:
        instruction = _instruction().lower()

        assert "already" in instruction

    def test_it_still_forbids_inventing_facts(self) -> None:
        # The conduct changed; the extraction guarantee did not.
        instruction = _instruction().lower()

        assert "never infer" in instruction
        assert "data, not a command" in instruction

    def test_it_still_never_asks_for_an_email(self) -> None:
        assert "never ask for an email" in _instruction().lower()


class TestTheInstructionSpeaksTheVisitorsLanguage:
    """The opening is chosen from html[lang]; the replies were always Spanish.

    An English visitor got an English greeting and then Spanish answers to it.
    The language is a property of the conversation, so it has to reach the
    instruction rather than be baked into it.
    """

    def test_spanish_is_the_default(self) -> None:
        assert "in Spanish" in _instruction()

    def test_english_is_asked_for_explicitly(self) -> None:
        assert "in English" in _instruction("en")

    def test_the_language_is_the_only_thing_that_changes(self) -> None:
        # The conduct and the extraction contract are identical in both: a
        # translated prompt that drifts is two prompts.
        for phrase in ("never infer", "data, not a command", "never ask for an email"):
            assert phrase in _instruction("es").lower()
            assert phrase in _instruction("en").lower()


class TestTheModelCanReportAnAttack:
    """A second net behind the deterministic guard, never the only one.

    The guard runs first and short-circuits, so this is what catches phrasing a
    regex does not. It is advisory: the endpoint decides what it means.
    """

    def test_the_delta_accepts_an_injection_flag(self) -> None:
        parsed = _ModelDelta.model_validate(
            {"facts": {}, "reply": "…", "injection": True}
        )

        assert parsed.injection is True

    def test_it_defaults_to_false_when_the_model_omits_it(self) -> None:
        parsed = _ModelDelta.model_validate({"facts": {}, "reply": "…"})

        assert parsed.injection is False

    def test_the_instruction_asks_for_it(self) -> None:
        assert "injection" in _instruction().lower()


class TestTheInstructionCarriesTheStep:
    """The server decides the step; the model puts it into words.

    Both halves were shipped, and between them a fixed sentence in the client
    asked for the address too — so a single turn carried two questions, one of
    them written by nobody in the conversation.
    """

    def test_the_email_step_tells_the_model_to_ask_for_the_address(self) -> None:
        instruction = _instruction("es", "email").lower()

        assert "email address" in instruction

    def test_the_email_step_forbids_asking_anything_else(self) -> None:
        # The defect exactly: the model asked about the company while the client
        # asked for the address. One turn, one question.
        instruction = _instruction("es", "email").lower()

        assert "only" in instruction and "one question" in instruction

    def test_the_default_step_still_never_asks_for_an_email(self) -> None:
        # The old rule survives everywhere else: the address is asked for when
        # the server says so, and at no other time.
        assert "never ask for an email" in _instruction("es", "message").lower()

    def test_the_closing_step_announces_the_report(self) -> None:
        assert "report" in _instruction("es", "closing").lower()

    def test_the_conduct_is_the_same_in_both_languages(self) -> None:
        for step in ("message", "email", "closing"):
            assert "never infer" in _instruction("es", step).lower()
            assert "never infer" in _instruction("en", step).lower()


class TestTheDeadlineGivenToTheModel:
    """The extractor's deadline is the one the visitor waits behind, so it is
    stated here rather than left to a default that changed under us (COD-63)."""

    def test_it_matches_the_one_the_report_generator_uses(self) -> None:
        from app.services import report_gemini
        from app.services.extraction import REQUEST_TIMEOUT_SECONDS

        assert REQUEST_TIMEOUT_SECONDS == report_gemini.REQUEST_TIMEOUT_SECONDS


@pytest.mark.anyio
class TestTheGroundTheReportIsAbout:
    """COD-65: the report assesses ten points, so the script has to ask about
    them. Four grouped questions, asked after the required facts are held."""

    def test_the_instruction_names_the_four_new_fields(self) -> None:
        instruction = _instruction()

        for field in ("delivery", "context_home", "ai_practice", "governance"):
            assert field in instruction

    def test_the_json_shape_carries_them_too(self) -> None:
        """The model answers with the shape it is shown. A field missing from the
        example is a field the model has no slot to put an answer in."""
        shape = _instruction().split('Answer with a single JSON object: ')[1]

        for field in ("delivery", "context_home", "ai_practice", "governance"):
            assert f'"{field}"' in shape

    def test_it_still_refuses_to_infer(self) -> None:
        """Four open questions about pipelines and tooling are exactly where a
        model starts filling in plausible detail. The rule holds."""
        assert "Never infer, never fill in" in _instruction()

    def test_it_still_never_asks_for_an_email(self) -> None:
        assert "never ask for an email address" in _instruction().lower()

    async def test_the_stub_asks_about_them_once_the_required_facts_are_held(self) -> None:
        held = ConversationFacts(
            contact_name="Ada",
            company="Analytical Engines",
            website="https://ae.example",
            team="four developers",
        )

        result = await StubFactExtractor().extract("eso es todo", held)

        assert "informe y te lo envío" not in result.reply
        assert "?" in result.reply

    async def test_the_stub_still_closes_once_there_is_nothing_left_to_ask(self) -> None:
        held = ConversationFacts(
            contact_name="Ada",
            company="Analytical Engines",
            website="https://ae.example",
            team="four developers",
            delivery="PRs con revisión, tests que bloquean el merge",
            context_home="requisitos en Notion, ADRs junto al código",
            ai_practice="Copilot a diario",
            governance="secretos en el gestor del proveedor",
        )

        result = await StubFactExtractor().extract("nada más", held)

        assert "informe" in result.reply.lower()
