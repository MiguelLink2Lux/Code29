import { afterEach, beforeEach, describe, expect, it, vi } from 'vitest'

import { createTurnstileClient, TurnstileNotConfigured } from '@/utils/turnstile-client'

/**
 * A stand-in for the script Cloudflare injects. `render` hands back a widget id
 * and keeps the callbacks, so a test can decide when the challenge resolves —
 * which is the only way to assert what happens *after* it does.
 */
function fakeTurnstile() {
  const rendered: {
    container: HTMLElement
    options: { callback: (token: string) => void; 'error-callback': () => void }
  }[] = []
  let nextId = 0

  return {
    rendered,
    removed: [] as string[],
    render(container: HTMLElement, options: never) {
      rendered.push({ container, options })
      return `widget-${nextId++}`
    },
    remove(widgetId: string) {
      this.removed.push(widgetId)
    },
  }
}

let stub: ReturnType<typeof fakeTurnstile>

beforeEach(() => {
  stub = fakeTurnstile()
  window.turnstile = stub as never
})

afterEach(() => {
  delete window.turnstile
  document.body.innerHTML = ''
  vi.restoreAllMocks()
})

describe('createTurnstileClient', () => {
  it('refuses without a site key instead of loading the script', async () => {
    await expect(createTurnstileClient('').getToken(document.createElement('div'))).rejects.toBeInstanceOf(
      TurnstileNotConfigured,
    )

    expect(stub.rendered).toHaveLength(0)
  })

  it('renders into the container it was given', async () => {
    const host = document.createElement('div')
    document.body.appendChild(host)

    const pending = createTurnstileClient('site-key').getToken(host)
    await vi.waitFor(() => expect(stub.rendered).toHaveLength(1))

    // The regression: a container outside the document makes Cloudflare log
    // "Cannot find Widget …" and leaves an interactive challenge unreachable.
    expect(stub.rendered[0].container).toBe(host)
    expect(stub.rendered[0].container.isConnected).toBe(true)

    stub.rendered[0].options.callback('token')
    await expect(pending).resolves.toBe('token')

    // Drained before the test ends: the teardown is deferred, and a pending one
    // would fire against the next test's stub.
    await vi.waitFor(() => expect(stub.removed).toEqual(['widget-0']))
  })

  it('destroys the widget once the challenge is solved', async () => {
    const host = document.createElement('div')
    document.body.appendChild(host)

    const pending = createTurnstileClient('site-key').getToken(host)
    await vi.waitFor(() => expect(stub.rendered).toHaveLength(1))
    stub.rendered[0].options.callback('token')
    await pending

    // Deferred on purpose: the widget is torn down after the promise settles,
    // never on the path to settling it.
    await vi.waitFor(() => expect(stub.removed).toEqual(['widget-0']))
  })

  it('destroys the widget when the challenge fails', async () => {
    const host = document.createElement('div')
    document.body.appendChild(host)

    const pending = createTurnstileClient('site-key').getToken(host)
    await vi.waitFor(() => expect(stub.rendered).toHaveLength(1))
    stub.rendered[0].options['error-callback']()

    await expect(pending).rejects.toThrow(/challenge failed/i)
    await vi.waitFor(() => expect(stub.removed).toEqual(['widget-0']))
  })

  it('leaves no widget behind when the visitor retries', async () => {
    const host = document.createElement('div')
    document.body.appendChild(host)
    const client = createTurnstileClient('site-key')

    const first = client.getToken(host)
    await vi.waitFor(() => expect(stub.rendered).toHaveLength(1))
    stub.rendered[0].options['error-callback']()
    await expect(first).rejects.toThrow()

    const second = client.getToken(host)
    await vi.waitFor(() => expect(stub.rendered).toHaveLength(2))
    stub.rendered[1].options.callback('token')
    await expect(second).resolves.toBe('token')

    // Two challenges, two teardowns: without this a retry piles orphaned
    // widgets into the same container.
    await vi.waitFor(() => expect(stub.removed).toEqual(['widget-0', 'widget-1']))
  })
})
