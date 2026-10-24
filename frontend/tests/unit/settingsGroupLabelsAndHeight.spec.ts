/**
 * 批次 #71 契约：站点设置页"每个选项的标签说的是它自己的事" + 主区自然增高。
 *
 * 两类真实缺陷：
 *   ① 标签表按 key 单源、跨分组撞名就串味——分组键里 `enable`/`title`/`description`/
 *      `subtitle`/`icp_number` 各有 2–4 个组在用，而通用表按评论组命名，于是公告组的
 *      "启用站点公告"显示成"启用评论功能"。这类错位不会报错，只会让管理员按字面去拨
 *      另一个功能的开关。
 *   ② 主区曾用 `md:h-[calc(100vh-220px)]` 固定高度 + 内层 ScrollArea，长分组在盒子里
 *      内滚：Tab 键把字段滚出可视区、滚动条不明显，看起来"设置项不见了"。
 * 分组键清单以后端 `_default_<group>()` 为唯一真源，本用例直接读它，不在前端再抄一份。
 */
import { describe, it, expect } from 'vitest'
import { existsSync, readFileSync } from 'node:fs'
import process from 'node:process'

const FE_ROOT = process.cwd().replace(/[\\/]$/, '')
const SETTINGS_VUE = `${FE_ROOT}/pages/admin/system/settings.vue`
// 后端设置模块在仓库根的 backend/ 下，vitest 的 cwd 是 frontend/
const GROUPS_PY = `${FE_ROOT}/../backend/api/settings_groups.py`

