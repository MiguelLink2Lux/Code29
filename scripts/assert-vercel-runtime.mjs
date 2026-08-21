/**
 * Fails when the build emitted a Node runtime Vercel no longer accepts.
 *
 * @astrojs/vercel v7 reads the LOCAL process.version to decide the function
 * runtime. On an unsupported local Node (e.g. 23) it silently falls back to
 * nodejs18.x — and Vercel has rejected Node 18 on new deployments since
 * 2025-09-01. The build still succeeds, so nothing warns you until the deploy
 * fails or the function refuses to boot.
 *
 * `engines.node` in package.json only governs the build Vercel runs from Git.
 * This script is what catches a local build that must not be uploaded with
 * `vercel --prebuilt`.
 */
import { readFileSync } from 'node:fs'
import { join } from 'node:path'

const CONFIG = join(
  process.cwd(),
  '.vercel',
  'output',
  'functions',
  '_render.func',
  '.vc-config.json',
)

const EXPECTED_MAJOR = readFileSync(join(process.cwd(), '.nvmrc'), 'utf8').trim()
const EXPECTED_RUNTIME = `nodejs${EXPECTED_MAJOR}.x`

let config
try {
  config = JSON.parse(readFileSync(CONFIG, 'utf8'))
} catch {
  console.error(`No build output found at ${CONFIG}. Run \`npm run build\` first.`)
  process.exit(1)
}

const localMajor = process.versions.node.split('.')[0]

if (config.runtime !== EXPECTED_RUNTIME) {
  console.error(
    [
      `Emitted Vercel runtime is "${config.runtime}", expected "${EXPECTED_RUNTIME}".`,
      `Local Node is v${process.versions.node}; .nvmrc pins ${EXPECTED_MAJOR}.`,
      localMajor === EXPECTED_MAJOR
        ? 'Investigate the adapter configuration.'
        : `Switch to Node ${EXPECTED_MAJOR} and rebuild, or let Vercel build from Git — it honours .nvmrc and engines.node.`,
      'Never deploy this output with `vercel --prebuilt`.',
    ].join('\n'),
  )
  process.exit(1)
}

console.log(`Vercel runtime OK: ${config.runtime} (local Node v${process.versions.node})`)
