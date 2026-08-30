import base from './playwright.config'

/**
 * The CI runner, reproduced locally.
 *
 * On 2026-08-30 three e2e failed on CI and passed locally every time. Two
 * differences did it: the runner's browser is in English, so the chat adopts a
 * language the developer's machine never switches to — and it runs two workers
 * on one box, which is slow enough for a fingerprint captured "immediately" to
 * land before hydration rather than after.
 *
 * `retries: 0` on purpose. CI retries twice, which turns a real race into a
 * "flaky" line somebody scrolls past; here a race has to fail.
 *
 * Run with `npm run test:e2e:ci-sim` before blaming the runner.
 */
export default {
  ...base,
  workers: 2,
  retries: 0,
  use: { ...base.use, locale: 'en-US' },
}
