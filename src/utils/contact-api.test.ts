import { afterEach, describe, expect, it, vi } from 'vitest'

import { ContactApiError, createContactApi, resolveApiBaseUrl } from '@/utils/contact-api'

const json = (body: unknown, status = 200) =>
  new Response(JSON.stringify(body), {
    status,
    headers: { 'Content-Type': 'application/json' },
  })

afterEach(() => {
  vi.restoreAllMocks()
})

describe('resolveApiBaseUrl', () => {
  it('uses PUBLIC_API_BASE_URL when set', () => {
    expect(resolveApiBaseUrl({ PUBLIC_API_BASE_URL: 'https://api.code29.dev' })).toBe(
      'https://api.code29.dev',
    )
  })

  it('strips a trailing slash so joins never double up', () => {
    expect(resolveApiBaseUrl({ PUBLIC_API_BASE_URL: 'https://api.code29.dev/' })).toBe(
      'https://api.code29.dev',
    )
  })

  it('falls back to the local backend during development', () => {
    expect(resolveApiBaseUrl({})).toBe('http://localhost:8000')
  })

  it('rejects a scheme-less value instead of building broken URLs', () => {
    expect(() => resolveApiBaseUrl({ PUBLIC_API_BASE_URL: 'api.code29.dev' })).toThrow(/absolute/i)
  })
})

describe('requestVerificationCode', () => {
  it('posts the address and the Turnstile token', async () => {
    const fetchSpy = vi.fn().mockResolvedValue(json({ status: 'sent' }, 202))
    const api = createContactApi({ baseUrl: 'https://api.test', fetchImpl: fetchSpy })

    await api.requestVerificationCode('ada@example.com', 'turnstile-token')

    const [url, init] = fetchSpy.mock.calls[0]
    expect(url).toBe('https://api.test/api/v1/contact/verification/request')
    expect(JSON.parse(init.body)).toEqual({
      email: 'ada@example.com',
      turnstileToken: 'turnstile-token',
    })
  })

  it('surfaces a failed human check as a typed error', async () => {
    const api = createContactApi({
      baseUrl: 'https://api.test',
      fetchImpl: vi.fn().mockResolvedValue(json({ detail: 'Human verification failed.' }, 403)),
    })

    await expect(api.requestVerificationCode('ada@example.com', 't')).rejects.toMatchObject({
      name: 'ContactApiError',
      status: 403,
    })
  })

  it('surfaces an unconfigured backend as 503 rather than a generic failure', async () => {
    const api = createContactApi({
      baseUrl: 'https://api.test',
      fetchImpl: vi.fn().mockResolvedValue(json({ detail: 'not configured' }, 503)),
    })

    await expect(api.requestVerificationCode('ada@example.com', 't')).rejects.toMatchObject({
      status: 503,
    })
  })

  it('turns a network failure into ContactApiError, never a raw TypeError', async () => {
    const api = createContactApi({
      baseUrl: 'https://api.test',
      fetchImpl: vi.fn().mockRejectedValue(new TypeError('Failed to fetch')),
    })

    await expect(api.requestVerificationCode('ada@example.com', 't')).rejects.toBeInstanceOf(
      ContactApiError,
    )
  })
})

describe('confirmVerificationCode', () => {
  it('returns the access token', async () => {
    const api = createContactApi({
      baseUrl: 'https://api.test',
      fetchImpl: vi.fn().mockResolvedValue(json({ accessToken: 'token-abc' })),
    })

    expect(await api.confirmVerificationCode('ada@example.com', '123456')).toBe('token-abc')
  })

  it('rejects when the backend answers without a token', async () => {
    const api = createContactApi({
      baseUrl: 'https://api.test',
      fetchImpl: vi.fn().mockResolvedValue(json({})),
    })

    await expect(api.confirmVerificationCode('ada@example.com', '123456')).rejects.toBeInstanceOf(
      ContactApiError,
    )
  })
})

describe('requestConversationReport', () => {
  const json = (body: unknown, status = 200) =>
    new Response(JSON.stringify(body), {
      status,
      headers: { 'Content-Type': 'application/json' },
    })

  it('sends the envelope and the consent, with the token as a credential', async () => {
    const fetchSpy = vi.fn().mockResolvedValue(json({ delivered: true }))
    const api = createContactApi({ baseUrl: 'https://api.test', fetchImpl: fetchSpy })

    await api.requestConversationReport('signed-envelope', 'token-abc')

    const [url, init] = fetchSpy.mock.calls[0]
    expect(url).toBe('https://api.test/api/v1/contact/report')
    expect(init.headers.Authorization).toBe('Bearer token-abc')

    const body = JSON.parse(init.body)
    expect(body.envelope).toBe('signed-envelope')
    // The facts come from the envelope; nothing about the lead travels loose.
    expect(body.contact_name).toBeUndefined()
    expect(body.company).toBeUndefined()
    expect(body.consent).toEqual({ privacy_accepted: true, report_accepted: true })
    expect(init.body).not.toContain('token-abc')
  })

  it('surfaces an expired conversation as 401 so the UI can restart it', async () => {
    const api = createContactApi({
      baseUrl: 'https://api.test',
      fetchImpl: vi.fn().mockResolvedValue(json({ detail: 'no longer valid' }, 401)),
    })

    await expect(
      api.requestConversationReport('stale', 'token-abc'),
    ).rejects.toMatchObject({ status: 401 })
  })

  it('surfaces a delivery failure rather than reporting success', async () => {
    const api = createContactApi({
      baseUrl: 'https://api.test',
      fetchImpl: vi.fn().mockResolvedValue(json({ detail: 'resend down' }, 502)),
    })

    await expect(
      api.requestConversationReport('envelope', 'token-abc'),
    ).rejects.toMatchObject({ status: 502 })
  })
})
