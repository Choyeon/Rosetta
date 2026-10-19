/**
 * 公开 SSR 页的日期展示单源守卫。
 *
 * 表现：`d.toLocaleDateString(locale.value, {...})` 看着"已经传了 locale"所以很像对的，
 * 但**服务端的 Node 常常没有 full-icu**，Intl 会静默回退 en-US：
 * 同一条评论/同一条留言，服务端渲染成 `08/20`、浏览器渲染成 `8月20日` → hydration
 * text mismatch；这一页还带 swr，服务端那份字节会被 TTL 内所有访客复用。
 * `toLocaleTimeString(loc, {hour:'2-digit'})` 另一头：en-US 默认 12 小时制带 AM/PM，
 * 中文是 24 小时制，两端同一条记录两种文本。
 *
 * 口径：公开 SSR 页只用 `composables/useI18nHelpers` 的三个静态拼接形态
 * （formatDateText 完整日期 / formatStampText 月日时分 / formatMonthDayText 月日），
 * 月名统一取自 MONTH_TABLE。后台与 `/account` 等 ssr:false 反选页只在浏览器渲染，
 * 跟随浏览器 locale 是期望行为，不在扫描面内。
 */
import { describe, it, expect } from 'vitest'
import { readdirSync, readFileSync } from 'node:fs'
import process from 'node:process'
import {
  formatDateText,
  formatMonthDayText,
  formatStampText,
  MONTH_TABLE
} from '@/composables/useI18nHelpers'

const ROOT = process.cwd().replace(/[\\/]$/, '')
const SPA_PATHS = ['/login', '/register', '/forgot-password', '/search', '/account', '/oobe']
// 2026-08-20T14:05:00 本地时区无法保证，用固定分量断言而不是"今天减两天"
const SAMPLE = new Date(2026, 7, 20, 14, 5)

/** 真正的调用（排除注释里对旧写法的说明），逐行判定。 */
function realCalls(source: string): string[] {
  const hits: string[] = []
  for (const line of source.split(/\r?\n/u)) {
    const t = line.trim()
    if (t.startsWith('//') || t.startsWith('*') || t.startsWith('/*')) continue
    if (/\.toLocale(?:DateString|TimeString)\(/u.test(line)) hits.push(t)
  }
  return hits
}

function walk(dir: string): string[] {
  const out: string[] = []
  for (const entry of readdirSync(dir, { withFileTypes: true })) {
    const full = `${dir}/${entry.name}`
    if (entry.isDirectory()) {
      if (entry.name === 'node_modules' || entry.name.startsWith('.')) continue
      out.push(...walk(full))
    } else if (/\.vue$/u.test(entry.name)) out.push(full)
  }
  return out
}

describe('SSR 日期单源：三个形态的产出', () => {
  it('zh / zh_Hant / ja 用月表短名 + 年月日中文分隔', () => {
    for (const loc of ['zh', 'zh_Hant', 'ja']) {
      expect(formatDateText(SAMPLE, loc)).toBe('2026年8月20日')
      expect(formatMonthDayText(SAMPLE, loc)).toBe('8月20日')
      expect(formatStampText(SAMPLE, loc)).toBe('8月20 14:05')
    }
  })

  it('en 用短月名，时间固定 24 小时制（不随浏览器 locale 变成 PM）', () => {
    expect(formatDateText(SAMPLE, 'en')).toBe('Aug 20, 2026')
    expect(formatMonthDayText(SAMPLE, 'en')).toBe('Aug 20')
    expect(formatStampText(SAMPLE, 'en')).toBe('Aug 20 14:05')
  })

  it('未知 locale 回落英文月表；空值与非法日期回空串', () => {
    expect(MONTH_TABLE.en.length).toBe(12)
    expect(formatDateText('not-a-date', 'zh')).toBe('')
    expect(formatMonthDayText(null, 'zh')).toBe('')
    expect(formatStampText(undefined, 'en')).toBe('')
    expect(formatStampText('', 'en')).toBe('')
  })
})

describe('公开 SSR 页不得再出现 toLocaleDateString / toLocaleTimeString', () => {
  it('pages/**（排除后台与 ssr:false 反选页）零命中', () => {
    const offenders: string[] = []
    for (const file of walk(`${ROOT}/pages`)) {
      const posix = `/${file.replace(`${ROOT}/`, '')}`
      if (posix.includes('/admin/')) continue
      if (SPA_PATHS.some(p => posix.startsWith(`/${p}/`) || posix === `/${p}`)) continue
      const calls = realCalls(readFileSync(file, 'utf8'))
      if (calls.length > 0) offenders.push(`${posix} :: ${calls.join(' | ')}`)
    }
    expect(
      offenders,
      `这些 SSR 页面的日期依赖运行端 ICU，两端文本会不一致，请改 useI18nHelpers 的三个形态：${offenders.join('; ')}`
    ).toEqual([])
  })

  it('归档页与留言板确实走单源', () => {
    expect(readFileSync(`${ROOT}/pages/archive/index.vue`, 'utf8')).toContain('formatMonthDayText(')
    expect(readFileSync(`${ROOT}/pages/guestbook.vue`, 'utf8')).toContain('formatStampText(')
    expect(readFileSync(`${ROOT}/pages/activity.vue`, 'utf8')).toContain('formatStampText(')
  })
})
