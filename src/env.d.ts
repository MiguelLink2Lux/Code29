/// <reference path="../.astro/types.d.ts" />
import 'astro/client'

interface ImportMetaEnv {
  readonly PUBLIC_GA4_ID?: string
  readonly RESEND_API_KEY?: string
  readonly CONTACT_TO_EMAIL?: string
  readonly CONTACT_FROM_EMAIL?: string
}

interface ImportMeta {
  readonly env: ImportMetaEnv
}