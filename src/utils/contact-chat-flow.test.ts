import { describe, expect, it } from 'vitest'

import { CONTACT_CHAT_STEPS, stepById, validateAnswer } from '@/utils/contact-chat-flow'

describe('flow definition', () => {
  it('is a fixed, ordered sequence — not a free chat', () => {
    expect(CONTACT_CHAT_STEPS.map((step) => step.id)).toEqual([
      'name',
      'company',
      'email',
      'code',
      'delivery',
      'bugs',
      'deploys',
      'security',
      'observability',
      'website',
      'consent',
    ])
  })

  it('gates every expensive step behind email verification', () => {
    const ids = CONTACT_CHAT_STEPS.map((step) => step.id)
    const codeIndex = ids.indexOf('code')

    // Nothing that costs us money or reputation may precede verification.
    for (const gated of ['website', 'consent'] as const) {
      expect(ids.indexOf(gated)).toBeGreaterThan(codeIndex)
    }
  })

  it('asks about the four diagnosis axes the report is built on', () => {
    const ids = CONTACT_CHAT_STEPS.map((step) => step.id)
    for (const axis of ['delivery', 'bugs', 'deploys', 'security', 'observability']) {
      expect(ids).toContain(axis)
    }
  })

  it('offers choices for the workflow questions instead of free text', () => {
    for (const id of ['delivery', 'bugs', 'deploys', 'security', 'observability']) {
      const step = stepById(id)
      expect(step.kind).toBe('choice')
      expect(step.options?.length ?? 0).toBeGreaterThanOrEqual(3)
    }
  })

  it('never marks a step optional without a default', () => {
    for (const step of CONTACT_CHAT_STEPS) {
      if (!step.required) expect(step.skippable).toBe(true)
    }
  })
})

describe('validateAnswer', () => {
  it('requires a name', () => {
    expect(validateAnswer('name', '')).toBe('required')
    expect(validateAnswer('name', '  ')).toBe('required')
    expect(validateAnswer('name', 'Ada')).toBeNull()
  })

  it('validates the email shape', () => {
    expect(validateAnswer('email', 'not-an-email')).toBe('invalidEmail')
    expect(validateAnswer('email', 'ada@example.com')).toBeNull()
  })

  it('requires exactly six digits for the code', () => {
    expect(validateAnswer('code', '12345')).toBe('invalidCode')
    expect(validateAnswer('code', 'abcdef')).toBe('invalidCode')
    expect(validateAnswer('code', '123456')).toBeNull()
  })

  it('accepts a choice only from the offered options', () => {
    const step = stepById('deploys')
    expect(validateAnswer('deploys', 'something-else')).toBe('invalidChoice')
    expect(validateAnswer('deploys', step.options![0].value)).toBeNull()
  })

  it('accepts a website with or without a scheme but rejects nonsense', () => {
    expect(validateAnswer('website', 'example.com')).toBeNull()
    expect(validateAnswer('website', 'https://example.com')).toBeNull()
    expect(validateAnswer('website', 'not a url')).toBe('invalidUrl')
    // Skippable: a company without a site must be able to move on.
    expect(validateAnswer('website', '')).toBeNull()
  })

  it('requires consent to be explicitly granted', () => {
    expect(validateAnswer('consent', 'false')).toBe('consentRequired')
    expect(validateAnswer('consent', '')).toBe('consentRequired')
    expect(validateAnswer('consent', 'true')).toBeNull()
  })

  it('caps free-text length so the payload cannot be abused', () => {
    expect(validateAnswer('company', 'x'.repeat(400))).toBe('tooLong')
  })
})
