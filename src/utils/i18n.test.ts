import { afterEach, describe, expect, it, vi } from 'vitest'

import { DEFAULT_LANG, getLang, resolveBrowserLang, useTranslations } from '@/utils/i18n'

afterEach(() => {
  localStorage.clear()
  vi.unstubAllGlobals()
})

describe('resolveBrowserLang', () => {
  it('treats every Spanish variant as es', () => {
    for (const value of ['es', 'es-ES', 'ES-es', 'es-419']) {
      expect(resolveBrowserLang(value)).toBe('es')
    }
  })

  it('falls back to en for anything else, including empty input', () => {
    for (const value of ['en-GB', 'fr', '', null, undefined]) {
      expect(resolveBrowserLang(value)).toBe('en')
    }
  })
})

describe('getLang', () => {
  it('prefers a valid stored preference over the browser locale', () => {
    localStorage.setItem('lang', 'en')
    vi.stubGlobal('navigator', { language: 'es-ES' })
    expect(getLang()).toBe('en')
  })

  it('ignores a corrupted stored value and falls back to the browser', () => {
    localStorage.setItem('lang', 'klingon')
    vi.stubGlobal('navigator', { language: 'es-ES' })
    expect(getLang()).toBe('es')
  })

  it('defaults to Spanish, matching the server-rendered copy', () => {
    // BaseLayout server-renders lang="es"; a different default here would make
    // the html lang attribute disagree with the visible copy.
    expect(DEFAULT_LANG).toBe('es')
  })
})

describe('useTranslations', () => {
  it('returns the section copy for the requested language', () => {
    const es = useTranslations('hero', 'es')
    const en = useTranslations('hero', 'en')
    expect(es).not.toEqual(en)
    expect(Object.keys(es)).toEqual(Object.keys(en))
  })

  it('keeps both languages structurally identical across every section', () => {
    // A key present in one language only renders as blank copy for the other.
    const sections = ['hero', 'contact', 'footer'] as const
    for (const section of sections) {
      expect(Object.keys(useTranslations(section, 'es')).sort()).toEqual(
        Object.keys(useTranslations(section, 'en')).sort(),
      )
    }
  })
})
