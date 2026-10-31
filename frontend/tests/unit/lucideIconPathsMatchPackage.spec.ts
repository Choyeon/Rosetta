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
import { readFileSync } from 'node:fs'
import { join } from 'node:path'
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
