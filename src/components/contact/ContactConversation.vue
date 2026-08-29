<script setup lang="ts">
// The conversational contact island: a message thread instead of one step at a
// time, free text instead of closed options, and no step counter — the server
// decides when the conversation is done.
//
// It owns presentation and side-effect calls only. The flow rules, the budget
// and the privacy guarantees live in src/utils/contact-conversation.ts, which is
// framework-free and unit-tested without mounting anything.
//
// One composer serves the whole conversation. Verifying the address used to be
// a separate block of labelled fields beside the thread, which is what made the
// chat read as a form wearing a costume: the bot now asks for the address in its
// own voice, in the thread, and the visitor answers where they answer everything
// else. The address and the code are marked ephemeral by the module, so they are
// shown and never stored.
import { computed, nextTick, onMounted, ref, watch } from 'vue'

import { translations, type Lang } from '@/i18n/translations'
import { DEFAULT_LANG, getLang } from '@/utils/i18n'
import { type ContactApi, createContactApi } from '@/utils/contact-api'
import {
  createConversation,
  MAX_MESSAGE_LENGTH,
  readAnswer,
} from '@/utils/contact-conversation'
import {
  createTurnstileClient,
  TurnstileNotConfigured,
  type TurnstileClient,
} from '@/utils/turnstile-client'

const props = defineProps<{
  api?: ContactApi
  turnstile?: TurnstileClient
  /** Injectable so a test can pin the opening. */
  pickOpening?: (count: number) => number
}>()

const api = props.api ?? createContactApi()
const turnstile =
  props.turnstile ??
  createTurnstileClient((import.meta.env.PUBLIC_TURNSTILE_SITE_KEY as string) ?? '')

/**
 * The language, from the utility that owns it — never sniffed off the DOM.
 *
 * It starts at DEFAULT_LANG, which is what Astro renders on the server, so the
 * client's first render matches the served HTML exactly. That matters: reading
 * `document.documentElement.lang` in setup produced a different value on the
 * client than on the server, and Vue's hydration corrects text nodes but not
 * attributes — so the bot spoke English into a Spanish placeholder.
 *
 * `getLang()` (localStorage, falling back to the browser) is the site's source
 * of truth, and it is applied in onMounted: a reactive change after mount is a
 * real render, and attributes follow. The rest of the page already works this
 * way through `data-i18n`, so the brief flash of Spanish is the behaviour the
 * whole site has, not a new one.
 */
const currentLang = ref<Lang>(DEFAULT_LANG)

const copy = computed(() => translations.contactConversation[currentLang.value])

/**
 * Picks this conversation's variant out of a rotating pool.
 *
 * The seed lives with the thread, so the wording is stable across a reload: the
 * verification messages are ephemeral and get re-rendered from scratch, and a
 * bot whose phrasing changes when the tab reloads reads as a different bot.
 */
function variant(pool: readonly string[]): string {
  return pool[chat.state.variantSeed % pool.length]
}

const chat = createConversation({
  api,
  // A getter: the visitor can switch language mid-conversation.
  lang: () => currentLang.value,
  openings: translations.contactConversation[currentLang.value].openings,
  botCopy: {
    codeRejected: translations.contactConversation[currentLang.value].verify.codeRejected,
    humanCheck: translations.contactConversation[currentLang.value].verify.humanCheck,
  },
  ...(props.pickOpening ? { pickOpening: props.pickOpening } : {}),
})

// The conversation state is deliberately framework-free, so it is not reactive.
// This counter is bumped after every mutation and read by the computeds below,
// which is what makes the thread follow the flow without coupling the module to
// Vue.
const tick = ref(0)
const sync = () => {
  tick.value += 1
}

const draft = ref('')
const localError = ref<string | null>(null)
const thread = ref<HTMLElement | null>(null)
// Where Cloudflare mounts the challenge. It has to be a node that is actually in
// the document: a detached one makes Turnstile lose track of its own widget, and
// an interactive challenge rendered there would be unreachable for the visitor.
const turnstileHost = ref<HTMLElement | null>(null)

