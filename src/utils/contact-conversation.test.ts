import { beforeEach, describe, expect, it, vi } from 'vitest'

import { ContactApiError } from '@/utils/contact-api'
import { createConversation, MAX_MESSAGE_LENGTH } from '@/utils/contact-conversation'

/**
 * The conversational state, framework-free so it can be reasoned about without
 * mounting a component.
 *
 * Two privacy rules are enforced here rather than trusted to the component: the
 * transcript lives in sessionStorage so lead data dies with the tab, and the
 * access token is never persisted — it proves email ownership and belongs in
 * memory only.
 */

const turn = (overrides: Record<string, unknown> = {}) => ({
  reply: '¿En qué empresa trabajas?',
  envelope: 'envelope-1',
  complete: false,
  exhausted: false,
  missing: ['company', 'website', 'team', 'email'],
  ...overrides,
})

function stubApi(overrides: Record<string, unknown> = {}) {
  return {
    takeConversationTurn: vi.fn().mockResolvedValue(turn()),
    requestVerificationCode: vi.fn().mockResolvedValue(undefined),
    confirmVerificationCode: vi.fn().mockResolvedValue('token-abc'),
    requestReport: vi.fn().mockResolvedValue(undefined),
    ...overrides,
  }
}

beforeEach(() => {
  sessionStorage.clear()
})

describe('sending a message', () => {
  it('shows the visitor message immediately, before the answer arrives', async () => {
    const api = stubApi()
    const chat = createConversation({ api })

    const pending = chat.send('hola')

    expect(chat.state.messages.at(-1)).toEqual({ role: 'visitor', text: 'hola' })
    await pending
  })

  it('appends the bot reply after the call', async () => {
    const chat = createConversation({ api: stubApi() })

    await chat.send('hola')

    expect(chat.state.messages.map((m) => m.role)).toEqual(['visitor', 'bot'])
    expect(chat.state.messages.at(-1)?.text).toBe('¿En qué empresa trabajas?')
  })

  it('carries the envelope from one turn into the next', async () => {
    const api = stubApi()
    const chat = createConversation({ api })

    await chat.send('hola')
    await chat.send('Analytical Engines')

    expect(api.takeConversationTurn).toHaveBeenLastCalledWith(
      'Analytical Engines',
      'envelope-1',
      undefined,
    )
  })

  it('tracks what the conversation still needs', async () => {
    const chat = createConversation({ api: stubApi() })

    await chat.send('hola')

    expect(chat.state.missing).toContain('email')
  })

  it('reports busy while a turn is in flight', async () => {
    let release: (value: unknown) => void = () => {}
    const api = stubApi({
      takeConversationTurn: vi.fn().mockReturnValue(new Promise((r) => (release = r))),
    })
    const chat = createConversation({ api })

    const pending = chat.send('hola')
    expect(chat.state.busy).toBe(true)

    release(turn())
    await pending
    expect(chat.state.busy).toBe(false)
  })

  it('ignores a second send while one is in flight', async () => {
    let release: (value: unknown) => void = () => {}
    const api = stubApi({
      takeConversationTurn: vi.fn().mockReturnValue(new Promise((r) => (release = r))),
    })
    const chat = createConversation({ api })

    const first = chat.send('hola')
    await chat.send('otra vez')

    expect(api.takeConversationTurn).toHaveBeenCalledTimes(1)
    release(turn())
    await first
  })

  it('refuses an empty message without calling the backend', async () => {
    const api = stubApi()
    const chat = createConversation({ api })

    await chat.send('   ')

    expect(api.takeConversationTurn).not.toHaveBeenCalled()
  })

  it('refuses an over-long message locally instead of paying for a 413', async () => {
    const api = stubApi()
    const chat = createConversation({ api })

    await chat.send('x'.repeat(MAX_MESSAGE_LENGTH + 1))

    expect(api.takeConversationTurn).not.toHaveBeenCalled()
    expect(chat.state.error).toBe('tooLong')
  })
})

describe('completion', () => {
  it('is not complete until the server says so', async () => {
    const chat = createConversation({ api: stubApi() })

    await chat.send('hola')

    expect(chat.state.complete).toBe(false)
  })

  it('trusts the server, never its own count of facts', async () => {
    const api = stubApi({
      takeConversationTurn: vi.fn().mockResolvedValue(turn({ complete: true, missing: [] })),
    })
    const chat = createConversation({ api })

    await chat.send('listo')

    expect(chat.state.complete).toBe(true)
  })

  it('surfaces an exhausted budget as a closed conversation, not an error', async () => {
    const api = stubApi({
      takeConversationTurn: vi
        .fn()
        .mockResolvedValue(turn({ complete: true, exhausted: true, missing: ['email'] })),
    })
    const chat = createConversation({ api })

    await chat.send('sigo hablando')

    expect(chat.state.exhausted).toBe(true)
    expect(chat.state.error).toBeNull()
  })
})

