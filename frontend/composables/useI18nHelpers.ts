/**
 * i18n 辅助 composable：全站共享
 *
 * 解决问题：
 *   · AppHeader、default.vue、PostCard、posts/index.vue 等都有"从 i18n dict 里按当前 locale 挑字符串"的函数，
 *     实现略有差异，容易出 bug。
 *   · PostCard.vue 内嵌了 SSR-safe 的日期格式化（避免 Node Intl 与浏览器输出不一致导致 hydration mismatch），
 *     这部分也应该被共享。
 *
 * 约定：
 *   · 所有后端返回的"可能是 i18n dict"的字段（name / title / label / content / excerpt …），
 *     统一走 resolveLocalized() / pickLocalized() 规范化，不要在每个文件里手写 switch。
 */

import { toHM } from '~~/lib/datetime'

// 与 useI18n.ts 导出保持一致（避免 SSR 首屏 VueI18n 不可用时返回 undefined）
const _fallbackLocale = 'zh'

/** 月份短名表：SSR 与浏览器字节级一致的唯一月份名来源，别再自带第二份。 */
export const MONTH_TABLE: Record<string, string[]> = {
  zh: ['1月', '2月', '3月', '4月', '5月', '6月', '7月', '8月', '9月', '10月', '11月', '12月'],
  zh_Hant: ['1月', '2月', '3月', '4月', '5月', '6月', '7月', '8月', '9月', '10月', '11月', '12月'],
  en: ['Jan', 'Feb', 'Mar', 'Apr', 'May', 'Jun', 'Jul', 'Aug', 'Sep', 'Oct', 'Nov', 'Dec'],
  ja: ['1月', '2月', '3月', '4月', '5月', '6月', '7月', '8月', '9月', '10月', '11月', '12月']
}

/**
 * 本地化取值唯一口径（纯函数，不依赖 setup 上下文，可被单测直接调用）。
 *
 * 顺序：当前 locale → zh/zh_Hant 互通 → 第一个非空值 → fallback。
 * 「非空」很关键：`{zh:'标题', en:''}` 这类脏数据在 `??` 口径下会把当前语言渲染成
 * 空白，而按真值判定才能回落到有内容的那份；本仓曾有 6 个页面用 `??`、8 个用真值，
 * 同一个分类名在列表页有字、在详情页空白。
 * 非 string/object 的标量返回 String(value)（多数页面原来也是这么做的），至少不留白。
 */
export function pickLocalizedText(
  value: unknown,
  localeCode?: string | null,
  fallback = ''
): string {
  if (value == null) return fallback
  if (typeof value === 'string') return value || fallback
  if (typeof value !== 'object') return String(value)
  const dict = value as Record<string, unknown>
  const textOf = (key: string): string => {
    const raw = dict[key]
    return typeof raw === 'string' && raw !== '' ? raw : ''
  }
  const direct = textOf(localeCode || '')
  if (direct) return direct
  // 后端常只写 zh，前端切到繁体时仍应有字（反之亦然）
  if (localeCode === 'zh_Hant') {
    const t = textOf('zh')
    if (t) return t
  }
  if (localeCode === 'zh') {
    const t = textOf('zh_Hant')
    if (t) return t
  }
  for (const key of Object.keys(dict)) {
    const t = textOf(key)
    if (t) return t
  }
  return fallback
}

export interface I18nLocalized {
  /**
   * 从后端返回的 i18n dict 中按当前 locale 选择字符串。
   *
   * 兼容三种输入：
   *   1. string 原文 → 直接返回
   *   2. { zh, en, ja, zh_Hant } dict → 按当前 locale 命中
   *   3. null / undefined → 返回 fallback
   *
   * 当 locale 未命中时，fallback 顺序：
   *   dict 的第一个可用值 → fallback 参数 → ''
   */
  resolveLocalized: (
    value: string | Record<string, string> | null | undefined,
    fallback?: string
  ) => string

  /**
   * resolveLocalized 的别名（旧代码中叫 pickLocalized / pickNavStr / pickAnnStr）。
   * 行为完全一致，只是名字更短。
   */
  pickLocalized: (
    value: string | Record<string, string> | null | undefined,
    fallback?: string
  ) => string

