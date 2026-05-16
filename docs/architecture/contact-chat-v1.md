# Design: Contact Chat v1

## Enfoque tecnico

Sustituir el placeholder actual de contacto por una isla Vue que renderice un chat guiado paso a paso. La primera entrega mantiene la arquitectura existente de Astro + Vercel: el cliente recoge respuestas, valida cada paso y envia un payload normalizado a un endpoint serverless que despacha el contacto por email. El contrato de UI se define para que el mismo shell del chat pueda pasar mas adelante de prompts guiados a prompts generados por IA sin rehacer la seccion.

## Funcionalidades por fases

| Fase | Objetivo | Alcance |
|------|----------|---------|
| 1 | Salir rapido | Chat guiado sin IA, campos obligatorios, validacion incremental, estados loading/success/error y entrega por Resend |
| 2 | Mejorar cualificacion | Preguntas ramificadas, recuperacion de sesion, metadatos estructurados y eventos de analitica |
| 3 | Introducir IA | Backend FastAPI, orquestacion IA, respuestas en streaming y analisis enriquecido del lead |

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

## Preguntas abiertas

- [ ] En la Fase 1, ¿guardamos el chat en progreso tras un refresh o lo dejamos para la Fase 2?
- [ ] ¿El email de entrega debe incluir el transcript completo, un resumen normalizado o ambos?
