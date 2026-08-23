# Architecture Decision Records — Index

Chronological log of significant architecture decisions (MADR format).

| ADR | Title | Status |
|-----|-------|--------|
| [[0001-backend-repo-structure]] | Backend lives in a monorepo `backend/` folder | Accepted |
| [[0002-fastapi-as-backend-framework]] | FastAPI (+ Pydantic) as the backend framework | Accepted |
| [[0003-api-versioning-strategy]] | URL path API versioning (`/api/v1`) | Accepted |
| [[0004-backend-deploy-provider]] | Backend deploys on Vercel as a second project (root `backend/`) | Accepted |
| [[0005-genkit-runtime]] | Genkit on Python, embedded in the FastAPI backend | Accepted (partially superseded by 0007) |
| [[0006-guided-ai-contact-flow]] | Guided AI contact flow with stateless email verification | Accepted (report structure superseded by 0008) |
| [[0007-gemini-over-rest]] | Talk to Gemini over the REST API instead of the Genkit SDK | Accepted |
| [[0008-improvement-canon]] | Ten fixed improvement points as the structure of the workflow report | Accepted (partially supersedes 0006) |

The **location** decided by 0005 — the AI layer embedded in the FastAPI backend — still
stands; only the **mechanism** (the Genkit Python SDK) was replaced by a direct REST call
in [[0007-gemini-over-rest]].

[[0008-improvement-canon]] supersedes one part of [[0006-guided-ai-contact-flow]]: the
report's diagnosis structure moves from five `DiagnosisAxis` members to the ten fixed points
of [[improvement-canon]]. Everything else 0006 decided — the step order as an authorisation
rule, stateless verification, the Turnstile gate, the SSRF guard, the privacy posture —
stands unchanged.

## References

- [[tech-stack-decision]]
- [[contact-chat-v1]]
- [[improvement-canon]]
