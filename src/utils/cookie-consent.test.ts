import { ConsentService } from '@/utils/cookie-consent'

describe('cookie consent service', () => {
  beforeEach(() => {
    ConsentService.clear()
  })

  it('returns null before any decision is made', () => {
    expect(ConsentService.get()).toBeNull()
    expect(ConsentService.hasDecided()).toBe(false)
  })

  it('persists accept all', () => {
    expect(ConsentService.acceptAll()).toEqual({
      necessary: true,
      analytics: true,
      marketing: true,
    })

    expect(ConsentService.get()).toEqual({
      necessary: true,
      analytics: true,
      marketing: true,
    })
  })

  it('persists custom preferences', () => {
    expect(
      ConsentService.save({
        necessary: true,
        analytics: true,
        marketing: false,
      }),
    ).toEqual({
      necessary: true,
      analytics: true,
      marketing: false,
    })
  })

  it('rejects optional cookies by default', () => {
    expect(ConsentService.rejectAll()).toEqual({
      necessary: true,
      analytics: false,
      marketing: false,
    })
  })
})
