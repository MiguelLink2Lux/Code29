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

describe('requestReport', () => {
  it('sends the access token as a bearer credential, not in the body', async () => {
    const fetchSpy = vi.fn().mockResolvedValue(json({ status: 'sent' }, 202))
    const api = createContactApi({ baseUrl: 'https://api.test', fetchImpl: fetchSpy })

    await api.requestReport({ consent: true } as never, 'token-abc')

    const [, init] = fetchSpy.mock.calls[0]
    expect(init.headers.Authorization).toBe('Bearer token-abc')
    expect(init.body).not.toContain('token-abc')
  })

  it('treats an expired token as a distinct, recoverable failure', async () => {
    const api = createContactApi({
      baseUrl: 'https://api.test',
      fetchImpl: vi.fn().mockResolvedValue(json({ detail: 'invalid token' }, 401)),
    })

    await expect(api.requestReport({ consent: true } as never, 'stale')).rejects.toMatchObject({
      status: 401,
    })
  })
})
