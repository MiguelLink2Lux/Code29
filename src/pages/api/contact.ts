import type { APIRoute } from 'astro'
import {
  buildContactEmailText,
  coerceContactFormData,
  hasContactValidationErrors,
  validateContactForm,
} from '@/utils/contact'

function json(body: Record<string, unknown>, status: number): Response {
  return new Response(JSON.stringify(body), {
    status,
    headers: {
      'Content-Type': 'application/json; charset=utf-8',
    },
  })
}

function getRequiredEnv(name: 'RESEND_API_KEY' | 'CONTACT_TO_EMAIL' | 'CONTACT_FROM_EMAIL'): string {
  const value = import.meta.env[name]

  if (!value) {
    throw new Error(`Missing required environment variable: ${name}`)
  }

  return value
}

export const POST: APIRoute = async ({ request }) => {
  if (!request.headers.get('content-type')?.includes('application/json')) {
    return json({ error: 'Unsupported content type.' }, 415)
  }

  let body: unknown

  try {
    body = await request.json()
  } catch {
    return json({ error: 'Invalid JSON payload.' }, 400)
  }

  const payload = coerceContactFormData(body)

  if (!payload) {
    return json({ error: 'Invalid request body.' }, 400)
  }

  const validationErrors = validateContactForm(payload)

  if (hasContactValidationErrors(validationErrors)) {
    return json({ error: 'Invalid contact form payload.', fields: validationErrors }, 400)
  }

  let resendApiKey: string
  let contactToEmail: string
  let contactFromEmail: string

  try {
    resendApiKey = getRequiredEnv('RESEND_API_KEY')
    contactToEmail = getRequiredEnv('CONTACT_TO_EMAIL')
    contactFromEmail = getRequiredEnv('CONTACT_FROM_EMAIL')
  } catch (error) {
    return json(
      {
        error:
          error instanceof Error ? error.message : 'Contact email service is not configured.',
      },
      503,
    )
  }

  const resendResponse = await fetch('https://api.resend.com/emails', {
    method: 'POST',
    headers: {
      Authorization: `Bearer ${resendApiKey}`,
      'Content-Type': 'application/json',
    },
    body: JSON.stringify({
      from: contactFromEmail,
      to: [contactToEmail],
      reply_to: payload.email,
      subject: `New contact request from ${payload.fullName}`,
      text: buildContactEmailText(payload),
    }),
  })

  if (!resendResponse.ok) {
    const resendBody = await resendResponse.text()

    return json(
      {
        error: `Resend request failed with status ${resendResponse.status}.`,
        details: resendBody,
      },
      502,
    )
  }

  return json({ ok: true }, 200)
}
