"""The Gemini generator: a real model writing the report, over plain REST.

No Genkit. The plugin that speaks to Gemini drags 137MB of `google/` and `grpc/`
into the bundle, which does not fit Vercel's Python function ceiling; httpx is
already a dependency and the port is one method, so this is a drop-in.

The model is treated as **untrusted output**: everything it returns is validated
against the same models the stub produces, and anything malformed is a typed
failure. A silent fallback to the template would email a generated report as if
a model had written it.
"""

import json

import httpx
import pytest

from app.services.report import (
    ContactReport,
    DiagnosisAxis,
    ReportFacts,
    ServiceOffering,
    SiteSignals,
    UnusableReportGenerator,
    WorkflowAnswers,
    build_report_generator,
)
from app.services.report_gemini import (
    GEMINI_MODEL,
    GeminiReportGenerator,
    ModelResponseInvalid,
    ModelUnavailable,
)

API_KEY = "test-gemini-key"

FACTS = ReportFacts(
    contact_name="Ada Lovelace",
    company="Analytical Engines",
    locale="es",
    workflow=WorkflowAnswers(practices=["ci_pipeline", "automated_tests"]),
    site=SiteSignals(available=True, https=True, title="Analytical Engines"),
)


def valid_model_payload() -> dict:
    """The shape the prompt asks the model for."""
    return {
        "title": "Diagnóstico de flujo de trabajo",
        "summary": "Tenéis integración continua pero la IA no participa del ciclo.",
        "sections": [
            {
                "axis": DiagnosisAxis.AI_DEVELOPMENT.value,
                "heading": "IA en el desarrollo",
                "diagnosis": "No hay asistencia de IA en el bucle diario.",
                "evidence": ["No se reporta programación asistida por IA"],
            }
        ],
        "recommendations": [
            {
                "axis": DiagnosisAxis.AI_DEVELOPMENT.value,
                "action": "Implantar un flujo AI-First en el equipo",
                "rationale": "Ya tienen CI, el siguiente salto es el bucle diario.",
                "service": ServiceOffering.AI_ANALYSIS.value,
                "priority": "high",
            }
        ],
    }


def gemini_response(payload: dict) -> dict:
    """Wraps a payload the way the Gemini REST API wraps generated text."""
    return {"candidates": [{"content": {"parts": [{"text": json.dumps(payload)}]}}]}


def transport_returning(body: dict, status_code: int = 200) -> httpx.MockTransport:
    return httpx.MockTransport(lambda _request: httpx.Response(status_code, json=body))


def capturing_transport(body: dict) -> tuple[httpx.MockTransport, list[httpx.Request]]:
    seen: list[httpx.Request] = []

    def handler(request: httpx.Request) -> httpx.Response:
        seen.append(request)
        return httpx.Response(200, json=body)

    return httpx.MockTransport(handler), seen


@pytest.mark.anyio
class TestRequest:
    async def test_calls_the_configured_model_with_the_key(self) -> None:
        transport, seen = capturing_transport(gemini_response(valid_model_payload()))
        generator = GeminiReportGenerator(api_key=API_KEY, transport=transport)

        await generator.generate(FACTS)

        assert GEMINI_MODEL in str(seen[0].url)
        # The key travels as a header, never in the query string: URLs end up in
        # proxy logs and error reports.
        assert seen[0].headers["x-goog-api-key"] == API_KEY
        assert "key=" not in str(seen[0].url)

    async def test_sends_the_facts_and_asks_for_json(self) -> None:
        transport, seen = capturing_transport(gemini_response(valid_model_payload()))
        generator = GeminiReportGenerator(api_key=API_KEY, transport=transport)

        await generator.generate(FACTS)

        body = json.loads(seen[0].content)
        prompt = json.dumps(body)
        assert "Analytical Engines" in prompt
        assert "ci_pipeline" in prompt
        assert body["generationConfig"]["responseMimeType"] == "application/json"

    async def test_pins_temperature_to_zero_for_repeatable_reports(self) -> None:
        transport, seen = capturing_transport(gemini_response(valid_model_payload()))
        generator = GeminiReportGenerator(api_key=API_KEY, transport=transport)

        await generator.generate(FACTS)

        assert json.loads(seen[0].content)["generationConfig"]["temperature"] == 0

    async def test_never_sends_an_email_address(self) -> None:
        # ReportFacts has no email field; this guards the prompt builder too.
        transport, seen = capturing_transport(gemini_response(valid_model_payload()))
        generator = GeminiReportGenerator(api_key=API_KEY, transport=transport)

        await generator.generate(FACTS)

        assert "@" not in seen[0].content.decode()


