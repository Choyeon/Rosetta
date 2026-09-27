/**
 * 版本历史行级 diff（纯函数，无依赖）
 *
 * 后端 /admin/posts/{id}/revisions/compare 只返回左右两份正文，比对在前端做。
 * 标准 LCS 动态规划；任一侧超过 MAX_LINES 时退化为「整段替换」，
 * 避免超长文章把浏览器算成 O(n·m) 卡顿——退化结果仍正确，只是不够细。
 */

export type DiffLineType = 'same' | 'added' | 'removed'

export interface DiffLine {
  type: DiffLineType
  text: string
}

export const MAX_LINES = 1200

function splitLines(value: string): string[] {
  if (!value || !value.trim()) return []
  return value.replace(/\r\n/g, '\n').split('\n')
}

export function diffLines(before: string, after: string): DiffLine[] {
  const a = splitLines(before)
  const b = splitLines(after)

  if (a.length > MAX_LINES || b.length > MAX_LINES) {
    return [
      ...a.map(text => ({ type: 'removed' as const, text })),
      ...b.map(text => ({ type: 'added' as const, text }))
    ]
  }

  // dp[i][j] = a[i:] 与 b[j:] 的最长公共子序列长度（越界按 0 处理）
  const dp: number[][] = Array.from({ length: a.length + 1 }, () => new Array(b.length + 1).fill(0))
  const at = (row: number, col: number) => dp[row]?.[col] ?? 0
  for (let i = a.length - 1; i >= 0; i--) {
    const row = dp[i] as number[]
    for (let j = b.length - 1; j >= 0; j--) {
      row[j] = a[i] === b[j] ? at(i + 1, j + 1) + 1 : Math.max(at(i + 1, j), at(i, j + 1))
    }
  }

  const out: DiffLine[] = []
  let i = 0
  let j = 0
  while (i < a.length && j < b.length) {
    const left = a[i] as string
    const right = b[j] as string
    if (left === right) {
      out.push({ type: 'same', text: left })
      i++
      j++
    } else if (at(i + 1, j) >= at(i, j + 1)) {
      out.push({ type: 'removed', text: left })
      i++
    } else {
      out.push({ type: 'added', text: right })
      j++
    }
  }
  while (i < a.length) out.push({ type: 'removed', text: a[i++] as string })
  while (j < b.length) out.push({ type: 'added', text: b[j++] as string })
  return out
}

/** diff 摘要：新增/删除行数，供标题旁徽标显示 */
export function diffStats(lines: DiffLine[]): { added: number, removed: number } {
  return {
    added: lines.filter(l => l.type === 'added').length,
    removed: lines.filter(l => l.type === 'removed').length
  }
}

/**
 * 取 i18n 字典里的单一语言文本（标题 / 摘要这类短字段用）。
 * 与 flattenLocalizedContent 分工：短字段平铺成「【zh】…【en】…」会让页头和卡片
 * 把同一句话重复四遍，只有正文需要逐语言铺开比对。
 */
export function pickLocalized(value: unknown): string {
  if (value == null) return ''
  if (typeof value === 'string') return value
  if (typeof value === 'object') {
    const dict = value as Record<string, unknown>
    for (const key of ['zh', 'en']) {
      const text = dict[key]
      if (typeof text === 'string' && text.trim()) return text
    }
    const first = Object.values(dict).find(x => typeof x === 'string' && (x as string).trim())
    return typeof first === 'string' ? first : ''
  }
  return String(value)
}

/** 把 i18n 正文字典压成带语言小标题的单串，供 diff 消费 */
export function flattenLocalizedContent(value: unknown): string {
  if (value == null) return ''
  if (typeof value === 'string') return value
  if (typeof value === 'object') {
    return Object.entries(value as Record<string, unknown>)
      .map(([lang, text]) => `【${lang}】\n${typeof text === 'string' ? text : JSON.stringify(text)}`)
      .join('\n\n')
  }
  return String(value)
}
