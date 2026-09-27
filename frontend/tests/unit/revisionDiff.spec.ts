import { describe, expect, it } from 'vitest'
import { diffLines, diffStats, flattenLocalizedContent, MAX_LINES } from '~~/lib/revisionDiff'

/**
 * 版本历史 diff 纯函数单测：
 * 后端 compare 端点只给两份正文，行级差异完全由前端算，所以差分口径必须自己钉住。
 */
describe('revisionDiff', () => {
  it('识别新增 / 删除 / 未变行', () => {
    const lines = diffLines('A\nB\nC', 'A\nX\nC')
    expect(lines).toEqual([
      { type: 'same', text: 'A' },
      { type: 'removed', text: 'B' },
      { type: 'added', text: 'X' },
      { type: 'same', text: 'C' }
    ])
    expect(diffStats(lines)).toEqual({ added: 1, removed: 1 })
  })

  it('完全相同的内容不产生增删', () => {
    const lines = diffLines('同一份\n正文', '同一份\n正文')
    expect(diffStats(lines)).toEqual({ added: 0, removed: 0 })
    expect(lines.every(l => l.type === 'same')).toBe(true)
  })

  it('空 → 有内容视为纯新增', () => {
    expect(diffStats(diffLines('', '第一行'))).toEqual({ added: 1, removed: 0 })
  })

  it('归一 CRLF，避免换行符差异伪装成改动', () => {
    expect(diffStats(diffLines('a\r\nb', 'a\nb'))).toEqual({ added: 0, removed: 0 })
  })

  it('超过阈值退化为整段替换，结果仍覆盖两侧内容', () => {
    const big = Array.from({ length: MAX_LINES + 5 }, (_, i) => `行${i}`).join('\n')
    const lines = diffLines(big, `${big}\n追加一行`)
    const stats = diffStats(lines)
    expect(stats.added).toBeGreaterThan(0)
    expect(stats.removed).toBeGreaterThan(0)
    // 退化路径不做 LCS，但两侧行数必须都在结果里出现
    expect(lines.filter(l => l.type === 'removed').length).toBe(MAX_LINES + 5)
  })

  it('i18n 字典压平成带语言标题的单一文本', () => {
    const flat = flattenLocalizedContent({ zh: '中文正文', en: 'English' })
    expect(flat).toContain('【zh】')
    expect(flat).toContain('English')
    expect(flattenLocalizedContent(null)).toBe('')
    expect(flattenLocalizedContent('纯字符串')).toBe('纯字符串')
  })
})
