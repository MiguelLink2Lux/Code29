# SDD: Landing v1 — Implementation Plan

> **Status:** In Progress — Phase 1 ✅ Phase 2 ✅ | Next: Phase 3 (Cookie Consent)
> **Jira epic range:** C29-16 → C29-22
> **SDD artifacts:** Engram project Code29, topic keys `sdd/landing-v1/*`

## Implementation Order

| Phase | Epic | Key | Tasks | Status |
|-------|------|-----|-------|--------|
| 1 | Layout & Infrastructure | C29-16 | C29-23 → C29-28 | ✅ Done |
| 2 | Home Sections | C29-17 | C29-29 → C29-35 | ✅ Done |
| 3 | Cookie Consent | C29-18 | C29-36 → C29-38 | 🔲 Pending |
| 4 | GA4 Analytics | C29-19 | C29-39 → C29-41 | 🔲 Pending |
| 5 | Contact Form | C29-20 | C29-42 → C29-45 | 🔲 Pending |
| 6 | Legal Pages | C29-21 | C29-46 → C29-48 | 🔲 Pending |
| 7 | SEO & Testing | C29-22 | C29-49 → C29-53 | 🔲 Pending |

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
- `@astrojs/vercel@^7.8.2` used (v10 requires Astro 6 — incompatible with current Astro 4.16)

## Implementation Log

### Phase 1 — Layout & Infrastructure ✅ (2026-04-14)

| File | Action |
|------|--------|
| `astro.config.ts` | Changed `output: 'static'` → `'hybrid'`, added `@astrojs/vercel` adapter |
| `package.json` | Added `@astrojs/vercel@^7.8.2` |
| `src/components/layout/Nav.astro` | Created — logo, links (Servicios/Stack/Testimonios), CTA → `#contacto` |
| `src/components/layout/Footer.astro` | Created — legal links, cookie preferences button (dispatches `open-cookie-preferences` event) |
| `src/layouts/BaseLayout.astro` | Extended — SEO props (OG, Twitter Card, canonical), Nav, Footer, `analytics` slot |
| `src/layouts/LegalLayout.astro` | Created — simplified layout with `noindex`, prose styles |
| `public/robots.txt` | Created — allow all, sitemap reference |

### Phase 2 — Home Sections ✅ (2026-04-14)

| File | Action |
|------|--------|
| `src/components/sections/HeroSection.astro` | Created — "THE NEON ARCHITECT" tagline, headline, dual CTA, decorative grid |
| `src/components/sections/StatsSection.astro` | Created — 4 metrics: 2x–3x speed, -60% errors, M+ transactions, Zero Trust |
| `src/components/sections/EducationStackSection.astro` | Created — AI Master's + 15-item tech stack grid with categories |
| `src/components/sections/ServicesSection.astro` | Created — CTO as a Service + AI Project Manager cards with features |
| `src/components/sections/TestimonialsSection.astro` | Created — 3 testimonials (Javier Domínguez, Elena Martí, Ricardo Costa) |
| `src/components/sections/ContactSection.astro` | Created — wrapper with `id="contacto"`, placeholder for Phase 5 form |
| `src/pages/index.astro` | Updated — composes all 6 sections in order |

## References

- [Tech Stack Decision](tech-stack-decision.md)
- [PRD](../requirements/PRD.md)
- [Design](design.md)
- [SDD Workflow](../protocols/sdd-workflow.md)