const messages = computed(() => {
  void tick.value
  return chat.state.messages
})
const busy = computed(() => {
  void tick.value
  return chat.state.busy
})
const exhausted = computed(() => {
  void tick.value
  return chat.state.exhausted
})
const blocked = computed(() => {
  void tick.value
  return chat.state.blocked
})

/**
 * Whether the conversation is over — which is NOT the same as `complete`.
 *
 * `complete` used to swap the composer for the closing block, so the moment the
 * server had enough facts the visitor lost the ability to add anything. Since
 * this cycle the bot announces the report and invites one last thing, so the
 * chat outlives completeness by exactly one message. The module owns the rule.
 */
const closed = computed(() => {
  void tick.value
  return chat.state.closed
})

/**
 * The bot asks for the address when the server says so — and the composer does
 * not change at all.
 *
 * `next_step` used to choose a *field*: the composer swapped its id, label,
 * placeholder, button, inputmode and autocomplete, and the chat visibly became
 * a form halfway through a conversation. That is the questionnaire wearing
 * burbujas, which is what the visitor recognised. The step now chooses only
 * what the bot SAYS. What the visitor writes is read by `readAnswer`.
 */
const awaitingCode = computed(() => {
  void tick.value

  return chat.state.pendingEmail !== null && !chat.state.emailVerified
})

const closingCopy = computed(() => {
  void tick.value
  return variant(copy.value.exhausted)
})

const sendLabel = computed(() => (busy.value ? copy.value.sending : copy.value.send))

const errorMessage = computed(() => {
  void tick.value
  const code = localError.value ?? chat.state.error

  if (!code) return ''

  const errors = copy.value.errors as Record<string, string>

  return errors[code] ?? errors.generic
})

// The bot asks for the address itself, once, the moment the server says it is
// the missing piece. Without this the composer would silently change shape and
// the visitor would have no idea why.
watch(awaitingCode, (waiting, wasWaiting) => {
  if (!waiting || wasWaiting) return

  chat.pushEphemeral('bot', variant(copy.value.verify.askCode))
  sync()
})

// Follow the conversation. A thread that stays where it was is a thread the
// visitor has to scroll to read their own answer.
watch(
  () => messages.value.length,
  async () => {
    await nextTick()
    if (thread.value) thread.value.scrollTop = thread.value.scrollHeight
  },
)

async function submit(): Promise<void> {
  if (busy.value || closed.value) return

  const text = draft.value.trim()
  localError.value = null

  if (!text) {
    localError.value = 'empty'
    sync()
    return
  }

  // The composer never changed shape, so the reply is classified by what it
  // contains rather than by which field was on screen.
  const answer = readAnswer(text, { pendingEmail: chat.state.pendingEmail })

  if (answer.kind === 'email' && !chat.state.emailVerified) return submitEmail(answer.value)
  if (answer.kind === 'code') return submitCode(answer.value)

  return submitMessage(text)
}

async function submitMessage(text: string): Promise<void> {
  // Checked here as well as in the module: no reason to spend a request to be
  // told what we already know.
  if (text.length > MAX_MESSAGE_LENGTH) {
    localError.value = 'tooLong'
    sync()
    return
  }


  // Started, then synced, then awaited: `send` flips `busy` synchronously, and
  // without this sync the typing indicator would only appear after the answer
  // it was meant to cover had already arrived.
  const pending = chat.send(text)
  draft.value = ''
  sync()
  await pending
  sync()

  // Completeness is the trigger, and the module refuses if the server has not
  // agreed — so calling it unconditionally is safe and never premature.
  await chat.deliverReport()
  sync()
}

async function submitEmail(address: string): Promise<void> {
  if (!turnstileHost.value) {
    // The host is unconditional in the template, so this is a bug on our side,
    // never something the visitor did.
    localError.value = 'unavailable'
    sync()
    return
  }

  try {
    const token = await turnstile.getToken(turnstileHost.value)
    await chat.requestCode(address, token)
    draft.value = ''
  } catch (error) {
    // A missing site key is a deployment problem: telling the visitor to prove
    // they are human would send them in circles.
    localError.value = error instanceof TurnstileNotConfigured ? 'unavailable' : 'humanCheck'
  } finally {
    sync()
  }
}

