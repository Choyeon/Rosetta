#!/usr/bin/env node
/**
 * Zero-dependency PNG → ICO converter (Windows Vista+ PNG-in-ICO format).
 *
 * Steps:
 *  1. Copy all logo assets from project-root/logo/ → frontend/public/logo/
 *     so Nuxt can serve them at /logo/<file>.
 *  2. Generate ONE multi-size favicon.ico by embedding the same source PNG
 *     multiple times, each declared as a different size entry.
 *     All modern browsers + Windows 10+ support PNG icons inside ICO;
 *     the OS picks the size closest to its needs automatically.
 *  3. Also emit multiple favicon-*.png files (16x16, 32x32, etc.) via
 *     nearest-neighbor downsampling using pure Node.js (no dependencies).
 *
 * Usage:
 *   node scripts/generate-favicon.js
 */

const fs = require('fs')
const path = require('path')
const zlib = require('zlib')

const ROOT = path.resolve(__dirname, '..', '..') // Rosetta root
const LOGO_SRC = path.join(ROOT, 'logo')
const PUBLIC_DIR = path.join(ROOT, 'frontend', 'public')
const LOGO_DEST = path.join(PUBLIC_DIR, 'logo')
const SOURCE_PNG = path.join(LOGO_SRC, 'rosetta-primary-icon.png')

// Sizes that ICO entries will declare. (Declared sizes only; the PNG data
// itself stays at source resolution — the host selects the closest entry
// header and scales the underlying PNG appropriately.)
const ICO_ENTRY_SIZES = [16, 24, 32, 48, 64, 128, 256]
// Sizes for actual resampled favicon-<size>.png files
const FAVICON_PNG_SIZES = [16, 32, 48, 64, 128, 180, 192, 512]

// ============================================================
// Utility
// ============================================================
function ensureDir(p) {
  fs.mkdirSync(p, { recursive: true })
}

function copyDirRecursive(src, dst) {
  ensureDir(dst)
  const entries = fs.readdirSync(src, { withFileTypes: true })
  for (const e of entries) {
    const s = path.join(src, e.name)
    const d = path.join(dst, e.name)
    if (e.isDirectory()) copyDirRecursive(s, d)
    else fs.copyFileSync(s, d)
  }
}

// ============================================================
// Minimal PNG reader/writer (RGBA-only, no filter tricks)
// ============================================================
function readUint32BE(buf, o) {
  return (buf[o] * 0x1000000) + (buf[o + 1] << 16) + (buf[o + 2] << 8) + buf[o + 3]
}
function writeUint32BE(buf, o, v) {
  buf[o]     = (v >>> 24) & 0xff
  buf[o + 1] = (v >>> 16) & 0xff
  buf[o + 2] = (v >>> 8)  & 0xff
  buf[o + 3] = v & 0xff
}
function writeUint16BE(buf, o, v) {
  buf[o]     = (v >>> 8) & 0xff
  buf[o + 1] = v & 0xff
}
function crc32(buf, start, end) {
  let c
  const table = crc32.table || (crc32.table = (() => {
    const t = new Uint32Array(256)
    for (let n = 0; n < 256; n++) {
      c = n
      for (let k = 0; k < 8; k++) c = (c & 1) ? (0xEDB88320 ^ (c >>> 1)) : (c >>> 1)
      t[n] = c >>> 0
    }
    return t
  })())
  let crc = 0xFFFFFFFF
  for (let i = start; i < end; i++) crc = (table[(crc ^ buf[i]) & 0xFF] ^ (crc >>> 8)) >>> 0
  return (crc ^ 0xFFFFFFFF) >>> 0
}

/**
 * Decode PNG → { width, height, pixels: Uint8ClampedArray (RGBA) }
 * Only supports PNGs with: color-type 2 (RGB) or 6 (RGBA), bit-depth 8,
 * non-interlaced, single IDAT. Good enough for our logo PNG.
 */
