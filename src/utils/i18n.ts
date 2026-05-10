// i18n utility — DIP abstraction layer between components and translations.ts
// Components import from here, never directly from translations.ts

import { translations } from '../i18n/translations'
export type { Lang } from '../i18n/translations'

export const DEFAULT_LANG = 'es' as const satisfies import('../i18n/translations').Lang

/**
 * Reads the current language from localStorage.
 * Falls back to DEFAULT_LANG if not set or if the value is invalid.
 * Safe to call in client-side scripts only (not during SSR).
 */
export function getLang(): import('../i18n/translations').Lang {
  if (typeof localStorage === 'undefined') return DEFAULT_LANG
  const stored = localStorage.getItem('lang')
  if (stored === 'es' || stored === 'en') return stored
  return DEFAULT_LANG
}

/**
 * Returns the translation object for a given section and language.
 *
 * Usage:
 *   const t = useTranslations('hero', 'es')
 *   t.tag // → 'THE NEON ARCHITECT'
 */
export function useTranslations<K extends keyof typeof translations>(
  section: K,
  lang: import('../i18n/translations').Lang,
): (typeof translations)[K][typeof lang] {
  return translations[section][lang]
}
