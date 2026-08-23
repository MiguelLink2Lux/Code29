import { fireEvent, render, screen, waitFor } from '@testing-library/vue'
import { beforeEach, describe, expect, it, vi } from 'vitest'

import ContactConversation from '@/components/contact/ContactConversation.vue'
import { ContactApiError } from '@/utils/contact-api'

/**
 * The conversational island. What separates it from the questionnaire it
 * replaces: a message thread instead of one step at a time, free text instead of
 * closed options, and no step counter — the server decides when it is done.
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

const stubTurnstile = () => ({ getToken: vi.fn().mockResolvedValue('turnstile-token') })

function mount(api = stubApi(), turnstile = stubTurnstile()) {
  return { api, turnstile, ...render(ContactConversation, { props: { api, turnstile } }) }
}

/**
 * The composer, addressed by id rather than by role: once verification is asked
 * for, the email field is a textbox too, and an ambiguous query would pick the
 * wrong one.
 */
const composer = () => document.getElementById('conversation-input') as HTMLInputElement

async function say(text: string) {
  const input = composer()
  await fireEvent.update(input, text)
  await fireEvent.submit(input.closest('form')!)
}

beforeEach(() => {
  sessionStorage.clear()
})

describe('the thread', () => {
  it('opens with an invitation, not a question counter', () => {
    mount()

    expect(screen.queryByText(/paso \d+ de \d+/i)).toBeNull()
    expect(composer()).toBeTruthy()
  })

  it('shows what the visitor said and what the bot answered', async () => {
    const { api } = mount()

    await say('hola')

    await waitFor(() => expect(api.takeConversationTurn).toHaveBeenCalled())
    expect(screen.getByText('hola')).toBeTruthy()
    await waitFor(() => expect(screen.getByText(/en qué empresa/i)).toBeTruthy())
  })

  it('clears the input after sending, so the next message starts empty', async () => {
    mount()

    await say('hola')

    await waitFor(() => expect(composer().value).toBe(''))
  })

  it('accepts free text: there are no option buttons to pick from', async () => {
    mount()

    await say('somos tres personas y desplegamos a mano los viernes')

    expect(screen.queryAllByRole('radio')).toHaveLength(0)
  })

  it('announces new bot messages to assistive technology', async () => {
    mount()

    await say('hola')

    await waitFor(() => expect(screen.getByRole('log')).toBeTruthy())
  })
})

describe('failure states never look like success', () => {
  it('surfaces a model failure and keeps the message on screen', async () => {
    const api = stubApi({
      takeConversationTurn: vi.fn().mockRejectedValue(new ContactApiError('down', 502)),
    })
    mount(api)

    await say('hola')

    await waitFor(() => expect(screen.getByRole('alert')).toBeTruthy())
    expect(screen.getByText('hola')).toBeTruthy()
    expect(screen.queryByRole('status')).toBeNull()
  })

  it('reads an unconfigured backend as unavailable, not as the visitor’s fault', async () => {
    const api = stubApi({
      takeConversationTurn: vi.fn().mockRejectedValue(new ContactApiError('nope', 503)),
    })
    mount(api)

    await say('hola')

    await waitFor(() =>
      expect(screen.getByRole('alert').textContent).toMatch(/no está disponible|unavailable/i),
    )
  })

  it('tells the visitor an expired conversation can simply be restarted', async () => {
    const api = stubApi({
      takeConversationTurn: vi.fn().mockRejectedValue(new ContactApiError('stale', 401)),
    })
    mount(api)

    await say('hola')

    await waitFor(() =>
      expect(screen.getByRole('alert').textContent).toMatch(/caducado|expired|de nuevo|again/i),
    )
  })

  it('refuses an over-long message without calling the backend', async () => {
    const { api } = mount()

    await say('x'.repeat(1001))

    expect(api.takeConversationTurn).not.toHaveBeenCalled()
    await waitFor(() => expect(screen.getByRole('alert')).toBeTruthy())
  })
})