async function submitCode(code: string): Promise<void> {
  const pending = chat.confirmCode(code)
  draft.value = ''
  sync()
  await pending
  sync()

  if (chat.state.emailVerified) {
    chat.pushEphemeral('bot', variant(copy.value.verify.verified))
    sync()
  }

  // Verifying the address is usually the last missing fact, so this is the
  // moment the report becomes possible.
  await chat.deliverReport()
  sync()
}

// Enter sends, Shift+Enter breaks the line — what every chat does, and the
// reason the composer is a textarea rather than a single-line input.
function onKeydown(event: KeyboardEvent): void {
  if (event.key !== 'Enter' || event.shiftKey) return

  event.preventDefault()
  void submit()
}

onMounted(() => {
  // Now that the DOM exists, adopt the language the site actually settled on.
  currentLang.value = getLang()
  chat.retranslateOpening(translations.contactConversation[currentLang.value].openings)
  sync()

  window.addEventListener('language-changed', (event) => {
    const detail = (event as CustomEvent<{ lang?: Lang }>).detail
    currentLang.value = detail?.lang === 'en' ? 'en' : 'es'
    chat.retranslateOpening(translations.contactConversation[currentLang.value].openings)
    sync()
  })
  sync()
})
</script>

<template>
  <div class="conversation">
    <!-- role="log" + aria-live: new bot messages are announced without stealing focus -->
    <ol
      ref="thread"
      class="conversation__thread"
      role="log"
      aria-live="polite"
      :aria-label="copy.threadLabel"
    >
      <li
        v-for="(message, index) in messages"
        :key="index"
        :class="[
          'conversation__message',
          message.role === 'visitor'
            ? 'conversation__message--visitor'
            : 'conversation__message--bot',
        ]"
      >
        <span class="conversation__who">
          {{ message.role === 'visitor' ? copy.you : copy.assistant }}
        </span>
        <p class="conversation__text">
          {{ message.text }}
        </p>
      </li>

      <li
        v-if="busy"
        class="conversation__message conversation__message--bot conversation__message--typing"
      >
        <span class="conversation__who">{{ copy.assistant }}</span>
        <p
          class="conversation__typing"
          :aria-label="copy.typing"
        >
          <span class="conversation__dot" />
          <span class="conversation__dot" />
          <span class="conversation__dot" />
        </p>
      </li>
    </ol>

    <div
      v-if="closed"
      class="conversation__done"
      role="status"
    >
      <p class="conversation__done-title">
        {{ blocked ? copy.blocked.title : copy.done.title }}
      </p>
      <p>{{ blocked ? copy.blocked.body : exhausted ? closingCopy : copy.done.body }}</p>
    </div>

    <form
      v-else
      class="conversation__composer"
      novalidate
      @submit.prevent="submit"
    >
      <label
        class="conversation__sr-only"
        for="conversation-input"
      >
        {{ copy.placeholder }}
      </label>
      <!--
        One id, one label, one placeholder, for the whole conversation. The
        composer must be indistinguishable at every moment: the instant it
        announces what it wants, the chat has become a form.
      -->
      <textarea
        id="conversation-input"
        v-model="draft"
        class="conversation__input"
        rows="1"
        :placeholder="copy.placeholder"
        autocomplete="off"
        :aria-invalid="Boolean(errorMessage)"
        :disabled="busy"
        @keydown="onKeydown"
      />
      <button
        type="submit"
        class="conversation__btn conversation__btn--primary"
        :disabled="busy"
      >
        {{ sendLabel }}
      </button>
    </form>

    <!--
      Always in the document, outside the v-if/v-else above: Turnstile needs a
      mounted node to render into, and when the challenge turns interactive the
      visitor has to be able to see and reach it.
    -->
    <div
      ref="turnstileHost"
      class="conversation__challenge"
    />

    <p
      v-if="errorMessage"
      class="conversation__error"
      role="alert"
    >
      {{ errorMessage }}
    </p>
  </div>
</template>

