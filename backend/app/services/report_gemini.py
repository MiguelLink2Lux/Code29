"""Report generation with Gemini over the plain REST API.

Not Genkit: `genkit-google-genai` drags 137MB of `google/` and `grpc/` into the
bundle, which does not fit Vercel's ~250MB Python function ceiling (measured, see
ADR 0004). `httpx` is already a dependency and `ReportGenerator` is a one-method
port, so this is a drop-in — and swapping to Genkit later means replacing this
class, nothing else.

Two rules shape everything here:

1. **The model's output is untrusted.** It is validated against the same models
   the template generator produces, and an invented axis or a service we do not
   sell is a hard failure. Nothing falls back to the template silently: a lead
   must never receive a generated report believing a model wrote it.
2. **The model sees facts, never instructions from the visitor.** It receives
   `ReportFacts`, which has no email and no free-text prompt field. That is what
   bounds prompt injection by construction rather than by filtering.
"""

from __future__ import annotations

import json
import re

import httpx
from pydantic import ValidationError

from app.services.report import (
    ContactReport,
    DiagnosisAxis,
    ReportFacts,
    ServiceOffering,
)

GEMINI_MODEL = "gemini-2.5-flash"
GEMINI_ENDPOINT = (
    f"https://generativelanguage.googleapis.com/v1beta/models/{GEMINI_MODEL}:generateContent"
)
REQUEST_TIMEOUT_SECONDS = 30.0
GENERATOR_NAME = f"gemini:{GEMINI_MODEL}"

# Models wrap JSON in fences even when asked not to.
_FENCE = re.compile(r"^\s*```(?:json)?\s*|\s*```\s*$", re.IGNORECASE)


class ModelUnavailable(Exception):
    """The model could not be reached or refused the request. Never quotes the key."""


class ModelResponseInvalid(Exception):
    """The model answered with something that is not a usable report."""


def _system_instruction(locale: str) -> str:
    language = "Spanish" if locale == "es" else "English"

    return (
        "You are a CTO-as-a-Service consultant writing a short workflow diagnosis "
        f"for a prospective client. Write in {language}. "
        "You will receive MEASURED FACTS as JSON: the practices the company reports "
        "using, and signals measured from their home page. "
        "Rules you must follow:\n"
        "- Use only the facts given. Never invent a measurement, a tool or a number.\n"
        "- If a fact is absent, say the practice was not reported; do not assume it is missing.\n"
        f"- Diagnose these axes only: {', '.join(a.value for a in DiagnosisAxis)}.\n"
        "- Every recommendation must map to one of these services: "
        f"{', '.join(s.value for s in ServiceOffering)}.\n"
        "- priority must be one of: high, medium, low.\n"
        "- Be concrete and brief. No sales language, no flattery.\n"
        "Answer with a single JSON object with exactly these keys: "
        "title, summary, sections[axis, heading, diagnosis, evidence[]], "
        "recommendations[axis, action, rationale, service, priority]."
    )


class GeminiReportGenerator:
    """Generates the report with Gemini and validates whatever comes back."""

    def __init__(self, *, api_key: str, transport: httpx.AsyncBaseTransport | None = None) -> None:
        self._api_key = api_key
        self._transport = transport

    async def generate(self, facts: ReportFacts) -> ContactReport:
        payload = {
            "systemInstruction": {"parts": [{"text": _system_instruction(facts.locale)}]},
            "contents": [
                {
                    "role": "user",
                    "parts": [
                        {
                            "text": "MEASURED FACTS:\n"
                            + facts.model_dump_json(indent=2, exclude_none=True)
                        }
                    ],
                }
            ],
            "generationConfig": {
                # Zero temperature: two identical fact sets should not produce
                # two different diagnoses for the same company.
                "temperature": 0,
                "responseMimeType": "application/json",
            },
        }

        try:
            async with httpx.AsyncClient(
                transport=self._transport, timeout=REQUEST_TIMEOUT_SECONDS
            ) as client:
                response = await client.post(
                    GEMINI_ENDPOINT,
                    json=payload,
                    # Header, not query string: URLs reach proxy logs and traces.
                    headers={"x-goog-api-key": self._api_key},
                )
        except httpx.HTTPError as error:
            raise ModelUnavailable(f"model transport failed ({type(error).__name__})") from error

        if response.is_error:
            raise ModelUnavailable(f"model refused the request with {response.status_code}")

        return self._parse(response)

    def _parse(self, response: httpx.Response) -> ContactReport:
        try:
            body = response.json()
            text = body["candidates"][0]["content"]["parts"][0]["text"]
        except (ValueError, KeyError, IndexError, TypeError) as error:
            raise ModelResponseInvalid("model response had no usable candidate") from error

        try:
            document = json.loads(_FENCE.sub("", text))
        except ValueError as error:
            raise ModelResponseInvalid("model did not answer with JSON") from error

        try:
            # Validation is the trust boundary: an unknown axis or an invented
            # service offering fails here rather than reaching a lead's inbox.
            return ContactReport.model_validate({**document, "generator": GENERATOR_NAME})
        except ValidationError as error:
            raise ModelResponseInvalid(f"model report failed validation: {error.error_count()} "
                                       "problem(s)") from error
