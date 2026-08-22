import { beforeEach, describe, expect, it, vi } from 'vitest'

import { createContactChat } from '@/utils/contact-chat'

const answerAll = (chat: ReturnType<typeof createContactChat>) => {
  chat.answer('Ada Lovelace')
  chat.answer('Analytical Engines')
  chat.answer('ada@example.com')
  chat.answer('123456')
  chat.answer('ai-assisted-editor')
  chat.answer('automated-tests-gate')
  chat.answer('ci-cd-pipeline')
  chat.answer('dependency-scanning')
  chat.answer('error-monitoring')
  chat.answer('example.com')
  chat.answer('true')
}

beforeEach(() => {
  sessionStorage.clear()
})

describe('progression', () => {
  it('starts on the first step', () => {
    expect(createContactChat().state.currentStepId).toBe('name')
  })

  it('advances only when the answer is valid', () => {
    const chat = createContactChat()

    expect(chat.answer('')).toEqual({ ok: false, error: 'required' })
    expect(chat.state.currentStepId).toBe('name')

    expect(chat.answer('Ada')).toEqual({ ok: true })
    expect(chat.state.currentStepId).toBe('company')
  })

  it('records answers in order as a transcript', () => {
    const chat = createContactChat()
    chat.answer('Ada')
    chat.answer('')

    expect(chat.state.transcript).toEqual([
      { stepId: 'name', answer: 'Ada' },
      { stepId: 'company', answer: '' },
    ])
  })

  it('reports completion only after the last step', () => {
    const chat = createContactChat()
    expect(chat.state.complete).toBe(false)

    answerAll(chat)

    expect(chat.state.complete).toBe(true)
  })

  it('exposes progress for the UI', () => {
    const chat = createContactChat()
    expect(chat.state.progress).toEqual({ index: 0, total: 11 })

    chat.answer('Ada')

    expect(chat.state.progress).toEqual({ index: 1, total: 11 })
  })

  it('allows going back without losing what was already answered', () => {
    const chat = createContactChat()
    chat.answer('Ada')
    chat.answer('Analytical Engines')

    chat.back()

    expect(chat.state.currentStepId).toBe('company')
    expect(chat.answerFor('name')).toBe('Ada')
  })

  it('ignores back on the first step', () => {
    const chat = createContactChat()
    chat.back()
    expect(chat.state.currentStepId).toBe('name')
  })
})

describe('verification gate', () => {
  it('knows the email is not verified until the code step is passed', () => {
    const chat = createContactChat()
    chat.answer('Ada')
    chat.answer('')
    chat.answer('ada@example.com')

    expect(chat.state.emailVerified).toBe(false)

    chat.markEmailVerified('token-abc')

    expect(chat.state.emailVerified).toBe(true)
    expect(chat.state.accessToken).toBe('token-abc')
  })

  it('never exposes the access token in the transcript', () => {
    const chat = createContactChat()
    chat.answer('Ada')
    chat.answer('')
    chat.answer('ada@example.com')
    chat.markEmailVerified('token-abc')

    expect(JSON.stringify(chat.state.transcript)).not.toContain('token-abc')
  })
})

describe('persistence', () => {
  it('survives a reload within the same tab', () => {
    const first = createContactChat()
    first.answer('Ada')
    first.answer('Analytical Engines')

    const restored = createContactChat()

    expect(restored.state.currentStepId).toBe('email')
    expect(restored.answerFor('name')).toBe('Ada')
  })

  it('uses sessionStorage, so lead data dies with the tab', () => {
    const chat = createContactChat()
    chat.answer('Ada')

    expect(sessionStorage.getItem('contact-chat')).not.toBeNull()
    expect(localStorage.getItem('contact-chat')).toBeNull()
  })

  it('never persists the access token', () => {
    const chat = createContactChat()
    chat.answer('Ada')
    chat.markEmailVerified('token-abc')

    expect(sessionStorage.getItem('contact-chat')).not.toContain('token-abc')
  })

  it('starts clean when the stored payload is corrupted', () => {
    sessionStorage.setItem('contact-chat', '{ not json')

    expect(createContactChat().state.currentStepId).toBe('name')
  })

  it('starts clean when storage is unavailable', () => {
    vi.spyOn(Storage.prototype, 'getItem').mockImplementation(() => {
      throw new Error('denied')
    })

    expect(() => createContactChat()).not.toThrow()

    vi.restoreAllMocks()
  })

  it('clears everything on reset', () => {
    const chat = createContactChat()
    chat.answer('Ada')

    chat.reset()

    expect(chat.state.currentStepId).toBe('name')
    expect(sessionStorage.getItem('contact-chat')).toBeNull()
  })
})

