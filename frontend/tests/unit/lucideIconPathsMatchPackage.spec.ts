/**
 * lib/lucide-svg-icons.ts 的字形数据必须与**已安装的** @lucide/vue 逐节点相等。
 *
 * 为什么钉这条：这个 lib 是把 lucide 的 path 逐条抄成常量（服务端渲染成稳定 <svg>，
 * 避开当年组件包在 SSR 吐注释节点导致的 hydration mismatch）。抄件一旦和包里的版本
 * 不同，同一个图标在两种来源下就是两种字形——批次 #144 实测踩到：首页「最新动态」侧栏
 * （走常量）与文章卡（走 @lucide/vue 的 Heart）的爱心 path 完全不同。
 *
 * 名字→文件不手写映射表，直接读包的 barrel（`dist/esm/lucide-vue.mjs` 的 re-export 行）：
 * lucide 1.x 把 bar-chart-3 / alert-triangle / loader-2 / globe-2 / smile 全改了名，
 * 包里保留旧导出名指向新文件，所以"包自己承认的导出名"是唯一不会烂的别名来源。
 * 升级 @lucide/vue 而没同步这份抄件 ⇒ 本文件直接红，而不是等访客发现两个爱心。
 */
import { readdirSync, readFileSync } from 'node:fs'
import { join, relative } from 'node:path'
import { describe, expect, it } from 'vitest'

const ROOT = join(__dirname, '..', '..')
const LIB = join(ROOT, 'lib', 'lucide-svg-icons.ts')
const PKG_ESM = join(ROOT, 'node_modules', '@lucide', 'vue', 'dist', 'esm')
const REPO_BLOCK_RE = /^export const (\w+) = S\(undefined,\n(.*?)^\)/gms

type IconNode = [string, [string, string][]]

function nodesToSet(nodes: IconNode[]): string[] {
  return nodes.map(([tag, attrs]) => `${tag}|${attrs.map(([k, v]) => `${k}=${v}`).sort().join('&')}`).sort()
}

/** 仓内抄件：`export const X = S(undefined, h('path', { d: '…' }), …)`。 */
function repoIcons(): Map<string, string[]> {
  const src = readFileSync(LIB, 'utf8')
  const out = new Map<string, string[]>()
  for (const m of src.matchAll(REPO_BLOCK_RE)) {
    const name = m[1]
    const body = m[2]
    if (!name || !body)
      continue
    const nodes: IconNode[] = []
    for (const n of body.matchAll(/h\('(\w+)',\s*\{([^}]*)\}\)/g)) {
      const tag = n[1]
      const attrs = n[2]
      if (!tag || !attrs)
        continue
      nodes.push([tag, [...attrs.matchAll(/(\w+):\s*'([^']*)'/g)].map(k => [k[1]!, k[2]!])])
    }
    out.set(name, nodesToSet(nodes))
  }
  return out
}

/** 包的 barrel：导出名 → 图标文件名（同一行的所有别名各占一条）。 */
function barrelFiles(): Map<string, string> {
  const src = readFileSync(join(PKG_ESM, 'lucide-vue.mjs'), 'utf8')
  const out = new Map<string, string>()
  for (const line of src.split('\n')) {
    const m = line.match(/export \{([^}]*)\} from '\.\/icons\/([^']+)\.mjs'/)
    if (!m)
      continue
    const specs = m[1]
    const file = m[2]
    if (!specs || !file)
      continue
    for (const raw of specs.split(',')) {
      const name = raw.trim().split(' as ').pop()!.trim()
      if (/^[A-Z][A-Za-z0-9]*$/.test(name) && !out.has(name))
        out.set(name, file)
    }
  }
  return out
}

/** 包内的节点数据：`__iconNode = [["path", { d: "…", key: "…" }], …]`（key 不进 DOM，剥掉）。 */
function packageNodes(file: string): string[] {
  const src = readFileSync(join(PKG_ESM, 'icons', `${file}.mjs`), 'utf8')
  const body = src.split('__iconNode = ')[1]?.split('];')[0] ?? ''
  const nodes: IconNode[] = []
  for (const n of body.matchAll(/\[\s*"(\w+)"\s*,\s*\{([^}]*)\}\s*\]/g)) {
    const tag = n[1]
    const attrs = n[2]
    if (!tag || !attrs)
      continue
    const pairs: [string, string][] = [...attrs.matchAll(/(\w+)\s*:\s*"([^"]*)"/g)]
      .filter(k => k[1] !== 'key')
      .map((k): [string, string] => [k[1]!, k[2]!])
    nodes.push([tag, pairs])
  }
  return nodesToSet(nodes)
}

