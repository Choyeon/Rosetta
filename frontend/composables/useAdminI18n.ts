/**
 * Admin 管理端共享 i18n / slug 工具函数
 *
 * 解决问题：
 *   categories.vue / tags.vue / series.vue / pages.vue / PostForm.vue / posts/index.vue
 *   都各自复制了一份 getLocalizedStr / normalizeI18nDict / slugify，
 *   实现略有差异（如正则范围不同），容易出 bug。
 *
 * Nuxt auto-import：放在 composables/ 下即可全站直接使用，无需手动 import。
 */

export type I18nDict = { zh: string, en: string, ja: string, zh_Hant: string }

export const EMPTY_I18N_DICT: I18nDict = { zh: '', en: '', ja: '', zh_Hant: '' }

/**
 * 从 i18n dict 中提取一个可读字符串。
 * 优先返回 zh，其次 en，最后取第一个非空值。
 */
export const getLocalizedStr = (
  v: string | Record<string, string> | null | undefined
): string => {
  if (v == null) return ''
  if (typeof v === 'string') return v
  return v.zh || v.en || Object.values(v)[0] || ''
}

/**
 * 将 string | dict | null 归一化为标准 4 语言 dict。
 * string 视为 zh 值；缺失的语言键补空串。
 */
export const normalizeI18nDict = (
  v: string | Record<string, string> | null | undefined
): I18nDict => {
  if (v == null) return { ...EMPTY_I18N_DICT }
  if (typeof v === 'string') return { zh: v, en: '', ja: '', zh_Hant: '' }
  return {
    zh: v.zh ?? '',
    en: v.en ?? '',
    ja: v.ja ?? '',
    zh_Hant: v.zh_Hant ?? ''
  }
}

/**
 * i18n dict → 提交 payload：过滤空语言，全部为空则返回 undefined。
 */
export const toI18nPayload = (
  v: Record<string, string>
): Record<string, string> | undefined => {
  const out: Record<string, string> = {}
  for (const [lang, val] of Object.entries(v)) {
    if (val && val.trim()) out[lang] = val
  }
  return Object.keys(out).length > 0 ? out : undefined
}

/**
 * 将中文/英文文本转为 URL 友好的 slug。
 * 支持中文字符保留（\u4e00-\u9fa5）。
 */
export const slugify = (text: string): string => {
  let s = text.trim().toLowerCase()
  s = s.replace(/[\s]+/g, '-')
  s = s.replace(/[^\w\u4e00-\u9fa5-]/g, '')
  s = s.replace(/-+/g, '-').replace(/^-|-$/g, '')
  return s
}