describe('payload', () => {
  it('builds the report request from the collected answers', () => {
    const chat = createContactChat()
    answerAll(chat)
    chat.markEmailVerified('token-abc')

    const payload = chat.buildReportRequest()

    expect(payload.contact_name).toBe('Ada Lovelace')
    expect(payload.company).toBe('Analytical Engines')
    expect(payload.locale).toBe('es')
    expect(payload.site_url).toBe('https://example.com')
    expect(payload.consent.privacy_accepted).toBe(true)
  })

  it('omits the email from the payload — the token carries it', () => {
    const chat = createContactChat()
    answerAll(chat)
    chat.markEmailVerified('token-abc')

    expect(JSON.stringify(chat.buildReportRequest())).not.toContain('ada@example.com')
  })

  it('refuses to build a payload before the flow is complete', () => {
    const chat = createContactChat()
    chat.answer('Ada')

    expect(() => chat.buildReportRequest()).toThrow(/incomplete/i)
  })
})

describe('backend contract', () => {
  it('maps the four choice answers onto the practice identifiers the report expects', () => {
    const chat = createContactChat()
    answerAll(chat)
    chat.markEmailVerified('token-abc')

    const payload = chat.buildReportRequest()

    // The report diagnoses axes by comparing practices present against absent,
    // so the chat's answers must arrive as those identifiers — not as its own
    // option values, which the generator would not recognise.
    expect(payload.workflow.practices).toEqual(
      expect.arrayContaining(['ai_assisted_coding', 'automated_tests', 'ci_pipeline']),
    )
  })

  it('reports no practices when nothing is in place', () => {
    const chat = createContactChat()
    chat.answer('Ada')
    chat.answer('')
    chat.answer('ada@example.com')
    chat.answer('123456')
    chat.answer('no-ai')
    chat.answer('manual-triage')
    chat.answer('manual-deploys')
    chat.answer('none')
    chat.answer('none')
    chat.answer('')
    chat.answer('true')

    expect(chat.buildReportRequest().workflow.practices).toEqual([])
  })

  it('sends an absolute site_url, since the backend rejects a scheme-less one', () => {
    const chat = createContactChat()
    answerAll(chat)

    expect(chat.buildReportRequest().site_url).toBe('https://example.com')
  })

  it('sends null site_url when the visitor skipped it', () => {
    const chat = createContactChat()
    chat.answer('Ada')
    chat.answer('')
    chat.answer('ada@example.com')
    chat.answer('123456')
    chat.answer('no-ai')
    chat.answer('manual-triage')
    chat.answer('manual-deploys')
    chat.answer('none')
    chat.answer('none')
    chat.answer('')
    chat.answer('true')

    expect(chat.buildReportRequest().site_url).toBeNull()
  })

  it('records consent granularly, as the backend models it', () => {
    const chat = createContactChat()
    answerAll(chat)

    expect(chat.buildReportRequest().consent).toEqual({
      privacy_accepted: true,
      report_accepted: true,
    })
  })

  it('includes the transcript so the delivered email is a complete record', () => {
    const chat = createContactChat()
    answerAll(chat)

    const transcript = chat.buildReportRequest().transcript
    expect(transcript[0]).toEqual({ step_id: 'name', answer: 'Ada Lovelace' })
    // 11 steps minus the email and the verification code, which never travel.
    expect(transcript).toHaveLength(9)
    expect(transcript.map((entry) => entry.step_id)).not.toContain('email')
    expect(transcript.map((entry) => entry.step_id)).not.toContain('code')
  })

  it('matches the shared contract fixture field for field', async () => {
    const fixture = (await import('../../tests/contracts/report-request.json')).default
    const chat = createContactChat()
    answerAll(chat)

    const payload = chat.buildReportRequest() as unknown as Record<string, unknown>
    const expectedKeys = Object.keys(fixture).filter((key) => !key.startsWith('_'))

    expect(Object.keys(payload).sort()).toEqual(expectedKeys.sort())
  })
})