/** 从 _default_<group>() 抠出该组的键清单（顶层多行字符串字面量的键）。 */
function backendGroups(): Record<string, string[]> {
  expect(existsSync(GROUPS_PY), `${GROUPS_PY} 不存在`).toBe(true)
  const raw = readFileSync(GROUPS_PY, 'utf8')
  const marks: Array<{ g: string, start: number }> = []
  // 只认无参的数据默认函数：`_default_for(group)` 是分发器，抠它会多出一个假分组
  const re = /^def\s+_default_(\w+)\(\)\s*->\s*dict:/gm
  let m: RegExpExecArray | null
  while ((m = re.exec(raw))) {
    if (m[1]) marks.push({ g: m[1], start: m.index })
  }
  marks.push({ g: '__end__', start: raw.length })
  const out: Record<string, string[]> = {}
  for (let i = 0; i < marks.length - 1; i++) {
    const cur = marks[i]
    const next = marks[i + 1]
    if (!cur || !next) continue
    const seg = raw.slice(cur.start, next.start)
    // 只认 `return {` 里正好缩进 8 空格的键：GROUPS 注册表（4 空格、值是指针）不算设置项
    const keys = [...seg.matchAll(/^ {8}(?:"|')([a-z0-9_]+)(?:"|')\s*:/gm)].map(x => x[1] ?? '').filter(Boolean)
    out[cur.g] = [...new Set(keys)]
  }
  return out
}

/** 抠出 .vue 里的通用标签表与 GROUP_LABELS 覆写表（只认 `key: '文案'` 形态）。 */
function labelTables() {
  const src = readFileSync(SETTINGS_VUE, 'utf8')
  const flatStart = src.indexOf('const label = {')
  const flatEnd = src.indexOf('[key] ?? key', flatStart)
  expect(flatStart, '找不到通用标签表').toBeGreaterThan(-1)
  expect(flatEnd, '通用标签表结尾锚点丢失').toBeGreaterThan(flatStart)
  const grab = (block: string) => {
    const map: Record<string, string> = {}
    for (const m of block.matchAll(/(?:^|[,{\s])"?([a-z0-9_]+)"?\s*:\s*'([^']*)'/gm)) {
      if (m[1]) map[m[1]] = m[2] ?? ''
    }
    return map
    // 说明：flat 表里 value 全用单引号，跨行对象用下面的 GROUP_LABELS 段单独抠
  }
  const flat = grab(src.slice(flatStart, flatEnd))

  const glStart = src.indexOf('const GROUP_LABELS')
  const glEnd = src.indexOf('function inferSchema', glStart)
  expect(glStart, '找不到 GROUP_LABELS').toBeGreaterThan(-1)
  const block = src.slice(glStart, glEnd)
  const perGroup: Record<string, Record<string, string>> = {}
  const groupRe = /^ {2}([a-z_]+): \{$/gm
  let gm: RegExpExecArray | null
  const groupMarks: Array<{ g: string, start: number }> = []
  while ((gm = groupRe.exec(block))) {
    if (gm[1]) groupMarks.push({ g: gm[1], start: gm.index })
  }
  groupMarks.push({ g: '__end', start: block.length })
  for (let i = 0; i < groupMarks.length - 1; i++) {
    const cur = groupMarks[i]
    const next = groupMarks[i + 1]
    if (!cur || !next) continue
    perGroup[cur.g] = grab(block.slice(cur.start, next.start))
  }
  return { flat, perGroup }
}

/** 页面实际解析出的标签：分组覆写优先，其次通用表，最后裸 key。 */
function resolveLabel(key: string, group: string, flat: Record<string, string>, perGroup: Record<string, Record<string, string>>) {
  return perGroup[group]?.[key] ?? flat[key] ?? key
}

// donate.methods 走专用收款码编辑器，不进通用 schema（有意不带标签）
const EDITOR_ONLY: Record<string, string[]> = { donate: ['methods'] }

describe('站点设置：分组键 ↔ 标签', () => {
  const groups = backendGroups()
  const { flat, perGroup } = labelTables()

  it('分组清单非空且都来自后端 _default_ 函数', () => {
    const keys = Object.keys(groups)
    expect(keys.length).toBeGreaterThanOrEqual(14)
    for (const [g, ks] of Object.entries(groups)) {
      expect(ks.length, `${g} 组没抠到键`).toBeGreaterThan(0)
    }
  })

  it('每个分组键都有可读标签（不得渲染裸 key）', () => {
    const bare: string[] = []
    for (const [g, ks] of Object.entries(groups)) {
      for (const k of ks) {
        if (EDITOR_ONLY[g]?.includes(k)) continue
        const label = resolveLabel(k, g, flat, perGroup)
        if (label === k) bare.push(`${g}.${k}`)
      }
    }
    expect(bare, `这些设置项会把裸 key 当标签渲染：\n${bare.join('\n')}`).toEqual([])
  })

  it('跨分组撞名的键必须各自有分组覆写，且文案互不相同', () => {
    const owners: Record<string, string[]> = {}
    for (const [g, ks] of Object.entries(groups)) {
      for (const k of ks) (owners[k] ||= []).push(g)
    }
    const collided = Object.entries(owners).filter(([, gs]) => gs.length > 1)
    expect(collided.length, '分组键撞名清单为空，本用例失去意义').toBeGreaterThan(0)
    for (const [key, gs] of collided) {
      const labels = gs.map(g => resolveLabel(key, g, flat, perGroup))
      const distinct = new Set(labels)
      expect(
        distinct.size,
        `键 ${key} 被 ${gs.join('/')} 共用，标签却有重复（说明缺分组覆写）：${labels.join(' | ')}`
      ).toBe(gs.length)
    }
  })

  it('公告组的开关不得写成评论', () => {
    expect(resolveLabel('enable', 'notice', flat, perGroup)).toContain('公告')
    expect(resolveLabel('enable', 'notice', flat, perGroup)).not.toContain('评论')
    expect(resolveLabel('title', 'notice', flat, perGroup)).toContain('公告')
  })

  it('Hero 组的开关说清它管首页整块区域', () => {
    const label = resolveLabel('enable', 'hero', flat, perGroup)
    expect(label).toContain('Hero')
    expect(label).not.toContain('评论')
  })

  it('只有评论组的 enable 才允许出现"评论功能"字样', () => {
    const wrong: string[] = []
    for (const [g, ks] of Object.entries(groups)) {
      if (g === 'comments') continue
      for (const k of ks) {
        const label = resolveLabel(k, g, flat, perGroup)
        if (k === 'enable' && label.includes('评论')) wrong.push(`${g}.${k}: ${label}`)
      }
    }
    expect(wrong, `非评论组却显示了评论文案：\n${wrong.join('\n')}`).toEqual([])
  })
})

describe('站点设置：主区自然增高（不再固定高度内滚）', () => {
  const src = readFileSync(SETTINGS_VUE, 'utf8')

  it('不再出现 calc(100vh-…) 固定高度', () => {
    expect(src).not.toMatch(/h-\[calc\(100vh-220px\)\]/)
  })

  it('不再使用 ScrollArea（表单滚动交给页面）', () => {
    expect(src).not.toMatch(/<ScrollArea/)
    expect(src).not.toMatch(/from '~~\/components\/ui\/scroll-area'/)
  })

  /**
   * sticky 顶距必须让开 64px 的后台顶栏（h-16 sticky top-0）：
   * 曾经的 `md:top-4` 会把分组栏整条停在顶栏背后，看起来像"分组栏消失了"。
   */
  it('左侧分组栏 sticky 且顶距对齐后台顶栏（top-20）', () => {
    expect(src).toMatch(/md:sticky md:top-20/)
    expect(src).not.toMatch(/md:sticky md:top-4/)
  })
})
