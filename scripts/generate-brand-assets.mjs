/**
 * Generates the social card and icon assets from inline SVG using sharp.
 *
 * Run after any change to the brand: `node scripts/generate-brand-assets.mjs`.
 * The outputs are committed to public/ — generation is a build-time-free step so
 * the deploy never depends on a rasterizer being available.
 *
 * Colors mirror src/styles/tokens.css. Type uses a generic sans stack on
 * purpose: sharp rasterizes with system fonts, and the display font
 * (Space Grotesk) is loaded by the browser, not installed here.
 */
import { mkdir, writeFile } from 'node:fs/promises'
import { join } from 'node:path'

import sharp from 'sharp'

const PUBLIC_DIR = join(process.cwd(), 'public')

const BASE = '#131314'
const SURFACE = '#1C1B1C'
const PRIMARY = '#00F0FF'
const SECONDARY = '#9D00FF'
const TEXT = '#E5E2E3'
const MUTED = '#9A9899'

const SANS = 'Helvetica Neue, Helvetica, Arial, sans-serif'

/** 1200x630 Open Graph card. */
const ogSvg = `<svg xmlns="http://www.w3.org/2000/svg" width="1200" height="630" viewBox="0 0 1200 630">
  <defs>
    <linearGradient id="glow" x1="0" y1="0" x2="1" y2="1">
      <stop offset="0%" stop-color="${PRIMARY}"/>
      <stop offset="100%" stop-color="${SECONDARY}"/>
    </linearGradient>
    <pattern id="grid" width="40" height="40" patternUnits="userSpaceOnUse">
      <path d="M40 0H0V40" fill="none" stroke="${SURFACE}" stroke-width="2"/>
    </pattern>
  </defs>

  <rect width="1200" height="630" fill="${BASE}"/>
  <rect width="1200" height="630" fill="url(#grid)" opacity="0.7"/>

  <!-- Accent bar: the design system forbids border radius. -->
  <rect x="80" y="150" width="8" height="330" fill="url(#glow)"/>

  <text x="128" y="212" font-family="${SANS}" font-size="26" letter-spacing="8"
        fill="${PRIMARY}" font-weight="600">&gt;_ CODE29</text>

  <text x="128" y="320" font-family="${SANS}" font-size="82" font-weight="700" fill="${TEXT}">
    Miguel Navarro
  </text>

  <text x="128" y="400" font-family="${SANS}" font-size="44" font-weight="600" fill="${PRIMARY}">
    CTO as a Service
  </text>

  <text x="128" y="462" font-family="${SANS}" font-size="34" fill="${MUTED}">
    AI Project Manager
  </text>

  <rect x="128" y="520" width="240" height="6" fill="${SECONDARY}" opacity="0.8"/>
</svg>`

/** Square mark used for every icon size. */
const faviconSvg = `<svg xmlns="http://www.w3.org/2000/svg" width="64" height="64" viewBox="0 0 64 64">
  <rect width="64" height="64" fill="${BASE}"/>
  <path d="M12 20 L22 32 L12 44" fill="none" stroke="${PRIMARY}" stroke-width="6"
        stroke-linecap="square"/>
  <rect x="28" y="40" width="24" height="6" fill="${SECONDARY}"/>
</svg>`

async function main() {
  await mkdir(PUBLIC_DIR, { recursive: true })

  await writeFile(join(PUBLIC_DIR, 'favicon.svg'), `${faviconSvg}\n`, 'utf8')

  await sharp(Buffer.from(ogSvg)).png().toFile(join(PUBLIC_DIR, 'og-image.png'))

  const icon = Buffer.from(faviconSvg)
  await sharp(icon).resize(32, 32).png().toFile(join(PUBLIC_DIR, 'favicon-32.png'))
  await sharp(icon).resize(180, 180).png().toFile(join(PUBLIC_DIR, 'apple-touch-icon.png'))

  console.log('brand assets written to public/: og-image.png, favicon.svg, favicon-32.png, apple-touch-icon.png')
}

await main()
