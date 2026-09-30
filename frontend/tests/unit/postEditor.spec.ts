/**
 * lib/postEditor.ts：编辑器侧的纯逻辑（字数统计 / slug 源语言 / 定时校验）。
 *
 * 三条都是"界面上看着对、实际错了"的那类问题：
 * ① 只盯 zh 标题生成 slug，作者先写英文标题时就永远拿不到 slug；
 * ② 定时时间不校验过去值，后端会把它降级成立即发布——作者以为排好了，其实已经发出去了；
 * ③ 字数把 Markdown 标记也算进去，统计比实际多一大截。
 */
import { describe, expect, it } from 'vitest'
import { estimateContentStats, scheduledAtError, slugSourceTitle } from '../../lib/postEditor'

describe('estimateContentStats', () => {
  it('空正文返回 0 字 / 1 分钟（0 分钟在界面上像是坏了）', () => {
    expect(estimateContentStats('')).toEqual({ words: 0, minutes: 1 })
    expect(estimateContentStats(null)).toEqual({ words: 0, minutes: 1 })
    expect(estimateContentStats('   \n\n  ')).toEqual({ words: 0, minutes: 1 })
  })

  it('中文按字计', () => {
    const stats = estimateContentStats('一二三四五')
    expect(stats.words).toBe(5)
    expect(stats.minutes).toBe(1)
  })

  it('西文按词计', () => {
    expect(estimateContentStats('hello world foo').words).toBe(3)
  })

  it('中英混排分别计数再相加', () => {
    expect(estimateContentStats('你好 hello world').words).toBe(4)
  })

  it('不算 Markdown 标记字符', () => {
    const plain = estimateContentStats('标题正文').words
    const marked = estimateContentStats('## 标题正文').words
    expect(marked).toBe(plain)

    expect(estimateContentStats('**加粗**').words).toBe(2)
    expect(estimateContentStats('[文字](https://example.com)').words).toBe(2)
  })

  it('代码块整体不计入', () => {
    expect(estimateContentStats('```\nconst a = 1\n```').words).toBe(0)
  })

  it('字数足够多时分钟数跟着涨', () => {
    const long = '字'.repeat(900)
    expect(estimateContentStats(long).minutes).toBe(3)
  })
})

describe('slugSourceTitle', () => {
  it('空值安全', () => {
    expect(slugSourceTitle(null)).toBe('')
    expect(slugSourceTitle(undefined)).toBe('')
    expect(slugSourceTitle({})).toBe('')
    expect(slugSourceTitle({ zh: '   ' })).toBe('')
  })

  it('zh 优先', () => {
    expect(slugSourceTitle({ zh: '中文标题', en: 'English' })).toBe('中文标题')
  })

  it('zh 为空时退到繁体、英文、日文', () => {
    expect(slugSourceTitle({ zh: '', en: 'English', ja: 'タイトル' })).toBe('English')
    expect(slugSourceTitle({ zh: '', ja: 'タイトル' })).toBe('タイトル')
  })

  it('只有约定之外的语言键时仍取第一个非空值', () => {
    expect(slugSourceTitle({ de: 'Deutsch' })).toBe('Deutsch')
  })
})

describe('scheduledAtError', () => {
  const future = new Date(Date.now() + 3600_000).toISOString()
  const past = new Date(Date.now() - 3600_000).toISOString()

  it('非定时状态一律放行', () => {
    expect(scheduledAtError('draft', null)).toBeNull()
    expect(scheduledAtError('published', '')).toBeNull()
  })

  it('定时状态缺时间要拦', () => {
    expect(scheduledAtError('scheduled', '')).toBe('请选择定时发布时间')
    expect(scheduledAtError('scheduled', null)).toBe('请选择定时发布时间')
  })

  it('过去的时间要拦（后端会把它降级成立即发布）', () => {
    expect(scheduledAtError('scheduled', past)).toBe('定时发布时间必须晚于当前时间')
  })

  it('非法格式要拦', () => {
    expect(scheduledAtError('scheduled', '昨天下午')).toBe('定时发布时间格式不正确')
  })

  it('未来的时间放行', () => {
    expect(scheduledAtError('scheduled', future)).toBeNull()
  })
})
