// @vitest-environment node
/**
 * Runs scripts/assert-vercel-runtime.mjs against throwaway `.vercel/output`
 * trees, one per row of the COD-36 I/O matrix. The script reads everything
 * relative to its cwd, so each fixture is just a temp dir with an .nvmrc.
 */
import { spawnSync } from 'node:child_process'
import { mkdirSync, mkdtempSync, rmSync, writeFileSync } from 'node:fs'
import { tmpdir } from 'node:os'
import { join, resolve } from 'node:path'

import { afterEach, beforeEach, describe, expect, it } from 'vitest'

const SCRIPT = resolve(__dirname, '../../scripts/assert-vercel-runtime.mjs')

let cwd: string

const run = () => spawnSync(process.execPath, [SCRIPT], { cwd, encoding: 'utf8' })

const writeFunction = (name: string, runtime: string) => {
  const dir = join(cwd, '.vercel', 'output', 'functions', name)
  mkdirSync(dir, { recursive: true })
  writeFileSync(join(dir, '.vc-config.json'), JSON.stringify({ runtime }))
}

beforeEach(() => {
  cwd = mkdtempSync(join(tmpdir(), 'assert-vercel-runtime-'))
  writeFileSync(join(cwd, '.nvmrc'), '24\n')
})

afterEach(() => {
  rmSync(cwd, { recursive: true, force: true })
})

describe('assert-vercel-runtime', () => {
  it('fails when there is no build output at all', () => {
    const result = run()
    expect(result.status).toBe(1)
    expect(result.stderr).toContain('Run `npm run build` first')
  })

  it('passes on static output with no functions directory', () => {
    mkdirSync(join(cwd, '.vercel', 'output', 'static'), { recursive: true })
    const result = run()
    expect(result.status).toBe(0)
    expect(result.stdout).toContain('static output, no function runtime')
  })

  it('passes when the functions directory holds no function config', () => {
    mkdirSync(join(cwd, '.vercel', 'output', 'functions', 'empty'), { recursive: true })
    const result = run()
    expect(result.status).toBe(0)
    expect(result.stdout).toContain('static output, no function runtime')
  })

  it('passes when every function targets the pinned runtime', () => {
    writeFunction('_render.func', 'nodejs24.x')
    writeFunction('api/nested.func', 'nodejs24.x')
    expect(run().status).toBe(0)
  })

  it.each(['nodejs18.x', 'nodejs20.x'])('fails on a stale %s function and names it', (runtime) => {
    writeFunction('_render.func', 'nodejs24.x')
    writeFunction('api/stale.func', runtime)
    const result = run()
    expect(result.status).toBe(1)
    expect(result.stderr).toContain(join('api', 'stale.func', '.vc-config.json'))
    expect(result.stderr).toContain(`"${runtime}"`)
    expect(result.stderr).toContain('"nodejs24.x"')
    expect(result.stderr).toContain('Never deploy this output with `vercel --prebuilt`')
  })
})
