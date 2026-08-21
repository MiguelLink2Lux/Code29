import { defineConfig } from 'vitest/config'

// Separate config so the artifact assertions stay out of the fast unit gate:
// they need `npm run build` to have run first.
export default defineConfig({
  test: {
    include: ['tests/artifacts/**/*.test.ts'],
  },
})