describe('email verification, inside the conversation', () => {
  it('asks for the address when the server says it is missing', async () => {
    mount()

    await say('hola')

    await waitFor(() => expect(screen.getByLabelText(/email|correo/i)).toBeTruthy())
  })

  it('solves the human challenge before asking the backend for a code', async () => {
    const { api, turnstile } = mount()
    await say('hola')

    const emailInput = await waitFor(() => screen.getByLabelText(/email|correo/i))
    await fireEvent.update(emailInput, 'ada@example.com')
    await fireEvent.click(screen.getByRole('button', { name: /verificar|verify|enviar código/i }))

    await waitFor(() => expect(turnstile.getToken).toHaveBeenCalled())
    expect(api.requestVerificationCode).toHaveBeenCalledWith('ada@example.com', 'turnstile-token')
  })

  it('a missing Turnstile key reads as unavailable, not as a human failure', async () => {
    const { TurnstileNotConfigured } = await import('@/utils/turnstile-client')
    const turnstile = { getToken: vi.fn().mockRejectedValue(new TurnstileNotConfigured()) }
    mount(stubApi(), turnstile)
    await say('hola')

    const emailInput = await waitFor(() => screen.getByLabelText(/email|correo/i))
    await fireEvent.update(emailInput, 'ada@example.com')
    await fireEvent.click(screen.getByRole('button', { name: /verificar|verify|enviar código/i }))

    await waitFor(() =>
      expect(screen.getByRole('alert').textContent).toMatch(/no está disponible|unavailable/i),
    )
  })

  it('confirms the code and stops asking for the address', async () => {
    const { api } = mount()
    await say('hola')

    const emailInput = await waitFor(() => screen.getByLabelText(/email|correo/i))
    await fireEvent.update(emailInput, 'ada@example.com')
    await fireEvent.click(screen.getByRole('button', { name: /verificar|verify|enviar código/i }))

    const codeInput = await waitFor(() => screen.getByLabelText(/código|code/i))
    await fireEvent.update(codeInput, '123456')
    await fireEvent.click(screen.getByRole('button', { name: /confirmar|confirm/i }))

    await waitFor(() =>
      expect(api.confirmVerificationCode).toHaveBeenCalledWith('ada@example.com', '123456'),
    )
  })

  it('a rejected code keeps the visitor unverified with an actionable message', async () => {
    const api = stubApi({
      confirmVerificationCode: vi.fn().mockRejectedValue(new ContactApiError('bad', 400)),
    })
    mount(api)
    await say('hola')

    const emailInput = await waitFor(() => screen.getByLabelText(/email|correo/i))
    await fireEvent.update(emailInput, 'ada@example.com')
    await fireEvent.click(screen.getByRole('button', { name: /verificar|verify|enviar código/i }))

    const codeInput = await waitFor(() => screen.getByLabelText(/código|code/i))
    await fireEvent.update(codeInput, '000000')
    await fireEvent.click(screen.getByRole('button', { name: /confirmar|confirm/i }))

    await waitFor(() =>
      expect(screen.getByRole('alert').textContent).toMatch(/no es válido|not valid/i),
    )
  })
})

describe('closing the conversation', () => {
  it('confirms completion when the server says the conversation is complete', async () => {
    const api = stubApi({
      takeConversationTurn: vi.fn().mockResolvedValue(turn({ complete: true, missing: [] })),
    })
    mount(api)

    await say('ya está')

    await waitFor(() => expect(screen.getByRole('status')).toBeTruthy())
  })

  it('a spent budget closes the conversation without looking like an error', async () => {
    const api = stubApi({
      takeConversationTurn: vi
        .fn()
        .mockResolvedValue(turn({ complete: true, exhausted: true, missing: [] })),
    })
    mount(api)

    await say('sigo hablando')

    await waitFor(() => expect(screen.getByRole('status')).toBeTruthy())
    expect(screen.queryByRole('alert')).toBeNull()
  })

  it('stops accepting messages once the conversation is closed', async () => {
    const api = stubApi({
      takeConversationTurn: vi.fn().mockResolvedValue(turn({ complete: true, missing: [] })),
    })
    mount(api)

    await say('ya está')

    await waitFor(() => expect(composer()).toBeNull())
  })
})