describe('lib/lucide-svg-icons 与 @lucide/vue 的字形数据对账', () => {
  const repo = repoIcons()
  const barrel = barrelFiles()

  it('抄件里有图标可被对账（解析失败要立刻红，而不是恒真）', () => {
    expect(repo.size).toBeGreaterThanOrEqual(70)
    expect(barrel.size).toBeGreaterThan(1000)
  })

  it('每个抄件图标都是包的真实导出名（改名不是靠猜的）', () => {
    const stale = [...repo.keys()].filter(n => !barrel.has(n))
    expect(stale).toEqual([])
  })

  it('每个图标的节点集合与包内数据逐条相等', () => {
    const drifted: string[] = []
    for (const [name, mine] of repo) {
      const file = barrel.get(name)
      if (!file)
        continue
      const theirs = packageNodes(file)
      if (theirs.length === 0 || theirs.join('\n') !== mine.join('\n'))
        drifted.push(`${name} (${theirs.length} vs ${mine.length})`)
    }
    expect(drifted).toEqual([])
  })

  it('爱心与文章卡同源（批次 #144 的原始症状）', () => {
    const heart = repo.get('Heart')?.join('\n') ?? ''
    expect(heart).toContain('M2 9.5a5.5 5.5')
    expect(heart).not.toContain('M19 14c1.49')
  })
})

/**
 * 模板里手写 `d="…"` 的组件是唯一清单（批次 #145）。
 *
 * 为什么钉这条：lib 与组件包同源之后，第三份来源是**抄进模板的字形**——
 * CategoryBadge 的文件夹、TagBadge 的标签、activity 的闪电都各抄了一份旧版 path，
 * 于是同一图标在同一页有两种画法（包里 folder-open 现为 `m6 14 1.5-2.9…`，抄件是 `m6 14 1.45-2.9…`）。
 * 值写包内的图标文件名 ⇒ 该文件每个内联 d 必须逐字节等于那个图标；填 null 的只有品牌标记
 * （octocat 与实心 RSS 用 fill，不是 lucide 的 stroke 图标，无组件可换）。
 * 新抄一个字形而不登记＝本用例红，改图标只能走 <FolderOpen /> 这类组件。
 */
const INLINE_GLYPH_FILES: Record<string, string | null> = {
  'components/AppFooter.vue': null,
  'components/ui/accordion/AccordionTrigger.vue': 'chevron-down',
  'components/ui/breadcrumb/BreadcrumbSeparator.vue': 'chevron-right'
}

function listVue(dir: string, acc: string[] = []): string[] {
  for (const entry of readdirSync(dir, { withFileTypes: true })) {
    if (['node_modules', '.nuxt', 'dist', '.output'].includes(entry.name))
      continue
    const p = join(dir, entry.name)
    if (entry.isDirectory())
      listVue(p, acc)
    else if (entry.name.endsWith('.vue'))
      acc.push(p)
  }
  return acc
}

/** 包内某个图标的 path 数据（逐字节，不做归一——归一就是把漂移藏起来）。 */
function packagePathData(file: string): string[] {
  const src = readFileSync(join(PKG_ESM, 'icons', `${file}.mjs`), 'utf8')
  return [...src.matchAll(/\bd:\s*"([^"]*)"/g)].map(m => m[1]).filter(Boolean) as string[]
}

