// Orchestration for the guided contact chat: current step, transcript,
// validation and the payload handed to the backend.
//
// Deliberately framework-free so it can be unit-tested without mounting a
// component; ContactChat.vue is a thin renderer over this state.
//
// Two privacy rules are enforced here rather than left to the caller:
//  - in-progress answers live in sessionStorage, so lead data dies with the tab;
//  - the access token is never persisted and never enters the transcript. It
//    proves email ownership, and the backend reads the address from it, so the
//    address itself never travels in the report payload.

import {
  CONTACT_CHAT_STEPS,
  type ContactChatStepId,
  type ContactChatValidationCode,
  stepById,
  validateAnswer,
} from '@/utils/contact-chat-flow'

const STORAGE_KEY = 'contact-chat'

export interface TranscriptEntry {
  stepId: ContactChatStepId
  answer: string
}

export interface ContactChatState {
  currentStepId: ContactChatStepId
  transcript: TranscriptEntry[]
  complete: boolean
  emailVerified: boolean
  accessToken: string | null
  progress: { index: number; total: number }
}

/**
 * The shape the backend accepts — see tests/contracts/report-request.json.
 * Snake_case because it is the API's vocabulary, not ours: aligning here beats
 * a translation layer nobody remembers to update.
 */
export interface ReportRequest {
  contact_name: string
  company: string
  locale: 'es' | 'en'
  workflow: {
    practices: string[]
    team_size: string | null
    notes: string | null
  }
  site_url: string | null
  transcript: Array<{ step_id: string; answer: string }>
  consent: {
    privacy_accepted: boolean
    report_accepted: boolean
  }
}

/**
 * Chat answers → the practice identifiers the report generator diagnoses by.
 * The generator compares practices present against absent per axis, so an
 * unmapped answer is not a smaller report: it is a wrong one.
 */
const PRACTICES_BY_ANSWER: Record<string, string[]> = {
  // AI in development
  'no-ai': [],
  unsure: [],
  'ai-assisted-editor': ['ai_assisted_coding'],
  'ai-agents-in-workflow': ['ai_assisted_coding'],
  // Bugs and quality
  'manual-triage': [],
  'issue-tracker-only': [],
  'automated-tests-gate': ['automated_tests', 'code_review'],
  'ai-assisted-triage': ['ai_bug_triage', 'automated_tests'],
  // Deploys
  'manual-deploys': [],
  'scripted-deploys': [],
  'ci-cd-pipeline': ['ci_pipeline'],
  'continuous-delivery': ['ci_pipeline', 'automated_deploys'],
  // Security and dependencies
  none: [],
  'manual-reviews': ['code_review'],
  'dependency-scanning': ['dependency_scanning'],
  'scanning-and-policies': ['dependency_scanning'],
  // Observability
  'logs-only': [],
  'error-monitoring': ['error_monitoring'],
  'full-observability': ['error_monitoring'],
}

/** Absolute URL or null: the backend rejects a scheme-less site_url outright. */
function normalizeSiteUrl(raw: string): string | null {
  const value = raw.trim()

  if (!value) return null

  return /^https?:\/\//i.test(value) ? value : `https://${value}`
}

export type AnswerResult = { ok: true } | { ok: false; error: ContactChatValidationCode }

interface PersistedShape {
  index: number
  answers: Array<[ContactChatStepId, string]>
}

function readPersisted(): PersistedShape | null {
  try {
    const raw = sessionStorage.getItem(STORAGE_KEY)
    if (!raw) return null

    const parsed = JSON.parse(raw) as PersistedShape
    if (typeof parsed?.index !== 'number' || !Array.isArray(parsed.answers)) return null

    return parsed
  } catch {
    // Corrupted payload, private mode, or storage denied: start clean rather
    // than take the whole island down.
    return null
  }
}

function writePersisted(payload: PersistedShape): void {
  try {
    sessionStorage.setItem(STORAGE_KEY, JSON.stringify(payload))
  } catch {
    // Persistence is a convenience, never a requirement.
  }
}

function clearPersisted(): void {
  try {
    sessionStorage.removeItem(STORAGE_KEY)
  } catch {
    /* ignore */
  }
}

export function createContactChat(locale: 'es' | 'en' = 'es') {
  const answers = new Map<ContactChatStepId, string>()
  let index = 0
  let accessToken: string | null = null

  const restored = readPersisted()
  if (restored) {
    for (const [stepId, value] of restored.answers) {
      answers.set(stepId, value)
    }
    index = Math.min(Math.max(restored.index, 0), CONTACT_CHAT_STEPS.length)
  }

  const persist = () => writePersisted({ index, answers: [...answers.entries()] })

  const state: ContactChatState = {
    get currentStepId() {
      const step = CONTACT_CHAT_STEPS[Math.min(index, CONTACT_CHAT_STEPS.length - 1)]
      return step.id
    },
    get transcript() {
      return [...answers.entries()].map(([stepId, answer]) => ({ stepId, answer }))
    },
    get complete() {
      return index >= CONTACT_CHAT_STEPS.length
    },
    get emailVerified() {
      return accessToken !== null
    },
    get accessToken() {
      return accessToken
    },
    get progress() {
      return { index: Math.min(index, CONTACT_CHAT_STEPS.length), total: CONTACT_CHAT_STEPS.length }
    },
  }

  function answer(rawValue: string): AnswerResult {
    if (state.complete) return { ok: true }

    const stepId = state.currentStepId
    const error = validateAnswer(stepId, rawValue)

    if (error) return { ok: false, error }

    answers.set(stepId, rawValue.trim())
    index += 1
    persist()

    return { ok: true }
  }

  function back(): void {
    if (index === 0) return

    index -= 1
    persist()
  }

  function answerFor(stepId: ContactChatStepId): string {
    return answers.get(stepId) ?? ''
  }

  function markEmailVerified(token: string): void {
    // Held in memory only: never persisted, never in the transcript.
    accessToken = token
  }

  function reset(): void {
    answers.clear()
    index = 0
    accessToken = null
    clearPersisted()
  }

  function buildReportRequest(): ReportRequest {
    if (!state.complete) {
      throw new Error('Cannot build a report request from an incomplete chat')
    }

    const practices = new Set<string>()

    for (const stepId of ['delivery', 'bugs', 'deploys', 'security', 'observability'] as const) {
      for (const practice of PRACTICES_BY_ANSWER[answerFor(stepId)] ?? []) {
        practices.add(practice)
      }
    }

    return {
      contact_name: answerFor('name'),
      company: answerFor('company'),
      locale,
      workflow: {
        practices: [...practices],
        team_size: null,
        notes: null,
      },
      site_url: normalizeSiteUrl(answerFor('website')),
      // The email is already proven by the token, and the code is a one-use
      // secret: neither belongs in a transcript that gets emailed and logged.
      transcript: state.transcript
        .filter((entry) => entry.stepId !== 'email' && entry.stepId !== 'code')
        .map((entry) => ({
          step_id: entry.stepId,
          answer: entry.answer,
        })),
      consent: {
        privacy_accepted: answerFor('consent') === 'true',
        report_accepted: answerFor('consent') === 'true',
      },
    }
  }

  return { state, answer, back, answerFor, markEmailVerified, reset, buildReportRequest, stepById }
}
