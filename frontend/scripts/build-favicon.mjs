#!/usr/bin/env node
/**
 * Build favicon + logo assets using real JS libraries:
 *   sharp      → image resizing
 *   png-to-ico → assemble a multi-size Windows ICO
 *
 * Usage (called with npx to provide the two libs on PATH):
 *   npx -y -p sharp@0.33.5 -p png-to-ico@3.0.2 node frontend/scripts/build-favicon.mjs
 *
 * - Reads PNG sources from  <root>/logo/
 * - Copies logo set →      <root>/frontend/public/logo/
 * - Writes PNG favicon →   <root>/frontend/public/favicon-<size>.png
 * - Writes multi-size ICO  <root>/frontend/public/favicon.ico
 * - Writes manifest        <root>/frontend/public/site.webmanifest
 */

import sharp from 'sharp'
import pngToIco from 'png-to-ico'
import fs from 'node:fs'
import path from 'node:path'
import { fileURLToPath } from 'node:url'

const __filename = fileURLToPath(import.meta.url)
const FRONTEND = path.resolve(path.dirname(__filename), '..')
const ROOT = path.resolve(FRONTEND, '..')

const LOGO_SRC = path.join(ROOT, 'logo')
const PUBLIC_DIR = path.join(FRONTEND, 'public')
const LOGO_DEST = path.join(PUBLIC_DIR, 'logo')
const SOURCE_PNG = path.join(LOGO_SRC, 'rosetta-primary-icon.png')

const ensureDir = p => fs.mkdirSync(p, { recursive: true })
ensureDir(LOGO_DEST)
ensureDir(PUBLIC_DIR)

// ---------------------------------------------------------------
// 1) Copy ALL source logo assets (PNG) to public/logo/
// ---------------------------------------------------------------
console.log('[1/4] Copy logo assets to public/logo/ ...')
const copyList = fs.readdirSync(LOGO_SRC).filter(f => /\.(png|svg|jpg|jpeg|webp)$/i.test(f))
for (const name of copyList) {
  const src = path.join(LOGO_SRC, name)
  const dst = path.join(LOGO_DEST, name)
  fs.copyFileSync(src, dst)
  console.log(`  · ${name} → /logo/${name} (${fs.statSync(src).size} bytes)`)
}

if (!fs.existsSync(SOURCE_PNG)) {
  throw new Error(`Missing required source PNG: ${SOURCE_PNG}`)
}

// ---------------------------------------------------------------
// 2) Resize PNG favicon variants (sharp)
// ---------------------------------------------------------------
console.log('[2/4] Resize PNG favicon variants with sharp ...')
const PNG_SIZES = [16, 32, 48, 64, 128, 180, 192, 512]
const resizedFiles = {} // size → absolute path
const sourceBuf = fs.readFileSync(SOURCE_PNG)

for (const size of PNG_SIZES) {
  const out = path.join(PUBLIC_DIR, `favicon-${size}x${size}.png`)
  await sharp(sourceBuf, { failOnError: false })
    .resize(size, size, { fit: 'contain', background: { r: 0, g: 0, b: 0, alpha: 0 } })
    .png({ compressionLevel: 9, palette: false })
    .toFile(out)
  resizedFiles[size] = out
  const stat = fs.statSync(out)
  console.log(`  · favicon-${size}x${size}.png → ${stat.size} bytes`)
}

// Extra names used by nuxt.config head links
fs.copyFileSync(resizedFiles[180], path.join(PUBLIC_DIR, 'apple-touch-icon.png'))
fs.copyFileSync(resizedFiles[192], path.join(PUBLIC_DIR, 'android-chrome-192x192.png'))
fs.copyFileSync(resizedFiles[512], path.join(PUBLIC_DIR, 'android-chrome-512x512.png'))
console.log('  · aliases: apple-touch-icon.png / android-chrome-192x192.png / android-chrome-512x512.png')

// ---------------------------------------------------------------
// 3) Build multi-size favicon.ico (png-to-ico library)
// ---------------------------------------------------------------
console.log('[3/4] Assemble favicon.ico with png-to-ico library ...')
const ICO_SIZES = [16, 24, 32, 48, 64, 128, 256]
// png-to-ico accepts buffers or file-path strings;
// we need sharp to generate 24 and 256 as well.
for (const size of ICO_SIZES) {
  if (!resizedFiles[size]) {
    const out = path.join(PUBLIC_DIR, `favicon-${size}x${size}-tmp.png`)
    await sharp(sourceBuf, { failOnError: false })
      .resize(size, size, { fit: 'contain', background: { r: 0, g: 0, b: 0, alpha: 0 } })
      .png({ compressionLevel: 9 })
      .toFile(out)
    resizedFiles[size] = out
  }
}

const icoInputs = ICO_SIZES.map(s => fs.readFileSync(resizedFiles[s]))
const icoBuffer = await pngToIco(icoInputs)
const icoPath = path.join(PUBLIC_DIR, 'favicon.ico')
fs.writeFileSync(icoPath, icoBuffer)
console.log(`  · favicon.ico (${ICO_SIZES.length} embedded sizes) → ${fs.statSync(icoPath).size} bytes`)

// Clean up temporary intermediate PNGs (keep standard 16/32/48/64/128/180/192/512 only)
for (const size of [24, 256]) {
  const tmp = path.join(PUBLIC_DIR, `favicon-${size}x${size}-tmp.png`)
  if (fs.existsSync(tmp)) fs.unlinkSync(tmp)
}

// ---------------------------------------------------------------
// 4) site.webmanifest (PWA / Android icon metadata)
// ---------------------------------------------------------------
console.log('[4/4] Write site.webmanifest ...')
const manifest = {
  name: 'Rosetta',
  short_name: 'Rosetta',
  description: '穿越语言的边界 · Modern personal blog',
  icons: [
    { src: '/android-chrome-192x192.png', sizes: '192x192', type: 'image/png', purpose: 'any maskable' },
    { src: '/android-chrome-512x512.png', sizes: '512x512', type: 'image/png', purpose: 'any maskable' }
  ],
  theme_color: '#6366f1',
  background_color: '#ffffff',
  display: 'standalone',
  start_url: '/'
}
fs.writeFileSync(path.join(PUBLIC_DIR, 'site.webmanifest'), JSON.stringify(manifest, null, 2) + '\n')
console.log('  · site.webmanifest written')

// Final sanity stats
const finalSizes = [
  'favicon.ico',
  'favicon-16x16.png',
  'favicon-32x32.png',
  'favicon-48x48.png',
  'apple-touch-icon.png',
  'site.webmanifest',
  'logo/rosetta-primary-icon.png',
  'logo/rosetta-monochrome-icon.png'
].map((p) => {
  const full = path.join(PUBLIC_DIR, p)
  const exists = fs.existsSync(full)
  return `  ${p.padEnd(38)} ${exists ? String(fs.statSync(full).size).padStart(8) + ' B' : '   MISSING'}`
})
console.log('\nFinal output:\n' + finalSizes.join('\n'))
console.log('\n✅ Favicon + logo build complete.')
