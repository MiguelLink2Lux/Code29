> **Type:** Architecture · ADR — **Status:** Accepted (partially superseded by 0007) — **Date:** 2026-08-19
> **Part of:** [[Decisions]]

# ADR 0005 — Genkit on Python, embedded in the FastAPI backend

- **Status:** Accepted — **partially superseded by [[0007-gemini-over-rest]]**
- **Date:** 2026-08-19
- **Deciders:** Miguel Navarro Mantas
- **Linear:** COD-31

> **Partially superseded by [[0007-gemini-over-rest]] (2026-08-22).** This ADR decided two
> things at once. What **still stands**: the AI layer lives embedded in the FastAPI backend —
> one language on the server side, one process, one deployment, one test suite. What was
> **replaced**: the *mechanism* for reaching the model. The Genkit Python SDK is no longer
> used; the backend calls the Google Generative Language REST API directly over `httpx`,
> because the `genkit-google-genai` plugin drags in 137 MB of `google/` and `grpc/` and does
> not fit Vercel's ~250 MB Python function ceiling. Genkit is not installed. Everything below
> is kept as the historical record of the original decision.

## Context and Problem Statement

Phase 3 introduces an AI layer whose stated goal is to try and compare models across
several providers — Google AI Studio (Gemini) as the primary target, plus OpenAI and
Anthropic. Genkit was chosen as the framework that fronts those providers, but Genkit
ships SDKs in several languages at different maturity levels, and the project already
runs TypeScript on Vercel *and* Python in `backend/`. Both are physically available,
and they are not equivalent: the choice determines where the AI layer lives, how many
services get deployed, and how many languages the server side speaks.

## Decision Drivers

- Keep one language on the server side.
- Async-first request handling for streaming AI responses.
- Reuse the existing typed configuration (`pydantic-settings`, `Settings`).
- Do not contradict the Phase 3 design already documented.
- Provider plugins must actually exist for the chosen runtime — verified, not assumed.

## Considered Options

1. **Genkit Python inside the FastAPI backend** — one backend language, async-first,
   Pydantic integration. Beta SDK, not at feature parity with Node.
2. **Genkit TypeScript on Vercel** — the only stable SDK, full plugin ecosystem, no new
   runtime to host. Splits the AI layer from the backend built for it and puts two
   languages on the server side.
3. **Genkit Go** — rejected outright: there is no Go anywhere in the project.

SDK maturity as verified on 2026-08-17: TypeScript **stable**, Python **Beta**, Go Beta,
Dart Preview.

## Decision Outcome

Chosen option: **Genkit on Python, inside `backend/`** (FastAPI + uv, Python `>=3.12,<3.13`).
No separate Node service and no second deployment.

The Beta SDK is accepted deliberately: splitting server-side logic across two languages
costs more, permanently, than living with a pre-1.0 dependency in one place. The choice
is also the one the Phase 3 design already assumed — `contact-chat-v1.md` describes
Phase 3 as "Backend FastAPI, orquestacion IA, respuestas en streaming".

### Plugin availability (verified on PyPI, 2026-08-19)

All at version 0.9.0, uploaded 2026-07-31, `requires-python >=3.10` — compatible with
the backend's 3.12 pin:

| Package | Covers | Notes |
|---------|--------|-------|
| `genkit` | framework core | author Google |
| `genkit-google-genai` | Google AI Studio (Gemini) + Vertex AI | dep `google-genai>=1.63.0` |
| `genkit-openai` | OpenAI and OpenAI-compatible APIs | dep `openai` |
| `genkit-anthropic` | Claude | declared **"(Community)"**, dep `anthropic>=0.96.0` |
| `genkit-fastapi` | FastAPI integration | deps `fastapi>=0.100.0`, `pydantic>=2.10.5` |

Reproduce with `curl -s https://pypi.org/simple/ | grep genkit` to enumerate, then
`curl -s https://pypi.org/pypi/<pkg>/json` for version, `requires_python` and dependencies.

