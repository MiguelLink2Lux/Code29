import {
  buildContactEmailText,
  coerceContactFormData,
  hasContactValidationErrors,
  validateContactForm,
} from '@/utils/contact'

describe('contact utilities', () => {
  it('coerces and normalizes payload fields', () => {
    expect(
      coerceContactFormData({
        fullName: '  Miguel Navarro  ',
        company: '  Code29 ',
        email: '  MIGUEL@CODE29.DEV ',
        message: '  Hola  ',
        website: ' ',
      }),
    ).toEqual({
      fullName: 'Miguel Navarro',
      company: 'Code29',
      email: 'miguel@code29.dev',
      message: 'Hola',
      website: '',
    })
  })

  it('rejects invalid payload shape', () => {
    expect(coerceContactFormData(null)).toBeNull()
    expect(coerceContactFormData('invalid')).toBeNull()
    expect(coerceContactFormData([])).toBeNull()
  })

  it('validates required fields, email format, and honeypot', () => {
    const errors = validateContactForm({
      fullName: '',
      company: '',
      email: 'invalid-email',
      message: '',
      website: 'bot',
    })

    expect(errors).toEqual({
      fullName: 'required',
      company: 'required',
      email: 'invalidEmail',
      message: 'required',
      website: 'spam',
    })
    expect(hasContactValidationErrors(errors)).toBe(true)
  })

  it('builds the outgoing email body', () => {
    expect(
      buildContactEmailText({
        fullName: 'Miguel Navarro',
        company: 'Code29',
        email: 'miguel@code29.dev',
        message: 'Necesito ayuda con mi roadmap.',
        website: '',
      }),
    ).toContain('Name: Miguel Navarro')
  })
})
