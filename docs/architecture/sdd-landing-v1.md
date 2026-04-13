# SDD: Landing v1 — Implementation Plan

> **Status:** Planned — ready for implementation
> **Jira epic range:** C29-16 → C29-22
> **SDD artifacts:** Engram project Code29, topic keys `sdd/landing-v1/*`

## Implementation Order

| Phase | Epic | Key | Tasks |
|-------|------|-----|-------|
| 1 | Layout & Infrastructure | C29-16 | C29-23 → C29-28 |
| 2 | Home Sections | C29-17 | C29-29 → C29-35 |
| 3 | Cookie Consent | C29-18 | C29-36 → C29-38 |
| 4 | GA4 Analytics | C29-19 | C29-39 → C29-41 |
| 5 | Contact Form | C29-20 | C29-42 → C29-45 |
| 6 | Legal Pages | C29-21 | C29-46 → C29-48 |
| 7 | SEO & Testing | C29-22 | C29-49 → C29-53 |

> **Dependency:** C29-18 (Cookie Consent) MUST be completed before C29-19 (GA4).

## Prerequisites Before Starting

- [ ] GA4 Measurement ID — from Google Analytics console (needed for C29-40)
- [ ] Resend API key + verified domain — from resend.com (needed for C29-42)
- [ ] Legal text copywriting — aviso legal, privacidad, cookies (needed for C29-46/47/48)

## Key Technical Decisions

- All external services accessed via abstractions in `src/utils/` (SOLID DIP)
- Vue 3 Islands (`client:load`) for interactive components only
- `astro.config.ts` output set to `hybrid` to enable Vercel Serverless Functions
- Cookie consent is gatekeeper for GA4 — no analytics data before explicit user opt-in

## References

- [Tech Stack Decision](tech-stack-decision.md)
- [PRD](../requirements/PRD.md)
- [Design](design.md)
- [SDD Workflow](../protocols/sdd-workflow.md)