describe('failures produce actionable states', () => {
  const cases: Array<[number, string]> = [
    [401, 'expired'],
    [413, 'tooLong'],
    [502, 'retry'],
    [503, 'unavailable'],
    [0, 'network'],
  ]

  for (const [status, expected] of cases) {
    it(`maps ${status} to "${expected}"`, async () => {
      const api = stubApi({
        takeConversationTurn: vi.fn().mockRejectedValue(new ContactApiError('boom', status)),
      })
      const chat = createConversation({ api })

      await chat.send('hola')

      expect(chat.state.error).toBe(expected)
    })
  }

  it('keeps the visitor message on screen when the turn fails', async () => {
    // Losing what they typed on top of an error is twice the insult.
    const api = stubApi({
      takeConversationTurn: vi.fn().mockRejectedValue(new ContactApiError('boom', 502)),
    })
    const chat = createConversation({ api })

    await chat.send('mi mensaje')

    expect(chat.state.messages.at(-1)).toEqual({ role: 'visitor', text: 'mi mensaje' })
  })

  it('clears the error on the next successful turn', async () => {
    const api = stubApi({
      takeConversationTurn: vi
        .fn()
        .mockRejectedValueOnce(new ContactApiError('boom', 502))
        .mockResolvedValue(turn()),
    })
    const chat = createConversation({ api })

    await chat.send('primero')
    await chat.send('segundo')

    expect(chat.state.error).toBeNull()
  })

  it('an expired conversation drops the envelope so the next turn starts clean', async () => {
    const api = stubApi({
      takeConversationTurn: vi
        .fn()
        .mockResolvedValueOnce(turn())
        .mockRejectedValueOnce(new ContactApiError('stale', 401))
        .mockResolvedValue(turn()),
    })
    const chat = createConversation({ api })

    await chat.send('hola')
    await chat.send('sigo')
    await chat.send('otra vez')

    expect(api.takeConversationTurn).toHaveBeenLastCalledWith('otra vez', undefined, undefined)
  })
})

describe('email verification', () => {
  it('asks the backend for a code and remembers the pending address', async () => {
    const api = stubApi()
    const chat = createConversation({ api })

    await chat.requestCode('ada@example.com', 'turnstile-token')

    expect(api.requestVerificationCode).toHaveBeenCalledWith('ada@example.com', 'turnstile-token')
    expect(chat.state.pendingEmail).toBe('ada@example.com')
  })

  it('rejects an invalid address before calling the backend', async () => {
    const api = stubApi()
    const chat = createConversation({ api })

    await chat.requestCode('not-an-email', 'turnstile-token')

    expect(api.requestVerificationCode).not.toHaveBeenCalled()
    expect(chat.state.error).toBe('invalidEmail')
  })

  it('exchanges the code for a token held in memory only', async () => {
    const api = stubApi()
    const chat = createConversation({ api })

    await chat.requestCode('ada@example.com', 't')
    await chat.confirmCode('123456')

    expect(chat.state.emailVerified).toBe(true)
    expect(sessionStorage.getItem('contact-conversation')).not.toContain('token-abc')
  })

  it('sends the token on the next turn once verified', async () => {
    const api = stubApi()
    const chat = createConversation({ api })

    await chat.send('hola')
    await chat.requestCode('ada@example.com', 't')
    await chat.confirmCode('123456')
    await chat.send('listo')

    expect(api.takeConversationTurn).toHaveBeenLastCalledWith(
      'listo',
      'envelope-1',
      'token-abc',
    )
  })

  it('a rejected code leaves the visitor unverified with an actionable error', async () => {
    const api = stubApi({
      confirmVerificationCode: vi.fn().mockRejectedValue(new ContactApiError('bad', 400)),
    })
    const chat = createConversation({ api })

    await chat.requestCode('ada@example.com', 't')
    await chat.confirmCode('000000')

    expect(chat.state.emailVerified).toBe(false)
    expect(chat.state.error).toBe('codeRejected')
  })

  it('a failed human check is not the visitor being wrong about their email', async () => {
    const api = stubApi({
      requestVerificationCode: vi.fn().mockRejectedValue(new ContactApiError('human', 403)),
    })
    const chat = createConversation({ api })

    await chat.requestCode('ada@example.com', 't')

    expect(chat.state.error).toBe('humanCheck')
  })
})

describe('persistence', () => {
  it('survives a reload within the same tab', async () => {
    const first = createConversation({ api: stubApi() })
    await first.send('hola')

    const restored = createConversation({ api: stubApi() })

    expect(restored.state.messages).toHaveLength(2)
    expect(restored.state.envelope).toBe('envelope-1')
  })

  it('uses sessionStorage, so lead data dies with the tab', async () => {
    const chat = createConversation({ api: stubApi() })

    await chat.send('hola')

    expect(sessionStorage.getItem('contact-conversation')).not.toBeNull()
    expect(localStorage.getItem('contact-conversation')).toBeNull()
  })

  it('never persists the access token', async () => {
    const chat = createConversation({ api: stubApi() })

    await chat.send('hola')
    await chat.requestCode('ada@example.com', 't')
    await chat.confirmCode('123456')

    const stored = sessionStorage.getItem('contact-conversation') ?? ''
    expect(stored).not.toContain('token-abc')
    expect(stored).not.toContain('ada@example.com')
  })

  it('starts clean when the stored payload is corrupted', () => {
    sessionStorage.setItem('contact-conversation', '{ not json')

    expect(createConversation({ api: stubApi() }).state.messages).toEqual([])
  })

  it('starts clean when storage is unavailable', () => {
    vi.spyOn(Storage.prototype, 'getItem').mockImplementation(() => {
      throw new Error('denied')
    })

    expect(() => createConversation({ api: stubApi() })).not.toThrow()

    vi.restoreAllMocks()
  })

  it('clears everything on reset', async () => {
    const chat = createConversation({ api: stubApi() })
    await chat.send('hola')

    chat.reset()

    expect(chat.state.messages).toEqual([])
    expect(chat.state.envelope).toBeUndefined()
    expect(sessionStorage.getItem('contact-conversation')).toBeNull()
  })
})