function decodePng(pngBuf) {
  // 8-byte signature
  if (pngBuf[0] !== 0x89 || pngBuf[1] !== 0x50 || pngBuf[2] !== 0x4E || pngBuf[3] !== 0x47 ||
      pngBuf[4] !== 0x0D || pngBuf[5] !== 0x0A || pngBuf[6] !== 0x1A || pngBuf[7] !== 0x0A) {
    throw new Error('Not a valid PNG (bad signature)')
  }
  let off = 8
  let width = 0, height = 0, bitDepth = 0, colorType = 0
  let idatChunks = []
  let palette = null
  let tRNS = null
  while (off < pngBuf.length) {
    const length = readUint32BE(pngBuf, off); off += 4
    const type = pngBuf.toString('ascii', off, off + 4); off += 4
    const dataStart = off
    const dataEnd = off + length
    if (type === 'IHDR') {
      width = readUint32BE(pngBuf, dataStart)
      height = readUint32BE(pngBuf, dataStart + 4)
      bitDepth = pngBuf[dataStart + 8]
      colorType = pngBuf[dataStart + 9]
      const interlace = pngBuf[dataStart + 12]
      if (interlace !== 0) throw new Error('Interlaced PNG not supported')
      if (bitDepth !== 8) throw new Error(`Only 8-bit PNG supported (got ${bitDepth})`)
    } else if (type === 'PLTE') {
      palette = Buffer.from(pngBuf.slice(dataStart, dataEnd))
    } else if (type === 'tRNS') {
      tRNS = Buffer.from(pngBuf.slice(dataStart, dataEnd))
    } else if (type === 'IDAT') {
      idatChunks.push(Buffer.from(pngBuf.slice(dataStart, dataEnd)))
    } else if (type === 'IEND') {
      off = dataEnd + 4; break
    }
    // skip CRC
    off = dataEnd + 4
  }
  const comp = zlib.inflateSync(Buffer.concat(idatChunks))
  const channels = (colorType === 2) ? 3 : (colorType === 6) ? 4 : (colorType === 3) ? 1 : 0
  if (!channels) throw new Error(`Unsupported color type ${colorType}`)
  const stride = width * channels
  const raw = new Uint8Array(comp.buffer, comp.byteOffset, comp.byteLength)
  const pixels = new Uint8ClampedArray(width * height * 4)
  let src = 0
  let dst = 0
  const prev = new Uint8Array(stride)
  for (let y = 0; y < height; y++) {
    const filter = raw[src++]; const row = raw.subarray(src, src + stride); src += stride
    // Reconstruct
    for (let i = 0; i < stride; i++) {
      let x = row[i]
      const a = i >= channels ? prev[i - channels] : 0
      const b = prev[i]
      const c = i >= channels ? prev[i - channels] : 0
      switch (filter) {
        case 0: break // None
        case 1: x = (x + a) & 0xff; break // Sub
        case 2: x = (x + b) & 0xff; break // Up
        case 3: x = (x + ((a + b) >> 1)) & 0xff; break // Average
        case 4: x = (x + paeth(a, b, c)) & 0xff; break
        default: throw new Error('Unknown filter ' + filter)
      }
      row[i] = x
    }
    // Write RGBA pixels
    if (colorType === 6) {
      for (let i = 0; i < stride; i++) prev[i] = row[i]
      pixels.set(new Uint8ClampedArray(row.buffer, row.byteOffset, stride), dst)
      dst += stride
    } else if (colorType === 2) {
      for (let i = 0; i < stride; i++) prev[i] = row[i]
      for (let i = 0; i < width; i++) {
        pixels[dst++] = row[i * 3 + 0]
        pixels[dst++] = row[i * 3 + 1]
        pixels[dst++] = row[i * 3 + 2]
        pixels[dst++] = 255
      }
    } else if (colorType === 3 && palette) {
      for (let i = 0; i < width; i++) prev[i] = row[i]
      for (let i = 0; i < width; i++) {
        const idx = row[i]
        const p = idx * 3
        pixels[dst++] = palette[p]
        pixels[dst++] = palette[p + 1]
        pixels[dst++] = palette[p + 2]
        pixels[dst++] = (tRNS && idx < tRNS.length) ? tRNS[idx] : 255
      }
    }
  }
  return { width, height, pixels }
}