  /**
   * SSR-safe 日期格式化。
   *
   * —— 为什么不用 toLocaleDateString？——
   * Node SSR 的 Intl（无 full-icu 时）会把 zh/ja 回退到 en-US，
   * 生成类似 "Aug 20, 2025"，而浏览器按中文 locale 生成 "2025年8月20日"，
   * 两端文本不一致 → Vue Hydration node mismatch。
   *
   * 这里用静态月份名表 + 模板拼接，保证 SSR 与浏览器字节级一致。
   */
  formatDate: (date: string | Date | number | null | undefined) => string
}

/** 三个展示形态共用入参归一：空值 / 非法日期一律回空串，让调用方不必各自判 NaN。 */
function toDate(date: string | Date | number | null | undefined): Date | null {
  if (date == null || date === '') return null
  const d = new Date(date as string | number | Date)
  return Number.isNaN(d.getTime()) ? null : d
}

function monthNameOf(localeCode: string, d: Date): string {
  const months = MONTH_TABLE[localeCode] || MONTH_TABLE.en || []
  return months[d.getMonth()] ?? ''
}

/**
 * 「月 日」形态：归档列表按日列只要月和日。
 *
 * 日补零、月名取自 MONTH_TABLE，两端都是静态拼接；原先这里用
 * `toLocaleDateString(locale, {month:'2-digit',day:'2-digit'})`，Node 无 full-icu 时
 * 回退 en-US 产出 `08/20`，浏览器产出 `8月20日` → hydration mismatch，而这一页带 swr。
 */
export function formatMonthDayText(
  date: string | Date | number | null | undefined,
  localeCode: string = _fallbackLocale
): string {
  const d = toDate(date)
  if (!d) return ''
  const m = monthNameOf(localeCode, d)
  const day = String(d.getDate()).padStart(2, '0')
  return localeCode === 'en' ? `${m} ${day}` : `${m}${day}日`
}

/**
 * 「月 日 时:分」形态：一天之内年份是噪声的流（动态、留言板）。
 *
 * 时分固定 24 小时制（`toHM`）：`toLocaleTimeString('en-US', {hour:'2-digit'})` 默认给
 * `02:15 PM`，中文给 `14:15`，两端同一条留言两种文本。
 */
export function formatStampText(
  date: string | Date | number | null | undefined,
  localeCode: string = _fallbackLocale
): string {
  const d = toDate(date)
  if (!d) return ''
  // 与 formatMonthDayText 同一套分隔口径：CJK 月名与日之间不加空格（「8月20」），
  // 英文才要（「Aug 20」）。此前这里无条件拼空格，中文流就写成「8月 20 14:05」。
  const m = monthNameOf(localeCode, d)
  const day = String(d.getDate()).padStart(2, '0')
  return localeCode === 'en'
    ? `${m} ${day} ${toHM(d)}`
    : `${m}${day} ${toHM(d)}`
}

/** 完整日期形态：zh/zh_Hant/ja「2026年8月20日」，en「Aug 20, 2026」。 */
export function formatDateText(
  date: string | Date | number | null | undefined,
  localeCode: string = _fallbackLocale
): string {
  const d = toDate(date)
  if (!d) return ''
  const m = monthNameOf(localeCode, d)
  switch (localeCode) {
    case 'zh':
    case 'zh_Hant':
    case 'ja':
      return `${d.getFullYear()}年${m}${d.getDate()}日`
    default:
      return `${m} ${d.getDate()}, ${d.getFullYear()}`
  }
}

export const useI18nHelpers = (): I18nLocalized => {
  // SSR-safe：在 composables 中同步使用 useI18n，避免 setup 顶层 undefined
  let _localeCode: string = _fallbackLocale
  try {
    const { locale } = useI18n()
    if (locale && typeof locale.value === 'string') {
      _localeCode = locale.value
    }
  } catch {
    /* i18n 不可用时使用 fallback locale */
  }

  const resolveLocalized = (
    value: string | Record<string, string> | null | undefined,
    fallback = ''
  ): string => pickLocalizedText(value, _localeCode, fallback)

  const pickLocalized = resolveLocalized

  const formatDate = (date: string | Date | number | null | undefined): string =>
    formatDateText(date, _localeCode)

  return {
    resolveLocalized,
    pickLocalized,
    formatDate
  }
}
