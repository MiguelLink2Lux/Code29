// @vitest-environment node
/**
 * The verifier's reading of one conversation turn, one case per row of the
 * COD-69 matrix. It used to read `missing` whatever the HTTP status, so a 502
 * from a failing model was reported as "the stub is answering".
 */
import { describe, expect, it } from 'vitest'

import { conversationCheck } from '../../scripts/lib/conversation-check.mjs'

describe('conversationCheck', () => {
  it('passes when the model extracted the name', () => {
    const result = conversationCheck(200, { missing: ['company'] })

    expect(result.ok).toBe(true)
  })

  it('warns, without blocking, when the stub is answering', () => {
    const result = conversationCheck(200, { missing: ['contact_name', 'company'] })

    expect(result).toMatchObject({ ok: false, blocking: false })
    expect(result.detail).toMatch(/no model configured/)
  })

  it.each([502, 500, 503, 429])('fails the deploy when the turn answers %i', (status) => {
    const result = conversationCheck(status, { detail: 'No he podido procesar tu mensaje.' })

    expect(result).toMatchObject({ ok: false, blocking: true })
    expect(result.detail).toContain(`the model failed (HTTP ${status})`)
    expect(result.detail).not.toMatch(/stub/)
  })

  it('fails the deploy when the turn could not be reached at all', () => {
    const result = conversationCheck(undefined, null)

    expect(result).toMatchObject({ ok: false, blocking: true })
  })
})
