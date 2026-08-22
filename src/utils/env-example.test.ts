/**
 * `.env.example` is the only map a newcomer (or a fresh Vercel project) has of
 * what the frontend needs. A variable the code reads but the template omits is
 * discovered the hard way: a 503 in production, or a blank og:image.
 *
 * Static `import.meta.env.X` reads are discovered by scanning; the ones reached
 * reached through an injected env bag rather than a literal `import.meta.env.X`
 * are listed explicitly, since no scan can see them.
 */
import { readdirSync, readFileSync, statSync } from 'node:fs'
import { join } from 'node:path'

import { describe, expect, it } from 'vitest'

const ROOT = process.cwd()
const TEMPLATE = join(ROOT, '.env.example')

/**
 * Variables reached through an injected bag rather than a literal
 * `import.meta.env.X`, so no scan can see them. The Resend/CONTACT_* trio moved
 * to the backend when the guided chat replaced the serverless form.
 */
const DYNAMICALLY_READ = ['PUBLIC_API_BASE_URL', 'PUBLIC_TURNSTILE_SITE_KEY']

function sourceFiles(dir: string): string[] {
  return readdirSync(dir).flatMap((entry) => {
    const full = join(dir, entry)
    if (statSync(full).isDirectory()) return sourceFiles(full)
    return /\.(ts|astro|vue|mjs)$/.test(entry) && !entry.endsWith('.test.ts') ? [full] : []
  })
}

function scannedEnvNames(): Set<string> {
  const names = new Set<string>()

  for (const file of sourceFiles(join(ROOT, 'src'))) {
    const source = readFileSync(file, 'utf8')
    for (const match of source.matchAll(/import\.meta\.env\.([A-Z][A-Z0-9_]*)/g)) {
      names.add(match[1])
    }
    // `env.PUBLIC_*` on an injected env bag (e.g. src/utils/seo.ts).
    for (const match of source.matchAll(/\benv\.(PUBLIC_[A-Z0-9_]+)/g)) {
      names.add(match[1])
    }
  }

  return names
}

function documentedNames(): Set<string> {
  const names = new Set<string>()

  for (const line of readFileSync(TEMPLATE, 'utf8').split('\n')) {
    // Matches both `NAME=` and the commented `# NAME=` placeholder form.
    const match = line.match(/^\s*#?\s*([A-Z][A-Z0-9_]*)=/)
    if (match) names.add(match[1])
  }

  return names
}

describe('.env.example', () => {
  it('exists at the repo root', () => {
    expect(() => readFileSync(TEMPLATE, 'utf8')).not.toThrow()
  })

  it('documents every variable the source reads', () => {
    const documented = documentedNames()
    const missing = [...scannedEnvNames(), ...DYNAMICALLY_READ].filter(
      (name) => !documented.has(name),
    )

    expect(missing, 'variables read by the code but absent from .env.example').toEqual([])
  })

  it('carries no real values — only placeholders', () => {
    const template = readFileSync(TEMPLATE, 'utf8')

    // A Resend key starts with `re_`; a GA4 id with `G-` and always contains
    // digits. Requiring a digit is what separates a real id from a `G-XXXX`
    // placeholder — matching on shape alone would flag the template itself.
    expect(template).not.toMatch(/re_[A-Za-z0-9]{8,}/)
    expect(template).not.toMatch(/=\s*G-[A-Z0-9]*[0-9][A-Z0-9]*/)
  })
})
