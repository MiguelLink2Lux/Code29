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
    stated here rather than left to a default that changed under us (COD-63).

    It used to equal the report generator's 30 s. COD-69 split them: a turn is
    interactive and now retries once, so its whole budget must stay under what
    the visitor waited before; the report is neither."""

    def test_the_whole_turn_fits_in_less_than_the_old_worst_case(self) -> None:
        from app.services.extraction import TURN_BUDGET_SECONDS

        assert TURN_BUDGET_SECONDS < 25

    def test_connect_and_read_are_bounded_separately(self) -> None:
        from app.services.extraction import REQUEST_TIMEOUT, TURN_BUDGET_SECONDS

        # A refused connection is known fast; a slow answer is not. One attempt
        # must leave room in the budget for the second.
        assert REQUEST_TIMEOUT.connect is not None
        assert REQUEST_TIMEOUT.read is not None
        assert REQUEST_TIMEOUT.connect < REQUEST_TIMEOUT.read
        assert REQUEST_TIMEOUT.connect + REQUEST_TIMEOUT.read < TURN_BUDGET_SECONDS

    def test_the_report_generator_keeps_its_own_deadline(self) -> None:
        from app.services import report_gemini

        assert report_gemini.REQUEST_TIMEOUT_SECONDS == 30.0


def _model_ok() -> dict:
    return {
        "candidates": [
            {"content": {"parts": [{"text": json.dumps({"facts": {}, "reply": "¿Y tu web?"})}]}}
        ]
    }


def _gemini_error(code: int, status: str) -> dict:
    return {"error": {"code": code, "message": "quota detail", "status": status}}


class _Scripted:
    """A Gemini stand-in that answers from a script, one entry per call. An
    entry is either a response or an exception to raise."""

    def __init__(self, *script: object) -> None:
        import httpx

        self.script = list(script)
        self.calls = 0
        self.transport = httpx.MockTransport(self._handle)

    def _handle(self, request: object) -> object:
        entry = self.script[min(self.calls, len(self.script) - 1)]
        self.calls += 1
        if isinstance(entry, Exception):
            raise entry
        return entry


class _Sleeps:
    def __init__(self) -> None:
        self.waited: list[float] = []

    async def __call__(self, seconds: float) -> None:
        self.waited.append(seconds)


@pytest.mark.anyio
class TestATransientFailureIsRetriedOnce:
    """COD-69: about one turn in four answered 502 in production, on 429 and 503
    refusals that the next call would have survived. One retry, inside a budget
    the visitor can wait through — never more."""

    def _extractor(self, gemini: _Scripted, sleeps: _Sleeps) -> GeminiFactExtractor:
        return GeminiFactExtractor(api_key="k", transport=gemini.transport, sleep=sleeps)

    async def test_the_happy_path_makes_one_call(self) -> None:
        import httpx

        gemini, sleeps = _Scripted(httpx.Response(200, json=_model_ok())), _Sleeps()

        result = await self._extractor(gemini, sleeps).extract("hola", ConversationFacts())

        assert result.reply
        assert gemini.calls == 1
        assert sleeps.waited == []

    async def test_an_overloaded_model_is_asked_again(
        self, caplog: pytest.LogCaptureFixture
    ) -> None:
        import logging

        import httpx

        gemini = _Scripted(
            httpx.Response(503, json=_gemini_error(503, "UNAVAILABLE")),
            httpx.Response(200, json=_model_ok()),
        )
        sleeps = _Sleeps()

        with caplog.at_level(logging.WARNING):
            result = await self._extractor(gemini, sleeps).extract("hola", ConversationFacts())

        assert result.reply
        assert gemini.calls == 2
        logged = "\n".join(record.getMessage() for record in caplog.records)
        assert "503" in logged and "UNAVAILABLE" in logged
        assert "hola" not in logged, "the visitor's words are never logged"

    async def test_a_rate_limit_honours_retry_after_when_it_fits(self) -> None:
        import httpx

        gemini = _Scripted(
            httpx.Response(
                429,
                json=_gemini_error(429, "RESOURCE_EXHAUSTED"),
                headers={"Retry-After": "2"},
            ),
            httpx.Response(200, json=_model_ok()),
        )
        sleeps = _Sleeps()

        await self._extractor(gemini, sleeps).extract("hola", ConversationFacts())

        assert gemini.calls == 2
        assert sleeps.waited == [2.0]

    async def test_a_rate_limit_without_retry_after_waits_a_short_fixed_backoff(self) -> None:
        import httpx

        from app.services.extraction import RETRY_BACKOFF_SECONDS

        gemini = _Scripted(
            httpx.Response(429, json=_gemini_error(429, "RESOURCE_EXHAUSTED")),
            httpx.Response(200, json=_model_ok()),
        )
        sleeps = _Sleeps()

        await self._extractor(gemini, sleeps).extract("hola", ConversationFacts())

        assert gemini.calls == 2
        assert sleeps.waited == [RETRY_BACKOFF_SECONDS]
        assert RETRY_BACKOFF_SECONDS <= 2

    async def test_a_retry_after_beyond_the_budget_fails_fast(self) -> None:
        import httpx

        from app.services.report_gemini import ModelUnavailable

        gemini = _Scripted(
            httpx.Response(
                429,
                json=_gemini_error(429, "RESOURCE_EXHAUSTED"),
                headers={"Retry-After": "60"},
            ),
            httpx.Response(200, json=_model_ok()),
        )
        sleeps = _Sleeps()

        with pytest.raises(ModelUnavailable, match="429"):
            await self._extractor(gemini, sleeps).extract("hola", ConversationFacts())

        assert gemini.calls == 1
        assert sleeps.waited == []

    @pytest.mark.parametrize("code", [500, 504])
    async def test_a_server_fault_is_asked_again(self, code: int) -> None:
        import httpx

        gemini = _Scripted(
            httpx.Response(code, json=_gemini_error(code, "INTERNAL")),
            httpx.Response(200, json=_model_ok()),
        )

        result = await self._extractor(gemini, _Sleeps()).extract("hola", ConversationFacts())

        assert result.reply
        assert gemini.calls == 2

    async def test_a_retry_after_as_a_date_falls_back_to_the_fixed_backoff(self) -> None:
        import httpx

        from app.services.extraction import RETRY_BACKOFF_SECONDS

        gemini = _Scripted(
            httpx.Response(
                429,
                json=_gemini_error(429, "RESOURCE_EXHAUSTED"),
                headers={"Retry-After": "Wed, 21 Oct 2026 07:28:00 GMT"},
            ),
            httpx.Response(200, json=_model_ok()),
        )
        sleeps = _Sleeps()

        await self._extractor(gemini, sleeps).extract("hola", ConversationFacts())

        assert gemini.calls == 2
        assert sleeps.waited == [RETRY_BACKOFF_SECONDS]

    async def test_an_attempt_that_outlasts_the_budget_is_not_retried(
        self, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        import asyncio

        import httpx

        from app.services import extraction
        from app.services.report_gemini import ModelUnavailable

        monkeypatch.setattr(extraction, "TURN_BUDGET_SECONDS", 0.05)
        calls = 0

        async def slow(_request: httpx.Request) -> httpx.Response:
            nonlocal calls
            calls += 1
            await asyncio.sleep(1)
            return httpx.Response(200, json=_model_ok())

        extractor = GeminiFactExtractor(
            api_key="k", transport=httpx.MockTransport(slow), sleep=_Sleeps()
        )

        with pytest.raises(ModelUnavailable, match="exceeded the turn budget"):
            await extractor.extract("hola", ConversationFacts())

        assert calls == 1

    async def test_a_hang_is_cut_and_asked_again(self) -> None:
        import httpx

        gemini = _Scripted(
            httpx.ReadTimeout("read timed out"), httpx.Response(200, json=_model_ok())
        )
        sleeps = _Sleeps()

        result = await self._extractor(gemini, sleeps).extract("hola", ConversationFacts())

        assert result.reply
        assert gemini.calls == 2

    @pytest.mark.parametrize("code,reason", [(503, "UNAVAILABLE"), (429, "RESOURCE_EXHAUSTED")])
    async def test_a_persistent_refusal_fails_after_exactly_two_calls(
        self, code: int, reason: str
    ) -> None:
        import httpx

        from app.services.report_gemini import ModelUnavailable

        gemini = _Scripted(httpx.Response(code, json=_gemini_error(code, reason)))
        sleeps = _Sleeps()

        with pytest.raises(ModelUnavailable) as raised:
            await self._extractor(gemini, sleeps).extract("hola", ConversationFacts())

        assert gemini.calls == 2
        message = str(raised.value)
        assert str(code) in message
        assert reason in message
        assert "quota detail" not in message, "the provider's prose is not echoed"
        assert "hola" not in message

    async def test_a_persistent_hang_fails_after_exactly_two_calls(self) -> None:
        import httpx

        from app.services.report_gemini import ModelUnavailable

        gemini = _Scripted(httpx.ReadTimeout("read timed out"))

        with pytest.raises(ModelUnavailable, match="ReadTimeout"):
            await self._extractor(gemini, _Sleeps()).extract("hola", ConversationFacts())

        assert gemini.calls == 2

    @pytest.mark.parametrize("code", [400, 401, 403, 404])
    async def test_a_refusal_that_will_not_change_is_not_retried(self, code: int) -> None:
        import httpx

        from app.services.report_gemini import ModelUnavailable

        gemini = _Scripted(
            httpx.Response(code, json=_gemini_error(code, "INVALID_ARGUMENT")),
            httpx.Response(200, json=_model_ok()),
        )
        sleeps = _Sleeps()

        with pytest.raises(ModelUnavailable, match=str(code)):
            await self._extractor(gemini, sleeps).extract("hola", ConversationFacts())

        assert gemini.calls == 1
        assert sleeps.waited == []

    async def test_an_error_body_that_is_not_json_still_names_the_status(self) -> None:
        import httpx

        from app.services.report_gemini import ModelUnavailable

        gemini = _Scripted(httpx.Response(503, text="<html>bad gateway</html>"))

        with pytest.raises(ModelUnavailable, match="503"):
            await self._extractor(gemini, _Sleeps()).extract("hola", ConversationFacts())


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
