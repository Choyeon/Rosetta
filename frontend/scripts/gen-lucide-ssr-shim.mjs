/**
 * 重新生成 lib/lucide-svg-icons-all.ts（v2 —— 真实 iconNode 数据版）：
 *
 * SSR 端 @lucide/vue（vite resolveId 指向本文件）渲染结果必须与客户端
 * 真实 @lucide/vue 字节级一致，否则每个图标都是 hydration mismatch：
 *   - v1 的 rect placeholder 导致 svg 子节点 rect vs path 节点级 mismatch；
 *   - 手写 lucide-svg-icons.ts 的 path/class 与真实包不一致（class 缺
 *     `lucide lucide-x-icon lucide-x` 前缀、width/height 缺失、个别 d 数据偏差）。
 *
 * v2 直接从 node_modules/@lucide/vue 的 esm icons 提取真实 __iconNode，
 * 复刻 createLucideIcon 的确定渲染（无 Context provider 时全部走默认值）。
 *
 * 用法：node scripts/gen-lucide-ssr-shim.mjs
 */
import { readFileSync, writeFileSync, readdirSync } from 'node:fs'
import { dirname, resolve } from 'node:path'
import { fileURLToPath } from 'node:url'

const __dirname = dirname(fileURLToPath(import.meta.url))
const root = resolve(__dirname, '..')
const pkgDir = resolve(root, 'node_modules/.pnpm').length && (() => {
  const base = resolve(root, 'node_modules/.pnpm')
  const dir = readdirSync(base).find(d => d.startsWith('@lucide+vue@'))
  return resolve(base, dir, 'node_modules/@lucide/vue')
})()
const iconsDir = resolve(pkgDir, 'dist/esm/icons')
const dts = readFileSync(resolve(pkgDir, 'dist/lucide-vue.d.ts'), 'utf-8')

// ---- 1. 解析 declared 名（canonical）与 kebab（来自 lucide.dev/icons/<kebab> URL）----
// @component @name AArrowDown ... @see .../icons/a-arrow-down ... declare const AArrowDown: LucideIcon;
const declared = new Map() // canonicalName -> kebab
for (const m of dts.matchAll(/@name ([A-Za-z0-9_]+)[\s\S]{0,2000}?icons\/([a-z0-9-]+)[\s\S]{0,2000}?declare const ([A-Za-z0-9_]+): LucideIcon;/g)) {
  if (m[1] !== m[3]) continue // @name 与 declare 名必须一致，防止跨块误匹配
  declared.set(m[3], m[2])
}

// ---- 2. 解析导出语句（可能跨多行）：export { A, B as C, ... } -> exportedName -> canonicalName ----
const exportMatch = dts.match(/^export \{[\s\S]*?\}/m)
const aliasOf = new Map() // exportedName -> canonicalName
for (const part of (exportMatch?.[0] ?? '').replace(/^export \{|\}$/g, '').split(',')) {
  const seg = part.trim()
  if (!seg) continue
  const asMatch = seg.match(/^([\w]+) as ([\w]+)$/)
  if (asMatch) aliasOf.set(asMatch[2], asMatch[1])
  else aliasOf.set(seg, seg)
}

// ---- 3. 提取每个 canonical 的 __iconNode ----
function extractIconNode(kebab) {
  const file = resolve(iconsDir, `${kebab}.mjs`)
  const src = readFileSync(file, 'utf-8')
  const m = src.match(/const __iconNode = (\[[\s\S]*?\]);\s*\n/)
  if (!m) throw new Error(`no __iconNode in ${file}`)
  // 字面量含未加引号的键（d: / key:）——是合法 JS，直接 eval
  return new Function(`return ${m[1]}`)()
}

// ---- 4. 生成 ----
const fallbackStub = new Set()
const canonicalEmitted = new Map() // canonicalName -> kebab（已 emit）
const lines = []
const aliasLines = []

// 排序：canonical 优先 emit，别名 re-export
const allExported = [...aliasOf.keys()].sort()
const emittedNames = new Set() // 已产出 export 的名字（防自别名重复：A as A + A）
for (const exportedName of allExported) {
  if (exportedName === 'LucideSSR' || exportedName === 'default') continue
  const canonicalName = aliasOf.get(exportedName)
  const kebab = declared.get(canonicalName)
  if (canonicalName && kebab && !canonicalEmitted.has(canonicalName)) {
    let iconNode
    try {
      iconNode = extractIconNode(kebab)
    } catch {
      fallbackStub.add(canonicalName)
    }
    if (iconNode) {
      canonicalEmitted.set(canonicalName, kebab)
      lines.push(`export const ${canonicalName} = ssrIcon('${kebab}', ${JSON.stringify(iconNode)})`)
      emittedNames.add(canonicalName)
      // 排序时别名可能排在 canonical 之前：emit canonical 后补发本别名
      if (exportedName !== canonicalName) {
        aliasLines.push(`export { ${canonicalName} as ${exportedName} }`)
        emittedNames.add(exportedName)
      }
      continue
    }
  }
  if (canonicalEmitted.has(canonicalName) && exportedName !== canonicalName && !emittedNames.has(exportedName)) {
    aliasLines.push(`export { ${canonicalName} as ${exportedName} }`)
    emittedNames.add(exportedName)
  }
}