function paeth(a, b, c) {
  const p = a + b - c
  const pa = Math.abs(p - a), pb = Math.abs(p - b), pc = Math.abs(p - c)
  if (pa <= pb && pa <= pc) return a
  if (pb <= pc) return b
  return c
}

/**
 * Encode RGBA pixels → PNG buffer
 */
function encodePng(width, height, pixels) {
  const channels = 4
  const stride = width * channels
  const raw = Buffer.alloc((stride + 1) * height)
  let dst = 0
  for (let y = 0; y < height; y++) {
    raw[dst++] = 0 // filter: none
    for (let x = 0; x < stride; x++) raw[dst++] = pixels[y * stride + x]
  }
  const comp = zlib.deflateSync(raw, { level: 9 })
  // Build chunks
  function chunk(type, data) {
    const len = Buffer.alloc(4); writeUint32BE(len, 0, data.length)
    const tbuf = Buffer.from(type, 'ascii')
    const crcBuf = Buffer.alloc(4)
    const body = Buffer.concat([tbuf, data])
    writeUint32BE(crcBuf, 0, crc32(body, 0, body.length))
    return Buffer.concat([len, body, crcBuf])
  }
  const sig = Buffer.from([0x89, 0x50, 0x4E, 0x47, 0x0D, 0x0A, 0x1A, 0x0A])
  const ihdr = Buffer.alloc(13)
  writeUint32BE(ihdr, 0, width)
  writeUint32BE(ihdr, 4, height)
  ihdr[8] = 8   // bit depth
  ihdr[9] = 6   // color type RGBA
  ihdr[10] = 0; ihdr[11] = 0; ihdr[12] = 0
  return Buffer.concat([
    sig,
    chunk('IHDR', ihdr),
    chunk('IDAT', comp),
    chunk('IEND', Buffer.alloc(0))
  ])
}

// ============================================================
// Image resampling (nearest-neighbor, good enough for icons)
// ============================================================
function nearestNeighbor(src, sw, sh, dw, dh) {
  const out = new Uint8ClampedArray(dw * dh * 4)
  const xScale = sw / dw, yScale = sh / dh
  for (let y = 0; y < dh; y++) {
    const sy = Math.min(sh - 1, Math.floor(y * yScale)) * sw * 4
    const dy = y * dw * 4
    for (let x = 0; x < dw; x++) {
      const sx = Math.min(sw - 1, Math.floor(x * xScale)) * 4
      const i = sy + sx, j = dy + x * 4
      out[j] = src[i]; out[j + 1] = src[i + 1]; out[j + 2] = src[i + 2]; out[j + 3] = src[i + 3]
    }
  }
  return out
}

// ============================================================
// ICO writer (PNG-in-ICO, Windows Vista+ compatible)
// Each entry is just the same original PNG re-encoded but with a
// declared size header. This is what favicon.ico sites expect and
// produces a ~50–200KB multi-size icon (all sizes are honored via
// the image size field; the OS decoder picks the closest match and
// scales internally if it needs a different dimension).
// ============================================================
function buildIco(/* image list */ entries) {
  // entries: [{ sizeBytes: number, width: number, height: number, png: Buffer }]
  const headerSize = 6
  const dirEntrySize = 16
  const entryCount = entries.length
  const dirSize = headerSize + dirEntrySize * entryCount
  // Determine offsets
  let dataOffset = dirSize
  const header = Buffer.alloc(dirSize)
  // ICONDIR
  header.writeUInt16LE(0, 0) // reserved
  header.writeUInt16LE(1, 2) // type: ICO
  header.writeUInt16LE(entryCount, 4)
  const bufs = [header]
  for (let i = 0; i < entryCount; i++) {
    const e = entries[i]
    const dirOff = 6 + i * 16
    header[dirOff] = e.width >= 256 ? 0 : e.width
    header[dirOff + 1] = e.height >= 256 ? 0 : e.height
    header[dirOff + 2] = 0 // color count
    header[dirOff + 3] = 0 // reserved
    header.writeUInt16LE(1, dirOff + 4) // planes
    header.writeUInt16LE(32, dirOff + 6) // bit count
    header.writeUInt32LE(e.sizeBytes, dirOff + 8)
    header.writeUInt32LE(dataOffset, dirOff + 12)
    dataOffset += e.sizeBytes
    bufs.push(e.png)
  }
  return Buffer.concat(bufs)
}

