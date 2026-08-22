# Architecture Decision Records — Index

Chronological log of significant architecture decisions (MADR format).

| ADR | Title | Status |
|-----|-------|--------|
| [[0001-backend-repo-structure]] | Backend lives in a monorepo `backend/` folder | Accepted |
| [[0002-fastapi-as-backend-framework]] | FastAPI (+ Pydantic) as the backend framework | Accepted |
| [[0003-api-versioning-strategy]] | URL path API versioning (`/api/v1`) | Accepted |
| [[0004-backend-deploy-provider]] | Backend deploys on Vercel as a second project (root `backend/`) | Accepted |
| [[0005-genkit-runtime]] | Genkit on Python, embedded in the FastAPI backend | Accepted (partially superseded by 0007) |
| [[0006-guided-ai-contact-flow]] | Guided AI contact flow with stateless email verification | Accepted |
| [[0007-gemini-over-rest]] | Talk to Gemini over the REST API instead of the Genkit SDK | Accepted |

The **location** decided by 0005 — the AI layer embedded in the FastAPI backend — still
stands; only the **mechanism** (the Genkit Python SDK) was replaced by a direct REST call
in [[0007-gemini-over-rest]].

## References

- [[tech-stack-decision]]
- [[contact-chat-v1]]