const header = `/**
 * SSR-only shim that Vite resolver substitutes for \`@lucide/vue\` when
 * building/rendering on the server (see \`rosetta-lucide-ssr-fix\` in nuxt.config.ts).
 *
 * 本文件由 scripts/gen-lucide-ssr-shim.mjs 生成（勿手改）。
 *
 * v2（2026-10-01）：从 @lucide/vue dist esm icons 提取**真实 __iconNode**，
 * 服务端渲染与客户端真实包字节级一致（class 前缀 / width/height / path 数据
 * 全部对齐）——v1 的 rect placeholder 与手写 path 都会导致 hydration mismatch。
 *
 * 渲染语义复刻 createLucideIcon/Icon.mjs 的确定性路径（无 Provider 上下文）：
 *   svg 属性 = defaultAttributes，class = \`lucide lucide-<kebab>-icon lucide-<kebab>\`，
 *   其余 attrs（class/style 等）经 inheritAttrs fallthrough 合并，与客户端一致。
 *
 * Client builds use the original npm: @lucide/vue package (paths correct).
 */
import { defineComponent, h } from 'vue'
import type { DefineComponent } from 'vue'

type IconNode = ReadonlyArray<readonly [string, Record<string, unknown>]>

const defaultAttrs: Record<string, string | number> = {
  'xmlns': 'http://www.w3.org/2000/svg',
  'width': 24,
  'height': 24,
  'viewBox': '0 0 24 24',
  'fill': 'none',
  'stroke': 'currentColor',
  'stroke-width': 2,
  'stroke-linecap': 'round',
  'stroke-linejoin': 'round'
}

const ssrIcon = (name: string, iconNode: IconNode): DefineComponent =>
  defineComponent({
    name: \`LucideSSR_\${name}\`,
    inheritAttrs: true,
    setup() {
      return () =>
        h(
          'svg',
          { ...defaultAttrs, class: \`lucide lucide-\${name}-icon lucide-\${name}\` },
          iconNode.map(([tag, props]) => h(tag, props))
        )
    }
  }) as unknown as DefineComponent

// 极少数无法解析 iconNode 的名字走 rect 占位（仍保证 svg first-child 同构）
const stubIcon = (name: string): DefineComponent =>
  defineComponent({
    name: \`LucideSSR_stub_\${name}\`,
    inheritAttrs: true,
    setup() {
      return () =>
        h('svg', { ...defaultAttrs, class: \`lucide lucide-\${name}-icon lucide-\${name}\` }, [
          h('rect', { x: 3, y: 3, width: 18, height: 18, rx: 2, ry: 2, opacity: 0 })
        ])
    }
  }) as unknown as DefineComponent

// Dynamic fallback：任何未静态导出的名字仍可解析（Proxy）
const base: Record<string, DefineComponent> = {}
const withExports = new Proxy(base, {
  get(target, prop, receiver) {
    if (typeof prop !== 'string') return Reflect.get(target, prop, receiver)
    if (prop in target) return Reflect.get(target, prop, receiver)
    if (prop === 'default') return Reflect.get(target, prop, receiver)
    if (!prop.startsWith('__') && /^[A-Z][A-Za-z0-9]*$/.test(prop)) {
      const stub = stubIcon(prop)
      target[prop] = stub
      return stub
    }
    return Reflect.get(target, prop, receiver)
  },
  has(target, prop) {
    if (typeof prop === 'string' && /^[A-Z][A-Za-z0-9]*$/.test(prop)) return true
    return Reflect.has(target, prop)
  }
})
export default withExports
export const LucideSSR = withExports

// ==== Exhaustive real-data exports（${declared.size} canonical icons）====
`

if (fallbackStub.size > 0) {
  for (const n of fallbackStub) lines.push(`export const ${n} = stubIcon('${n}')`)
}

writeFileSync(resolve(root, 'lib/lucide-svg-icons-all.ts'), header + [...lines, ...aliasLines].join('\n') + '\n')
console.log(`generated: canonical=${lines.length} aliases=${aliasLines.length} stubFallback=${fallbackStub.size}`)