### Package naming — two traps

- The `genkit-plugin-*` distributions are **deprecated and renamed** to `genkit-*`
  (`genkit-plugin-google-genai` → `genkit-google-genai`, and so on). Older documentation
  and tutorials cite the dead names.
- **`genkit-ai` is not the core package.** It is stuck at `0.0.1.dev1` from 2025-03-31.
  The core is plain `genkit`.

### Consequences

- Good: the AI layer runs in the same process as the API — one deployment, one
  `pyproject.toml`, one test suite (`uv run pytest`).
- Good: `genkit-fastapi` exists as a first-class plugin, so this combination is a
  supported path rather than an improvisation.
- Good: Pydantic-native, matching the existing typed `Settings`.
- Bad: commits the project to a pre-1.0 (0.9.0) Beta SDK, giving up the only stable one.
- Bad: the Anthropic plugin is labelled "Community" while Google's and OpenAI's are not —
  the weakest of the three, and the one to isolate most carefully behind the abstraction.
- Neutral: supersedes the assumption in [[tech-stack-decision]] §Phase 3 and in
  [[0002-fastapi-as-backend-framework]] that models would be reached through the
  Anthropic SDK directly. Provider access now goes through Genkit.

### Binding constraints on the implementation

1. **SOLID DIP** (mandatory per project `CLAUDE.md`): business logic never imports Genkit
   or a provider SDK. Access goes through a boundary module, the same pattern as
   `src/utils/analytics.ts` and `src/utils/contact.ts`.
2. **Model selection by configuration**: the active model is an environment variable, not
   a code change. This follows directly from the goal of comparing models.
3. **Three API keys** — `GEMINI_API_KEY` (or `GOOGLE_API_KEY`), `OPENAI_API_KEY`,
   `ANTHROPIC_API_KEY` — but only the **active provider's** key may be required at boot.
   Demanding all three would make it impossible to test with one. Reference pattern:
   `getRequiredEnv` in `src/pages/api/contact.ts`, which fails loudly with 503.
4. **GDPR**: each provider is a distinct data processor. The privacy policy must name
   whichever one is live in production.
5. **Cost**: comparing models spends tokens across three bills. Rate limiting and a spend
   ceiling are operational necessities here, not precautions.

## Verification status

**Installed and resolved (spike, 2026-08-19).** `uv add genkit genkit-google-genai genkit-fastapi
genkit-openai genkit-anthropic` resolved cleanly against the `>=3.12,<3.13` pin on Python 3.12.10,
pulling `anthropic==0.124.0` and `openai==3.3.1`. All five modules import. The pre-existing suite
still passes (`uv run pytest` → 12 passed) and `uv run ruff check` is clean, so the dependency
addition did not disturb the healthcheck delivered in Phase 2.

### Import paths — a third naming trap

The plugins install as **top-level modules with underscores**, not as a `genkit.plugins.*` namespace:

```python
from genkit import Genkit
import genkit_google_genai   # exposes GoogleAI, GeminiConfigSchema, ...
import genkit_openai         # exposes OpenAI, OpenAIConfig, ...
import genkit_anthropic      # exposes Anthropic, AnthropicConfig, ...
import genkit_fastapi        # exposes serve_flow, serve_agent, handler, ...
```

`import genkit.plugins` raises `ModuleNotFoundError`. Documentation that uses that path is stale.

### Still not verified

**No real call to any model has been made** — no provider API key is configured in the environment.
The stack installs and imports; that it can actually reach Gemini, OpenAI or Claude is unproven, and
this ADR must not be read as evidence that it does.

## References

- [[0001-backend-repo-structure]]
- [[0002-fastapi-as-backend-framework]]
- [[0003-api-versioning-strategy]]
- [[contact-chat-v1]] — Phase 3 already sketched as FastAPI + AI orchestration + streaming
- [[tech-stack-decision]]
- https://github.com/genkit-ai/genkit
