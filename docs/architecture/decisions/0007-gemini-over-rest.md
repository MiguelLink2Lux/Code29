> **Type:** Architecture · ADR — **Status:** Accepted — **Date:** 2026-08-22
> **Part of:** [[Decisions]]

# ADR 0007 — Talk to Gemini over the REST API instead of the Genkit SDK

- **Status:** Accepted
- **Date:** 2026-08-22
- **Deciders:** Miguel Navarro Mantas
- **Partially supersedes:** [[0005-genkit-runtime]]

> **Scope of the supersession.** [[0005-genkit-runtime]] decided two things at once: *that*
> the AI layer lives inside the FastAPI backend, and *how* the backend reaches the model
> (the Genkit Python SDK plus `genkit-google-genai`). The first decision stands unchanged —
> the AI layer is still a module of `backend/`, one process, one deployment, one test suite.
> Only the second changes: the model is now reached with a direct HTTPS call to the Google
> Generative Language REST API. Genkit is not installed.

## Context and Problem Statement

Phase 3 needs the contact flow's workflow report ([[0006-guided-ai-contact-flow]]) written by
a model instead of by the deterministic template. ADR 0005 picked the Genkit Python SDK for
that, verified to the point of *installs and imports* — no real model call had ever been made.

The open risk recorded in [[0004-backend-deploy-provider]] ("the Genkit dependency tree may
exceed Vercel's serverless bundle size limit") then materialized and was measured on the
dependency spike (branch `chore/genkit-deps-adr`):

| Measurement | Value |
|-------------|-------|
| Installed backend with Genkit | **233 MB**, 92 packages |
| `google/` (from `google-genai`, pulled by `genkit-google-genai`) | **98 MB** |
| `grpc/` (transitive, same plugin) | **39 MB** |
| Those two alone | **137 MB** — 59% of the bundle |
| Vercel Python function ceiling | **~250 MB** unzipped |

233 MB against a ~250 MB ceiling is not a margin; it is a deploy that fails on the next
transitive dependency bump. And the 137 MB buys nothing this feature uses: the report is one
non-streaming JSON completion from one provider.

`httpx` is already a backend dependency (the site-analysis fetcher and the Turnstile verifier
both use it), so a REST connector adds **0 MB**.

## Decision Drivers

- The deployment target decided in [[0004-backend-deploy-provider]] is a size-capped
  serverless function. A dependency that consumes 59% of the cap must earn it.
- `ReportGenerator` is a one-method port, so the cost of being wrong here is one class.
- The report is a single non-streaming completion against a single provider — the multi-provider
  comparison Genkit was chosen for is not what this feature does.
- Whatever the model returns must be provably safe to put in a stranger's inbox.

## Considered Options

1. **Direct REST call to `generativelanguage.googleapis.com` with `httpx`.**
2. **Genkit Python + `genkit-google-genai`** (the ADR 0005 decision) — 137 MB over the wire
   for a feature that uses one provider and no streaming, on a bundle that is already at 93%
   of the ceiling.
3. **`google-genai` SDK without Genkit** — drops the Genkit framework but keeps `google/` and
   `grpc/`, which are the actual 137 MB. Removes the abstraction, keeps the cost.
4. **Move the backend to a container host (Cloud Run) so the bundle limit stops applying** —
   the option [[0004-backend-deploy-provider]] parked. Correct on the merits, but it trades a
   single-provider dashboard for a container toolchain in order to keep a framework this
   feature does not need.

## Decision Outcome

Chosen option: **option 1** — `backend/app/services/report_gemini.py` posts to
`v1beta/models/gemini-2.5-flash:generateContent` with `httpx` and validates the answer.

Request shape:

| Element | Value | Why |
|---------|-------|-----|
| Model | `gemini-2.5-flash` | Fast and cheap enough for a per-lead report. |
| Endpoint | `POST /v1beta/models/{model}:generateContent` | Non-streaming: the report is delivered by email, so there is no consumer for a token stream. |
| Auth | `x-goog-api-key` **header** | Never the query string — URLs end up in proxy logs, traces and error reports. |
| `generationConfig.temperature` | `0` | The same facts about the same company must not yield two different diagnoses. |
| `generationConfig.responseMimeType` | `application/json` | Asks for JSON directly instead of parsing prose. |
| Timeout | 30 s | Bounded by the serverless invocation, not left to the default. |

The connector tolerates the model wrapping its JSON in a ```` ```json ```` fence anyway —
models do it even when told not to — and strips the fence before parsing.

### Security posture — part of the decision, not an add-on

1. **The model's output is untrusted input.** The response is parsed and then validated against
   the same Pydantic models `TemplateReportGenerator` produces (`ContactReport`, whose
   `DiagnosisAxis` and `ServiceOffering` are `StrEnum`s). An invented axis, or a service Code29
   does not sell, raises `ModelResponseInvalid` — it never reaches a lead's inbox. Validation is
   the trust boundary; the prompt is only a request.
2. **No silent fallback to the template.** A model failure raises (`ModelUnavailable` /
   `ModelResponseInvalid`). Delivering a template report while the operator believes a model
   wrote it would make every future report unfalsifiable.
3. **The model sees facts, not the visitor's instructions.** It receives `ReportFacts`, which
   carries `contact_name`, `company`, `locale`, the reported practices and the measured site
   signals — and **no email address**, asserted by a test. This bounds prompt injection by
   construction rather than by filtering. It does not eliminate it:
   `ReportFacts.workflow.notes` is visitor-authored free text and is sent to the model, and the
   template generator quotes it verbatim in the summary. The guarantee that holds regardless is
   (1): injected text can steer the prose, but it cannot produce an axis or a service that does
   not exist, and it cannot reach anything but the report.
4. **The API key never appears in an exception.** Asserted by a test; the failure messages carry
   a status code or an exception class name, nothing else.

### Configuration

`REPORT_GENERATOR` selects the implementation via `build_report_generator`:

| Value | Behaviour |
|-------|-----------|
| `stub` | **Default.** `TemplateReportGenerator` — deterministic, no key, no network. |
| `gemini` | `GeminiReportGenerator`. Requires `GEMINI_API_KEY`; boots with a hard error without it. |
| `genkit` | **Refuses**, naming the real reason: the Genkit Gemini plugin does not fit the deployment's bundle limit. Use `gemini`. |

`genkit` refusing loudly rather than being deleted is deliberate: an operator who read ADR 0005
and set `REPORT_GENERATOR=genkit` gets told why it is gone, instead of an "unknown value" error.

### Consequences

- **Good — 0 MB added.** `httpx` was already a dependency. The bundle stays where Phase 2 left it,
  and the ADR 0004 risk is closed rather than mitigated.
- **Good — reversal is cheap.** `ReportGenerator` is a one-method Protocol
  (`async generate(facts) -> ContactReport`). Going back to Genkit means adding a class and one
  `REPORT_GENERATOR` value: the endpoint, the mailer and the frontend do not know which generator
  ran.
- **Good — the whole flow stays testable with no key and no network.** The default is the
  deterministic stub, and the connector is tested against `httpx.MockTransport`.
- **Bad — no Genkit tracing.** Prompt/response traces, the developer UI and flow-level
  observability are gone. Today the only evidence a report was model-written is the `generator`
  field (`gemini:gemini-2.5-flash`) stamped on `ContactReport`. If real observability of the AI
  layer becomes necessary, it has to be built separately — or Genkit comes back with the backend
  on a container host (see [[0004-backend-deploy-provider]]).
- **Bad — the prompt lives in code.** `_system_instruction()` in `report_gemini.py` is the prompt;
  there is no versioned prompt store, no dotprompt file, no way to change wording without a
  deploy. Changes to it are reviewed as code, which is the only versioning it gets.
- **Bad — no flow registry.** Genkit's flow abstraction would have given a uniform place to
  register future AI steps (the chat itself, for instance). Each one now brings its own connector.
- **Neutral — the multi-provider goal of ADR 0005 is deferred, not dropped.** Comparing Gemini,
  OpenAI and Claude was ADR 0005's stated purpose; nothing here forbids it, but each provider
  would now need its own connector behind the same port, and the bundle cost that killed Genkit
  applies to any provider SDK.
- **Neutral — one more environment variable pair** (`REPORT_GENERATOR`, `GEMINI_API_KEY`) on the
  backend Vercel project.

## Verification status

**Not verified against the real model.** Nobody has yet seen Gemini answer: `GEMINI_API_KEY` is
not configured in any environment.

What *is* verified — 18 tests in `backend/tests/test_report_gemini.py`, all against
`httpx.MockTransport`, **zero real network calls**:

- the request goes to the configured model with the key in the `x-goog-api-key` header;
- the facts are sent and JSON is requested; temperature is pinned to `0`;
- no email address is ever in the payload;
- a valid answer becomes a validated `ContactReport` stamped `gemini:gemini-2.5-flash`;
- a fenced ```` ```json ```` block is tolerated; prose instead of JSON is rejected;
- an unknown axis, a service Code29 does not sell, and an empty candidate list are all rejected;
- a rate limit and an unreachable API raise `ModelUnavailable`;
- the API key never appears in an exception message;
- `REPORT_GENERATOR`: `gemini` demands a key, `stub` is still the default, `genkit` refuses.

Read this as: the connector's contract and its failure modes are pinned. Whether Gemini returns a
report that satisfies `ContactReport` in practice — and how often it does not — is unknown until a
key exists. That is the next verification step, not a detail.

## Locale — both generators now write in the visitor's language

`ReportFacts.locale` (`es` | `en`, default `es`) is honoured on both paths, but by different
mechanisms, and that asymmetry is worth knowing:

- **Gemini** — `_system_instruction()` tells the model which language to write in. The language
  is an instruction, so it is as reliable as the model is.
- **Template** — all copy lives in `backend/app/services/report_copy.py` (`PRACTICE_LABELS`,
  `AXIS_COPY`, `TEMPLATE_COPY`), keyed by locale, with `resolve_locale()` falling back to `es`
  for an unknown value rather than raising. `backend/tests/test_report_locale.py` asserts key
  parity between the two languages, so a missing translation fails the suite instead of shipping
  as an English string in a Spanish report.

This closes a real defect: the template generator previously hard-coded English headings,
diagnoses and summaries and ignored `locale` entirely, so a Spanish-speaking visitor — using a
chat that asks in Spanish — was emailed an English report from the default generator. Fixed
2026-08-22, same branch as this ADR.

## References

- [[0005-genkit-runtime]] — the decision this partially supersedes; the AI-in-the-backend half stands
- [[0004-backend-deploy-provider]] — the bundle ceiling that forced this, and the Cloud Run option it parked
- [[0006-guided-ai-contact-flow]] — the flow that consumes the report
- [[0002-fastapi-as-backend-framework]] — the backend hosting the AI layer
- [[tech-stack-decision]] — overall architecture and phases
- [[index]] — ADR index
- https://ai.google.dev/api/generate-content — Generative Language API reference