describe('模板内联字形必须有登记且与包内数据一致', () => {
  const found = new Map<string, string[]>()
  for (const abs of ['components', 'pages', 'layouts'].flatMap(d => listVue(join(ROOT, d)))) {
    const rel = relative(ROOT, abs).split('\\').join('/')
    const ds = [...readFileSync(abs, 'utf8').matchAll(/\sd="([^"]+)"/g)].map(m => m[1]).filter(Boolean) as string[]
    if (ds.length > 0)
      found.set(rel, ds)
  }

  it('内联字形清单非空且解析到位（恒真守卫先排除）', () => {
    expect(found.size).toBe(Object.keys(INLINE_GLYPH_FILES).length)
    expect(packagePathData('chevron-down')).toEqual(['m6 9 6 6 6-6'])
  })

  it('没有未登记的抄件字形（新增一处即红，逼它改走图标组件）', () => {
    expect([...found.keys()].sort()).toEqual(Object.keys(INLINE_GLYPH_FILES).sort())
  })

  it('已登记抄件的每一条 path 与包内该图标逐字节相等', () => {
    const drifted: string[] = []
    for (const [rel, ds] of found) {
      const icon = INLINE_GLYPH_FILES[rel]
      if (!icon)
        continue
      const theirs = packagePathData(icon)
      for (const d of ds) {
        if (!theirs.includes(d))
          drifted.push(`${rel}: ${d.slice(0, 24)}…`)
      }
    }
    expect(drifted).toEqual([])
  })

  it('批次 #145 的三处抄件已改走组件（源码里不再有旧字形）', () => {
    for (const f of ['components/CategoryBadge.vue', 'components/TagBadge.vue', 'pages/activity.vue']) {
      const src = readFileSync(join(ROOT, f), 'utf8')
      expect(src, f).not.toMatch(/\sd="M/)
    }
    const cat = readFileSync(join(ROOT, 'components', 'CategoryBadge.vue'), 'utf8')
    expect(cat).toContain('import { FolderOpen } from \'@lucide/vue\'')
    const act = readFileSync(join(ROOT, 'pages', 'activity.vue'), 'utf8')
    expect(act).toContain('<Zap class="size-7 text-primary" />')
  })

  it('动态页的类型图标字典只留真正被取用的键，且不再抄任何 path 数据', () => {
    const act = readFileSync(join(ROOT, 'pages', 'activity.vue'), 'utf8')
    // TYPE_ICONS 的键只能来自 ACTIVITY_TYPES：backendToIconKey 只会喂进那五个值
    const dictStart = act.indexOf('const TYPE_ICONS')
    expect(dictStart).toBeGreaterThanOrEqual(0)
    const dict = act.slice(dictStart, dictStart + 400)
    const keys = [...dict.matchAll(/^ {2}(\w+): ([A-Z]\w+),?/gm)].map(m => m[1]!)
    expect(keys.length).toBe(5)
    const typesSource = /const ACTIVITY_TYPES = \[([^\]]*)\]/.exec(act)?.[1]
    expect(typesSource).toBeTruthy()
    const types = typesSource!
      .split(',')
      .map(s => s.trim().replace(/'/g, ''))
      .filter(Boolean)
    expect(keys.sort()).toEqual(types.sort())

    // 第四份抄件的入口封掉：字典里只有组件名，没有任何 d / viewBox 字面量
    expect(act).not.toMatch(/\bd:\s*'[MJ]/)
    expect(act).not.toContain('viewBox:')
    expect(act).not.toContain('getIcon')
    // 旧版闪电（手抄的那种）在整个前端源码里都不该再出现
    expect(act).not.toContain('M13 2 3 14h7l-1 8')
  })

  it('动态页每类型一枚 @lucide/vue 组件，导入名都是包的真实导出（批次 #146）', () => {
    const act = readFileSync(join(ROOT, 'pages', 'activity.vue'), 'utf8')
    const barrel = barrelFiles()
    const imported = /import \{([^}]*)\} from '@lucide\/vue'/.exec(act)?.[1] ?? ''
    const names = imported.split(',').map(s => s.trim()).filter(Boolean)
    expect(names.length).toBeGreaterThanOrEqual(6)
    expect(names.filter(n => !barrel.has(n))).toEqual([])
    for (const n of ['MessageCircle', 'Newspaper', 'History', 'Bell', 'Link2'])
      expect(names).toContain(n)
    expect(act).toContain('const TYPE_ICONS: Record<string, Component> =')
    expect(act).toContain(':is="typeIcon(activityIconKey(item.type))"')
  })
})
