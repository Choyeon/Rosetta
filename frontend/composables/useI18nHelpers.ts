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

// 与 useI18n.ts 导出保持一致（避免 SSR 首屏 VueI18n 不可用时返回 undefined）
const _fallbackLocale = 'zh'

const MONTH_TABLE: Record<string, string[]> = {
  zh: ['1月', '2月', '3月', '4月', '5月', '6月', '7月', '8月', '9月', '10月', '11月', '12月'],
  zh_Hant: ['1月', '2月', '3月', '4月', '5月', '6月', '7月', '8月', '9月', '10月', '11月', '12月'],
  en: ['Jan', 'Feb', 'Mar', 'Apr', 'May', 'Jun', 'Jul', 'Aug', 'Sep', 'Oct', 'Nov', 'Dec'],
  ja: ['1月', '2月', '3月', '4月', '5月', '6月', '7月', '8月', '9月', '10月', '11月', '12月']
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
  ): string => {
    if (value == null) return fallback
    if (typeof value === 'string') return value || fallback
    if (typeof value !== 'object') return fallback
    const dict = value as Record<string, string>
    const keys = Object.keys(dict)
    if (keys.length === 0) return fallback
    // 1) 当前 locale 精确命中
    if (_localeCode && dict[_localeCode]) return dict[_localeCode] || fallback
    // 2) zh → zh_Hant 互通（有些后端只存了 zh，但前端切到了繁体）
    if (_localeCode === 'zh_Hant' && dict['zh']) return dict['zh'] || fallback
    if (_localeCode === 'zh' && dict['zh_Hant']) return dict['zh_Hant'] || fallback
    // 3) 第一个非空值
    const firstKey = keys.find(k => dict[k])
    return firstKey ? (dict[firstKey] || fallback) : fallback
  }

  const pickLocalized = resolveLocalized

  const formatDate = (date: string | Date | number | null | undefined): string => {
    try {
      if (date == null || date === '') return ''
      const d = new Date(date as string | number | Date)
      if (isNaN(d.getTime())) return ''
      const months = (MONTH_TABLE[_localeCode] || MONTH_TABLE.en || []) as string[]
      const y = d.getFullYear()
      const m = months[d.getMonth()] ?? ''
      const day = d.getDate()
      switch (_localeCode) {
        case 'zh':
        case 'zh_Hant':
        case 'ja':
          return `${y}年${m}${day}日`
        case 'en':
        default:
          return `${m} ${day}, ${y}`
      }
    } catch {
      return ''
    }
  }

  return {
    resolveLocalized,
    pickLocalized,
    formatDate
  }
}
