> **Type:** Architecture — **Scope:** Contact chat — **Status:** Active (Phase 3 in progress)

# Design: Contact Chat v1

## Enfoque tecnico

Sustituir el placeholder actual de contacto por una isla Vue que renderice un chat guiado paso a paso. La primera entrega mantiene la arquitectura existente de Astro + Vercel: el cliente recoge respuestas, valida cada paso y envia un payload normalizado a un endpoint serverless que despacha el contacto por email. El contrato de UI se define para que el mismo shell del chat pueda pasar mas adelante de prompts guiados a prompts generados por IA sin rehacer la seccion.

## Funcionalidades por fases

| Fase | Objetivo | Alcance |
|------|----------|---------|
| 1 | Salir rapido | Chat guiado sin IA, campos obligatorios, validacion incremental, estados loading/success/error y entrega por Resend |
| 2 | Mejorar cualificacion | Preguntas ramificadas, recuperacion de sesion, metadatos estructurados y eventos de analitica |
| 3 | Introducir IA | Backend FastAPI, orquestacion IA, respuestas en streaming y analisis enriquecido del lead — **implementada** (generador IA en stub hasta que exista `GEMINI_API_KEY`), ver [[decisions/0006-guided-ai-contact-flow]] |

## Decisiones de arquitectura

### Decision: mantener serverless en la primera entrega

| Opcion | Tradeoff | Decision |
|------|------|------|
| Vercel serverless + envio por email | Camino mas corto, menos capacidad de orquestacion | **Elegida para Fase 1** |
| FastAPI desde el inicio | Mejor backend a largo plazo, MVP mas lento | Pospuesta a Fase 3 |

### Decision: usar chat guiado, no chat libre

| Opcion | Tradeoff | Decision |
|------|------|------|
| Flujo determinista configurable | UX predecible, validacion simple, migracion limpia | **Elegida para Fase 1** |
| Chat abierto sin IA | Parece conversacional, pero produce datos pobres | Descartada |

### Decision: separar flujo y envio

| Opcion | Tradeoff | Decision |
|------|------|------|
| Un solo componente con toda la logica | Mas rapido al inicio, dificil de evolucionar | Descartada |
| Configuracion del flujo + adaptador de envio | Algo mas de estructura, mucho mas escalable | **Elegida** |

## Flujo de datos

```text
Landing
  -> ContactSection.astro
    -> ContactChat.vue
      -> useContactChat() / estado del flujo
      -> validacion por paso
      -> submitContactLead()
        -> /api/contact
          -> adaptador de entrega
            -> Resend
```

El cliente solo envia datos cuando el chat llega al paso final de confirmacion. El payload incluye transcript del chat, datos normalizados de contacto, consentimiento y metadatos minimos para evolucion futura.

## Cambios de archivos

| Archivo | Accion | Descripcion |
|------|--------|-------------|
| `src/components/sections/ContactSection.astro` | Modificar | Reemplazar el placeholder por el host del chat y el bloque legal de soporte |
| `src/components/contact/ContactChat.vue` | Crear | UI del chat, render de pasos, estados y reintentos |
| `src/utils/contact-chat-flow.ts` | Crear | Configuracion declarativa de pasos y reglas de ramificacion |
| `src/utils/contact-chat.ts` | Crear | Orquestacion cliente, normalizacion y llamada al adaptador |
| `src/utils/contact-submit.ts` | Crear | Contrato abstracto de envio |
| `src/pages/api/contact.ts` | Crear | Endpoint serverless para la Fase 1 |
| `src/i18n/translations.ts` | Modificar | Prompts, labels, errores y mensajes de estado del chat |
| `docs/requirements/PRD.md` | Modificar | Ajustar el wording de "formulario" a "chat guiado de captacion" |

## Interfaces / contratos

```ts
type ContactChatStepId = 'name' | 'company' | 'email' | 'need' | 'confirm'

interface ContactLeadPayload {
  name: string
  company?: string
  email: string
  need: string
  transcript: Array<{ stepId: ContactChatStepId; answer: string }>
  consent: { privacyAccepted: true }
  meta: { source: 'landing-chat'; locale: 'es' | 'en' }
}

interface ContactSubmitResult {
  ok: boolean
  message: string
}
```

## Estrategia de testing

| Capa | Que probar | Enfoque |
|-------|-------------|----------|
| Unit | Flujo, validacion y normalizacion | Vitest |
| Integration | Contrato entre chat y endpoint serverless | Vitest con adaptador mock |
| E2E | Camino feliz, error de validacion y reintento | Playwright |

## Migracion / rollout

La Fase 1 sale sobre la seccion actual de contacto sin migracion de backend. La Fase 2 amplía el payload y el flujo sin cambiar el punto de entrada. La Fase 3 conserva el shell del chat, pero sustituye el adaptador de envio por una API conversacional en FastAPI.

## Resolved questions

Both questions this document closed with are now answered by the implementation:

- **Is an in-progress chat kept across a refresh?** Yes. `src/utils/contact-chat.ts` persists
  answers under the `contact-chat` key in **`sessionStorage`, deliberately not
  `localStorage`** — a reload keeps the conversation, and closing the tab destroys the lead's
  data. The access token is never persisted at all.
- **Summary, transcript, or both?** Both. `render_report_email()` in
  `backend/app/services/mailer.py` sends the normalised summary *and* the full transcript,
  together with the consent statement the visitor granted.

## Phase 3 — as implemented

Phase 3 landed, with the caveat that the report generator is still a deterministic **stub**
until `GEMINI_API_KEY` exists. The design above described the intent; the shipped shape
differs in ways worth reading before touching the code:

| Design said | Implementation does |
|---|---|
| 5 steps (`name, company, email, need, confirm`) | **10 fixed steps**: `name, company, email, code, delivery, bugs, deploys, security, website, consent` |
| `src/pages/api/contact.ts` serverless endpoint | **Deleted.** The FastAPI backend is the only email sender |
| `src/utils/contact-submit.ts` submit contract | `src/utils/contact-api.ts` (+ `src/utils/turnstile-client.ts`) |
| Email delivery of a contact lead | Email delivery of a **generated workflow report** |
| Free-form `need` answer | Four structured diagnosis axes (`delivery`, `bugs`, `deploys`, `security`) |

The step **order is an authorisation rule**, not a UX preference: `code` verifies the email
address before any step that costs money or makes an outbound request. The full rationale,
the stateless verification design, the Turnstile gate, the privacy posture and the open
security risks are recorded in [[decisions/0006-guided-ai-contact-flow]] — read it before
changing the flow.

Endpoints serving the flow, all under `/api/v1`:

| Route | Role |
|---|---|
| `POST /contact/verification/request` | Turnstile, then email a derived code |
| `POST /contact/verification/confirm` | Exchange the code for a signed access token |
| `POST /contact/site-analysis` | Fetch the lead's home page behind the SSRF guard (token required) |
| `POST /contact/report` | Generate and deliver the report (token required; it names the recipient) |

## References

- [[decisions/0006-guided-ai-contact-flow]] — Phase 3 decisions, risks and privacy posture
- [[decisions/0004-backend-deploy-provider]] — where the backend runs, and its bundle limit
- [[testing-strategy]] — the gates covering the chat
- [[index]]