<style scoped>
/* Terminal aesthetic, no border radius — see docs/architecture/design.md. */
.conversation {
  display: flex;
  flex-direction: column;
  gap: var(--space-4);
  background: var(--glass-bg);
  padding: var(--space-8);
  text-align: left;
}

.conversation__thread {
  display: flex;
  flex-direction: column;
  gap: var(--space-4);
  margin: 0;
  padding: 0;
  list-style: none;
  max-height: 22rem;
  overflow-y: auto;
  scroll-behavior: smooth;
}

.conversation__message {
  display: flex;
  flex-direction: column;
  gap: var(--space-1);
  padding: var(--space-3);
  background: var(--color-surface-1);
  /* Bubbles, not rows: each side keeps its own column so the thread reads as
     an exchange at a glance. */
  max-width: 85%;
}

.conversation__message--visitor {
  align-self: flex-end;
  border-right: 2px solid var(--color-surface-3);
  text-align: right;
}

.conversation__message--bot {
  align-self: flex-start;
  border-left: 2px solid var(--color-primary);
}

.conversation__who {
  font-family: var(--font-display);
  font-size: 0.6875rem;
  letter-spacing: 0.16em;
  color: var(--color-text-muted);
}

.conversation__text {
  color: var(--color-text);
  white-space: pre-wrap;
}

.conversation__typing {
  display: flex;
  gap: 0.25rem;
  align-items: center;
  min-height: 1.25rem;
}

.conversation__dot {
  width: 0.375rem;
  height: 0.375rem;
  background: var(--color-primary);
  opacity: 0.4;
  animation: conversation-blink 1.2s infinite ease-in-out;
}

.conversation__dot:nth-child(2) {
  animation-delay: 0.2s;
}

.conversation__dot:nth-child(3) {
  animation-delay: 0.4s;
}

@keyframes conversation-blink {
  0%,
  80%,
  100% {
    opacity: 0.25;
  }
  40% {
    opacity: 1;
  }
}

/* Respect a visitor who asked the system for less motion. */
@media (prefers-reduced-motion: reduce) {
  .conversation__thread {
    scroll-behavior: auto;
  }

  .conversation__dot {
    animation: none;
    opacity: 0.6;
  }
}

.conversation__composer {
  display: flex;
  gap: var(--space-3);
  align-items: flex-end;
  flex-wrap: wrap;
}

.conversation__input {
  flex: 1 1 12rem;
  background: transparent;
  border: none;
  border-bottom: var(--input-border-bottom);
  color: var(--color-text);
  padding: var(--space-2) 0;
  font-family: var(--font-body);
  font-size: 1rem;
  resize: none;
  /* Two lines at most before it scrolls: a composer that grows without limit
     pushes the conversation off screen. */
  max-height: 6rem;
}

.conversation__input:focus {
  outline: none;
  border-bottom: var(--input-border-focus);
}

.conversation__btn {
  font-family: var(--font-display);
  letter-spacing: 0.08em;
  padding: var(--space-3) var(--space-6);
  border: none;
  background: var(--color-surface-2);
  color: var(--color-text);
  cursor: pointer;
}

.conversation__btn--primary {
  background: var(--btn-gradient);
  box-shadow: var(--btn-glow);
  color: var(--color-base);
}

.conversation__btn:disabled {
  opacity: 0.6;
  cursor: progress;
}

/* With appearance: interaction-only the host stays empty on most visits, so it
   only claims space once Cloudflare actually puts a challenge in it. */
.conversation__challenge:not(:empty) {
  display: flex;
  justify-content: center;
  margin-top: 0.75rem;
}

.conversation__hint,
.conversation__verified {
  font-size: 0.875rem;
  color: var(--color-text-muted);
}

.conversation__error {
  font-size: 0.875rem;
  color: #ff7a7a;
}

.conversation__done-title {
  font-family: var(--font-display);
  font-size: 1.25rem;
  color: var(--color-primary);
}

.conversation__sr-only {
  position: absolute;
  width: 1px;
  height: 1px;
  overflow: hidden;
  clip-path: inset(50%);
}
</style>