// ============================================================
// Main
// ============================================================
function main() {
  console.log('[favicon] Project root :', ROOT)
  console.log('[favicon] Logo source   :', LOGO_SRC)
  console.log('[favicon] Frontend public:', PUBLIC_DIR)

  if (!fs.existsSync(SOURCE_PNG)) {
    throw new Error(`Source PNG not found: ${SOURCE_PNG}. Please place rosetta-primary-icon.png in /logo folder.`)
  }

  ensureDir(PUBLIC_DIR)

  // 1) Copy logo assets
  if (fs.existsSync(LOGO_SRC)) {
    console.log('[favicon] Copying logo/ → frontend/public/logo/ …')
    copyDirRecursive(LOGO_SRC, LOGO_DEST)
    const count = fs.readdirSync(LOGO_DEST).length
    console.log(`[favicon] … copied ${count} entries.`)
  } else {
    console.warn('[favicon] ⚠ /logo dir missing; skipping logo copy.')
  }

  // 2) Decode source
  console.log('[favicon] Decoding source PNG …')
  const srcBuf = fs.readFileSync(SOURCE_PNG)
  const { width: sw, height: sh, pixels } = decodePng(srcBuf)
  console.log(`[favicon] … source is ${sw} × ${sh} (${Math.round(srcBuf.length / 1024)} KB).`)

  // 3) Resample + write favicon-<N>.png (for Android/apple-touch-icon)
  const sizesProduced = []
  for (const sz of FAVICON_PNG_SIZES) {
    const dw = sz, dh = sz
    const resampled = nearestNeighbor(pixels, sw, sh, dw, dh)
    const png = encodePng(dw, dh, resampled)
    const fname = sz === 180 ? `apple-touch-icon.png` :
                  sz === 192 ? `android-chrome-192x192.png` :
                  sz === 512 ? `android-chrome-512x512.png` :
                  `favicon-${sz}x${sz}.png`
    const destPath = path.join(PUBLIC_DIR, fname)
    fs.writeFileSync(destPath, png)
    sizesProduced.push({ fname, sizeBytes: png.length })
  }
  console.log('[favicon] PNG icons written:', sizesProduced.map(s => `${s.fname} (${Math.round(s.sizeBytes/1024)} KB)`).join(', '))

  // 4) Build favicon.ico: multi-size entries. We encode the source at
  //    resampled sizes so each ICO entry truly contains the declared size.
  const icoEntries = []
  for (const sz of ICO_ENTRY_SIZES) {
    const dw = sz, dh = sz
    const resampled = nearestNeighbor(pixels, sw, sh, dw, dh)
    const png = encodePng(dw, dh, resampled)
    icoEntries.push({ width: dw, height: dh, sizeBytes: png.length, png })
  }
  const icoBuf = buildIco(icoEntries)
  const icoPath = path.join(PUBLIC_DIR, 'favicon.ico')
  fs.writeFileSync(icoPath, icoBuf)
  console.log(`[favicon] favicon.ico written (${icoEntries.length} sizes, ${Math.round(icoBuf.length / 1024)} KB).`)

  // 5) Write PWA-ish site.webmanifest
  const manifest = {
    name: 'Rosetta',
    short_name: 'Rosetta',
    description: 'Crossing language boundaries · Modern personal blog system.',
    icons: [
      { src: '/android-chrome-192x192.png', sizes: '192x192', type: 'image/png' },
      { src: '/android-chrome-512x512.png', sizes: '512x512', type: 'image/png' }
    ],
    theme_color: '#6366f1',
    background_color: '#ffffff',
    display: 'standalone'
  }
  fs.writeFileSync(path.join(PUBLIC_DIR, 'site.webmanifest'), JSON.stringify(manifest, null, 2) + '\n')
  console.log('[favicon] site.webmanifest written.')

  console.log('[favicon] ✅ All done.')
}

try {
  main()
} catch (e) {
  console.error('[favicon] ❌ Failed:', e && e.stack || e)
  process.exit(1)
}