@pytest.mark.anyio
class TestResponse:
    async def test_returns_a_validated_report(self) -> None:
        generator = GeminiReportGenerator(
            api_key=API_KEY, transport=transport_returning(gemini_response(valid_model_payload()))
        )

        report = await generator.generate(FACTS)

        assert isinstance(report, ContactReport)
        assert report.sections[0].axis is DiagnosisAxis.AI_DEVELOPMENT
        assert report.recommendations[0].service is ServiceOffering.AI_ANALYSIS

    async def test_stamps_its_own_generator_name(self) -> None:
        # The delivered email must say what wrote it: a template and a model are
        # not interchangeable to whoever reads the report.
        generator = GeminiReportGenerator(
            api_key=API_KEY, transport=transport_returning(gemini_response(valid_model_payload()))
        )

        report = await generator.generate(FACTS)

        assert "gemini" in report.generator.lower()

    async def test_tolerates_a_fenced_json_block(self) -> None:
        # Models wrap JSON in ```json fences even when told not to.
        fenced = {
            "candidates": [
                {
                    "content": {
                        "parts": [
                            {"text": f"```json\n{json.dumps(valid_model_payload())}\n```"}
                        ]
                    }
                }
            ]
        }
        generator = GeminiReportGenerator(api_key=API_KEY, transport=transport_returning(fenced))

        assert isinstance(await generator.generate(FACTS), ContactReport)


@pytest.mark.anyio
class TestFailures:
    async def test_rejects_prose_instead_of_json(self) -> None:
        body = {"candidates": [{"content": {"parts": [{"text": "Sure! Here is your report."}]}}]}
        generator = GeminiReportGenerator(api_key=API_KEY, transport=transport_returning(body))

        with pytest.raises(ModelResponseInvalid):
            await generator.generate(FACTS)

    async def test_rejects_an_unknown_axis(self) -> None:
        payload = valid_model_payload()
        payload["sections"][0]["axis"] = "vibes"
        generator = GeminiReportGenerator(
            api_key=API_KEY, transport=transport_returning(gemini_response(payload))
        )

        with pytest.raises(ModelResponseInvalid):
            await generator.generate(FACTS)

    async def test_rejects_a_service_we_do_not_sell(self) -> None:
        # An invented offering would send a lead to a service that does not exist.
        payload = valid_model_payload()
        payload["recommendations"][0]["service"] = "blockchain-consulting"
        generator = GeminiReportGenerator(
            api_key=API_KEY, transport=transport_returning(gemini_response(payload))
        )

        with pytest.raises(ModelResponseInvalid):
            await generator.generate(FACTS)

    async def test_rejects_an_empty_candidate_list(self) -> None:
        generator = GeminiReportGenerator(
            api_key=API_KEY, transport=transport_returning({"candidates": []})
        )

        with pytest.raises(ModelResponseInvalid):
            await generator.generate(FACTS)

    async def test_raises_on_a_rate_limit(self) -> None:
        generator = GeminiReportGenerator(
            api_key=API_KEY, transport=transport_returning({"error": "quota"}, status_code=429)
        )

        with pytest.raises(ModelUnavailable):
            await generator.generate(FACTS)

    async def test_raises_when_the_api_is_unreachable(self) -> None:
        def explode(_request: httpx.Request) -> httpx.Response:
            raise httpx.ConnectTimeout("timed out")

        generator = GeminiReportGenerator(
            api_key=API_KEY, transport=httpx.MockTransport(explode)
        )

        with pytest.raises(ModelUnavailable):
            await generator.generate(FACTS)

    async def test_never_puts_the_api_key_in_an_exception(self) -> None:
        generator = GeminiReportGenerator(
            api_key="super-secret-key", transport=transport_returning({}, status_code=500)
        )

        with pytest.raises(ModelUnavailable) as error:
            await generator.generate(FACTS)

        assert "super-secret-key" not in str(error.value)


class TestFactory:
    def test_gemini_requires_a_key(self) -> None:
        with pytest.raises(UnusableReportGenerator, match="GEMINI_API_KEY"):
            build_report_generator("gemini", model_api_key="")

    def test_gemini_is_selectable_once_configured(self) -> None:
        generator = build_report_generator("gemini", model_api_key=API_KEY)

        assert isinstance(generator, GeminiReportGenerator)

    def test_stub_is_still_the_default(self) -> None:
        assert type(build_report_generator("")).__name__ == "TemplateReportGenerator"

    def test_genkit_still_refuses_rather_than_pretending(self) -> None:
        with pytest.raises(UnusableReportGenerator):
            build_report_generator("genkit", model_api_key=API_KEY)
