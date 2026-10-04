/**
 * Fails when the build emitted a Node runtime Vercel no longer accepts.
 *
 * Adapters have picked the function runtime from the LOCAL process.version and
 * silently fallen back to a stale one on an unsupported local Node (v7 emitted
 * nodejs18.x on Node 23). The build still succeeds, so nothing warns you until
 * the deploy fails or the function refuses to boot.
 *
 * With @astrojs/vercel 9 and no on-demand routes the site is fully static, so
 * there is usually no function at all — that passes. Every function the build
 * does emit (`functions/**\/.vc-config.json`) must target the .nvmrc major.
 *
 * `engines.node` in package.json only governs the build Vercel runs from Git.
 * This script is what catches a local build that must not be uploaded with
 * `vercel --prebuilt`.
 */
import { existsSync, readdirSync, readFileSync } from 'node:fs'
import { join, relative } from 'node:path'

const OUTPUT = join(process.cwd(), '.vercel', 'output')
const FUNCTIONS = join(OUTPUT, 'functions')

const EXPECTED_MAJOR = readFileSync(join(process.cwd(), '.nvmrc'), 'utf8').trim()
const EXPECTED_RUNTIME = `nodejs${EXPECTED_MAJOR}.x`

if (!existsSync(OUTPUT)) {
  console.error(`No build output found at ${OUTPUT}. Run \`npm run build\` first.`)
  process.exit(1)
}

if (!existsSync(FUNCTIONS)) {
  console.log('Vercel runtime OK: static output, no function runtime')
  process.exit(0)
}

const configs = readdirSync(FUNCTIONS, { recursive: true })
  .filter((entry) => entry.split(/[\\/]/).pop() === '.vc-config.json')
  .map((entry) => join(FUNCTIONS, entry))

if (configs.length === 0) {
  console.log('Vercel runtime OK: static output, no function runtime')
  process.exit(0)
}

const localMajor = process.versions.node.split('.')[0]
const stale = configs
  .map((file) => ({ file, runtime: JSON.parse(readFileSync(file, 'utf8')).runtime }))
  .filter(({ runtime }) => runtime !== EXPECTED_RUNTIME)

if (stale.length > 0) {
  console.error(
    [
      ...stale.map(
        ({ file, runtime }) =>
          `${relative(process.cwd(), file)}: emitted runtime "${runtime}", expected "${EXPECTED_RUNTIME}".`
      ),
      `Local Node is v${process.versions.node}; .nvmrc pins ${EXPECTED_MAJOR}.`,
      localMajor === EXPECTED_MAJOR
        ? 'Investigate the adapter configuration.'
        : `Switch to Node ${EXPECTED_MAJOR} and rebuild, or let Vercel build from Git — it honours engines.node.`,
      'Never deploy this output with `vercel --prebuilt`.',
    ].join('\n')
  )
  process.exit(1)
}

console.log(
  `Vercel runtime OK: ${configs.length} function(s) on ${EXPECTED_RUNTIME} (local Node v${process.versions.node})`
)
