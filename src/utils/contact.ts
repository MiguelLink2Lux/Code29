export interface ContactFormData {
  fullName: string
  company: string
  email: string
  message: string
  website: string
}

export interface ContactSubmissionPayload {
  fullName: string
  company: string
  email: string
  message: string
  website?: string
}

export type ContactValidationCode = 'required' | 'invalidEmail' | 'tooLong' | 'spam'

export type ContactValidationErrors = Partial<
  Record<keyof ContactFormData, ContactValidationCode>
>

export class ContactSubmissionError extends Error {
  constructor(
    message: string,
    public readonly status: number,
  ) {
    super(message)
    this.name = 'ContactSubmissionError'
  }
}

const EMAIL_REGEX = /^[^\s@]+@[^\s@]+\.[^\s@]+$/i

const MAX_LENGTHS = {
  fullName: 120,
  company: 120,
  email: 160,
  message: 3000,
} as const

function trimString(value: unknown): string {
  return typeof value === 'string' ? value.trim() : ''
}

export function coerceContactFormData(input: unknown): ContactFormData | null {
  if (!input || typeof input !== 'object' || Array.isArray(input)) {
    return null
  }

  const record = input as Record<string, unknown>

  return {
    fullName: trimString(record.fullName),
    company: trimString(record.company),
    email: trimString(record.email).toLowerCase(),
    message: trimString(record.message),
    website: trimString(record.website),
  }
}

export function validateContactForm(input: ContactFormData): ContactValidationErrors {
  const errors: ContactValidationErrors = {}

  if (!input.fullName) errors.fullName = 'required'
  else if (input.fullName.length > MAX_LENGTHS.fullName) errors.fullName = 'tooLong'

  if (!input.company) errors.company = 'required'
  else if (input.company.length > MAX_LENGTHS.company) errors.company = 'tooLong'

  if (!input.email) errors.email = 'required'
  else if (input.email.length > MAX_LENGTHS.email) errors.email = 'tooLong'
  else if (!EMAIL_REGEX.test(input.email)) errors.email = 'invalidEmail'

  if (!input.message) errors.message = 'required'
  else if (input.message.length > MAX_LENGTHS.message) errors.message = 'tooLong'

  if (input.website) errors.website = 'spam'

  return errors
}

export function hasContactValidationErrors(errors: ContactValidationErrors): boolean {
  return Object.keys(errors).length > 0
}

export async function submitContactForm(payload: ContactSubmissionPayload): Promise<void> {
  const response = await fetch('/api/contact', {
    method: 'POST',
    headers: {
      'Content-Type': 'application/json',
    },
    body: JSON.stringify(payload),
  })

  if (response.ok) {
    return
  }

  let message = 'Unable to submit the contact request.'
  const contentType = response.headers.get('content-type') ?? ''

  if (contentType.includes('application/json')) {
    const data = (await response.json()) as { error?: string }
    if (typeof data.error === 'string' && data.error) {
      message = data.error
    }
  }

  throw new ContactSubmissionError(message, response.status)
}

export function buildContactEmailText(payload: ContactFormData): string {
  return [
    'New contact request from code29.dev',
    '',
    `Name: ${payload.fullName}`,
    `Company: ${payload.company}`,
    `Email: ${payload.email}`,
    '',
    'Message:',
    payload.message,
  ].join('\n')
}
