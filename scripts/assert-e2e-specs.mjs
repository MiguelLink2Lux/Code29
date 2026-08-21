/**
 * Fails if the e2e suite is empty.
 *
 * Before this guard, tests/e2e/ contained zero specs while package.json advertised
 * `npm run test:e2e` — the gate reported on nothing at all. A deleted spec file
 * must break the build, not quietly shrink coverage.
 */
import { readdirSync } from 'node:fs'
import { join } from 'node:path'

const MINIMUM_SPECS = 4
const E2E_DIR = join(process.cwd(), 'tests', 'e2e')

const specs = readdirSync(E2E_DIR).filter((file) => file.endsWith('.spec.ts'))

if (specs.length < MINIMUM_SPECS) {
  console.error(
    `e2e suite too small: found ${specs.length} spec file(s) in tests/e2e, expected at least ${MINIMUM_SPECS}.`,
  )
  process.exit(1)
}

console.log(`e2e specs found: ${specs.length} (${specs.join(', ')})`)
