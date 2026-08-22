// Declarative definition of the guided contact flow.
//
// The flow is FIXED: a known sequence of steps with per-step validation, not a
// free conversation. The model that later writes the report never decides what
// is asked, and never sees a prompt written by the visitor — it receives the
// answers collected here plus measured signals about their site.
//
// Order matters for more than UX: everything that costs money or reputation
// (fetching a third-party site, generating and emailing a report) sits *after*
// the email verification step, so an unverified visitor cannot trigger it.

export type ContactChatStepId =
  | 'name'
  | 'company'
  | 'email'
  | 'code'
  | 'delivery'
  | 'bugs'
  | 'deploys'
  | 'security'
  | 'observability'
  | 'website'
  | 'consent'

export type ContactChatStepKind = 'text' | 'email' | 'code' | 'choice' | 'consent'

export type ContactChatValidationCode =
  | 'required'
  | 'invalidEmail'
  | 'invalidCode'
  | 'invalidChoice'
  | 'invalidUrl'
  | 'consentRequired'
  | 'tooLong'

export interface ContactChatOption {
  /** Stable identifier stored in the transcript and sent to the backend. */
  value: string
  /** Key under `contactChat.steps.<stepId>.options` in translations.ts. */
  labelKey: string
}

export interface ContactChatStep {
  id: ContactChatStepId
  kind: ContactChatStepKind
  required: boolean
  /** A step that may be answered with an empty value. Implied by `!required`. */
  skippable?: boolean
  options?: ContactChatOption[]
  maxLength?: number
  /** Diagnosis axis this step feeds in the generated report. */
  axis?: 'delivery' | 'bugs' | 'deploys' | 'security' | 'observability'
}

const FREE_TEXT_MAX = 300
const EMAIL_REGEX = /^[^\s@]+@[^\s@]+\.[^\s@]+$/i
// Hostname with at least one dot, optional scheme and path. Deliberately loose:
// the authoritative check is the backend's SSRF guard, which resolves DNS.
const WEBSITE_REGEX = /^(https?:\/\/)?[a-z0-9][a-z0-9.-]*\.[a-z]{2,}(\/\S*)?$/i

const option = (value: string, labelKey: string): ContactChatOption => ({ value, labelKey })

export const CONTACT_CHAT_STEPS: readonly ContactChatStep[] = [
  { id: 'name', kind: 'text', required: true, maxLength: 120 },
  { id: 'company', kind: 'text', required: false, skippable: true, maxLength: FREE_TEXT_MAX },
  { id: 'email', kind: 'email', required: true, maxLength: 160 },
  { id: 'code', kind: 'code', required: true },
  {
    id: 'delivery',
    kind: 'choice',
    required: true,
    axis: 'delivery',
    options: [
      option('no-ai', 'noAi'),
      option('ai-assisted-editor', 'aiAssistedEditor'),
      option('ai-agents-in-workflow', 'aiAgents'),
      option('unsure', 'unsure'),
    ],
  },
  {
    id: 'bugs',
    kind: 'choice',
    required: true,
    axis: 'bugs',
    options: [
      option('manual-triage', 'manualTriage'),
      option('issue-tracker-only', 'trackerOnly'),
      option('automated-tests-gate', 'testsGate'),
      option('ai-assisted-triage', 'aiTriage'),
    ],
  },
  {
    id: 'deploys',
    kind: 'choice',
    required: true,
    axis: 'deploys',
    options: [
      option('manual-deploys', 'manual'),
      option('scripted-deploys', 'scripted'),
      option('ci-cd-pipeline', 'pipeline'),
      option('continuous-delivery', 'continuous'),
    ],
  },
  {
    id: 'security',
    kind: 'choice',
    required: true,
    axis: 'security',
    options: [
      option('none', 'none'),
      option('manual-reviews', 'manualReviews'),
      option('dependency-scanning', 'dependencyScanning'),
      option('scanning-and-policies', 'scanningAndPolicies'),
    ],
  },
  {
    id: 'observability',
    kind: 'choice',
    required: true,
    axis: 'observability',
    options: [
      option('none', 'none'),
      option('logs-only', 'logsOnly'),
      option('error-monitoring', 'errorMonitoring'),
      option('full-observability', 'fullObservability'),
    ],
  },
  { id: 'website', kind: 'text', required: false, skippable: true, maxLength: 300 },
  { id: 'consent', kind: 'consent', required: true },
]

export function stepById(id: string): ContactChatStep {
  const step = CONTACT_CHAT_STEPS.find((candidate) => candidate.id === id)

  if (!step) {
    throw new Error(`Unknown contact chat step: ${id}`)
  }

  return step
}

export function validateAnswer(
  id: string,
  rawValue: string,
): ContactChatValidationCode | null {
  const step = stepById(id)
  const value = rawValue.trim()

  if (!value) {
    if (step.kind === 'consent') return 'consentRequired'
    return step.required ? 'required' : null
  }

  if (step.maxLength && value.length > step.maxLength) {
    return 'tooLong'
  }

  switch (step.kind) {
    case 'email':
      return EMAIL_REGEX.test(value) ? null : 'invalidEmail'

    case 'code':
      return /^\d{6}$/.test(value) ? null : 'invalidCode'

    case 'choice':
      return step.options?.some((candidate) => candidate.value === value) ? null : 'invalidChoice'

    case 'consent':
      // Only an explicit affirmative counts: GDPR consent cannot be implied.
      return value === 'true' ? null : 'consentRequired'

    case 'text':
      if (step.id === 'website') {
        return WEBSITE_REGEX.test(value) ? null : 'invalidUrl'
      }
      return null

    default:
      return null
  }
}
