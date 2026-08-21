import type { APIRoute } from 'astro'

import { buildRobotsTxt } from '@/utils/seo'

// Prerendered so it is a plain static file in production, but generated from
// src/utils/seo.ts — the origin and sitemap filename live in exactly one place.
export const prerender = true

export const GET: APIRoute = () =>
  new Response(buildRobotsTxt(), {
    headers: { 'Content-Type': 'text/plain; charset=utf-8' },
  })
