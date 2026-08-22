import { fireEvent, render, screen, waitFor } from '@testing-library/vue'
import { beforeEach, describe, expect, it, vi } from 'vitest'

import ContactChat from '@/components/contact/ContactChat.vue'
import { ContactApiError } from '@/utils/contact-api'

function stubApi(overrides: Record<string, unknown> = {}) {
  return {
    requestVerificationCode: vi.fn().mockResolvedValue(undefined),
    confirmVerificationCode: vi.fn().mockResolvedValue('token-abc'),
    requestReport: vi.fn().mockResolvedValue(undefined),
    ...overrides,
  }
}

const stubTurnstile = () => ({ getToken: vi.fn().mockResolvedValue('turnstile-token') })

function mount(api = stubApi(), turnstile = stubTurnstile()) {
  return { api, turnstile, ...render(ContactChat, { props: { api, turnstile } }) }
}

/** Types a value into the visible input and submits the step. */
async function fill(value: string) {
  const input = screen.getByRole('textbox')
  await fireEvent.update(input, value)
  await fireEvent.click(screen.getByRole('button', { name: /continuar|continue/i }))
}

async function choose(index = 0) {
  const options = screen.getAllByRole('radio')
  await fireEvent.click(options[index])
  await fireEvent.click(screen.getByRole('button', { name: /continuar|continue/i }))
}

beforeEach(() => {
  sessionStorage.clear()
})

describe('rendering', () => {
  it('starts on the first question', () => {
    mount()
    expect(screen.getByText(/cómo te llamas/i)).toBeTruthy()
  })

  it('shows progress', () => {
    mount()
    expect(screen.getByText(/1.*11/)).toBeTruthy()
  })
})

describe('validation', () => {
  it('keeps the visitor on the step and explains why', async () => {
    mount()
    await fill('')

    expect(screen.getByRole('alert').textContent).toMatch(/obligatorio|required/i)
    expect(screen.getByText(/cómo te llamas/i)).toBeTruthy()
  })

  it('rejects a malformed email before calling the backend', async () => {
    const { api } = mount()
    await fill('Ada')
    await fill('')
    await fill('not-an-email')

    expect(api.requestVerificationCode).not.toHaveBeenCalled()
    expect(screen.getByRole('alert').textContent).toMatch(/no parece válido|does not look valid/i)
  })
})

describe('email verification', () => {
  async function reachCodeStep(api = stubApi(), turnstile = stubTurnstile()) {
    const mounted = mount(api, turnstile)
    await fill('Ada Lovelace')
    await fill('Analytical Engines')
    await fill('ada@example.com')
    return mounted
  }

  it('solves the human challenge before asking for a code', async () => {
    const { api, turnstile } = await reachCodeStep()

    await waitFor(() => expect(turnstile.getToken).toHaveBeenCalled())
    expect(api.requestVerificationCode).toHaveBeenCalledWith('ada@example.com', 'turnstile-token')
  })

  it('exchanges the code for a token and moves on', async () => {
    const { api } = await reachCodeStep()
    await waitFor(() => expect(api.requestVerificationCode).toHaveBeenCalled())

    await fill('123456')

    await waitFor(() =>
      expect(api.confirmVerificationCode).toHaveBeenCalledWith('ada@example.com', '123456'),
    )
    expect(screen.getByText(/cómo usáis la ia|how do you use ai/i)).toBeTruthy()
  })

  it('keeps the visitor on the code step when the backend rejects it', async () => {
    const api = stubApi({
      confirmVerificationCode: vi.fn().mockRejectedValue(new ContactApiError('bad code', 400)),
    })
    await reachCodeStep(api)

    await fill('123456')

    await waitFor(() =>
      expect(screen.getByRole('alert').textContent).toMatch(/no es válido|not valid/i),
    )
  })

  it('reports a failed human check without pretending the code was sent', async () => {
    const api = stubApi({
      requestVerificationCode: vi
        .fn()
        .mockRejectedValue(new ContactApiError('human verification failed', 403)),
    })
    await reachCodeStep(api)

    await waitFor(() =>
      expect(screen.getByRole('alert').textContent).toMatch(/persona|person/i),
    )
  })

  it('reports an unconfigured backend as unavailable, not as the visitor’s mistake', async () => {
    const api = stubApi({
      requestVerificationCode: vi
        .fn()
        .mockRejectedValue(new ContactApiError('not configured', 503)),
    })
    await reachCodeStep(api)

    await waitFor(() =>
      expect(screen.getByRole('alert').textContent).toMatch(/no está disponible|unavailable/i),
    )
  })
})

describe('report delivery', () => {
  async function completeFlow(api = stubApi()) {
    const mounted = mount(api)
    await fill('Ada Lovelace')
    await fill('Analytical Engines')
    await fill('ada@example.com')
    await waitFor(() => expect(api.requestVerificationCode).toHaveBeenCalled())
    await fill('123456')
    await waitFor(() => expect(api.confirmVerificationCode).toHaveBeenCalled())
    await choose()
    await choose()
    await choose()
    await choose()
    await choose()
    await fill('example.com')
    await fireEvent.click(screen.getByRole('checkbox'))
    await fireEvent.click(screen.getByRole('button', { name: /continuar|continue/i }))
    return mounted
  }

  it('sends the report with the access token and confirms it', async () => {
    const { api } = await completeFlow()

    await waitFor(() => expect(api.requestReport).toHaveBeenCalled())
    const [payload, token] = api.requestReport.mock.calls[0]
    expect(token).toBe('token-abc')
    expect(payload.consent.privacy_accepted).toBe(true)
    expect(payload.workflow.practices).toBeInstanceOf(Array)
    expect(payload.contact_name).toBe('Ada Lovelace')
    // Neither the address nor the code may appear anywhere in the payload.
    expect(JSON.stringify(payload)).not.toContain('ada@example.com')
    expect(JSON.stringify(payload)).not.toContain('123456')

    await waitFor(() => expect(screen.getByText(/informe en camino|report on its way/i)).toBeTruthy())
  })

  it('surfaces a delivery failure instead of claiming success', async () => {
    const api = stubApi({
      requestReport: vi.fn().mockRejectedValue(new ContactApiError('resend down', 502)),
    })
    await completeFlow(api)

    await waitFor(() => expect(screen.getByRole('alert')).toBeTruthy())
    expect(screen.queryByText(/informe en camino|report on its way/i)).toBeNull()
  })
})
