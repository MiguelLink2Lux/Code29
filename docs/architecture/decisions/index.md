# Architecture Decision Records — Index

Chronological log of significant architecture decisions (MADR format).

| ADR | Title | Status |
|-----|-------|--------|
| [[0001-backend-repo-structure]] | Backend lives in a monorepo `backend/` folder | Accepted |
| [[0002-fastapi-as-backend-framework]] | FastAPI (+ Pydantic) as the backend framework | Accepted |
| [[0003-api-versioning-strategy]] | URL path API versioning (`/api/v1`) | Accepted |
| [[0004-backend-deploy-provider]] | Backend deploys on Vercel as a second project (root `backend/`) | Accepted |
| [[0005-genkit-runtime]] | Genkit on Python, embedded in the FastAPI backend | Accepted (partially superseded by 0007) |
| [[0006-guided-ai-contact-flow]] | Guided AI contact flow with stateless email verification | Accepted (step flow superseded by 0009; report structure by 0008) |
| [[0007-gemini-over-rest]] | Talk to Gemini over the REST API instead of the Genkit SDK | Accepted |
| [[0008-improvement-canon]] | Ten fixed improvement points as the structure of the workflow report | Accepted (partially supersedes 0006) |
| [[0009-conversational-contact-agent]] | A conversational agent replaces the guided questionnaire, and an agent verifies the report | Accepted (partially supersedes 0006) |

The **location** decided by 0005 — the AI layer embedded in the FastAPI backend — still
stands; only the **mechanism** (the Genkit Python SDK) was replaced by a direct REST call
in [[0007-gemini-over-rest]].

[[0006-guided-ai-contact-flow]] is superseded in **two parts, by two ADRs**, and current in
everything else:

- [[0008-improvement-canon]] replaces the **report's diagnosis structure** — five
  `DiagnosisAxis` members become the ten fixed points of [[improvement-canon]].
- [[0009-conversational-contact-agent]] replaces the **eleven-step fixed flow** with a
  conversational agent, and is where the canon report is actually implemented.

Still in force from 0006: stateless email verification by HMAC, Turnstile failing closed, the
SSRF guard, the absence of a datastore and the privacy posture. Note that "the step order is
an authorisation rule" is gone with the steps — 0009 restates the property as a server-side
completeness predicate over the access token.

**Live since 2026-08-24.** The `contact-chat-agent` cycle completed (phases A–E) and cut over
in PR #29 (`462e927`): the conversational agent and the ten-point canon report are what the site
serves, and the eleven-step questionnaire was deleted, not left dormant. Search grounding ships
off — see §7 of 0009.

## References

- [[tech-stack-decision]]
- [[contact-chat-v1]]
- [[improvement-canon]]
