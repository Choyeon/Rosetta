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

/** 四语键名（与 i18n.config.ts 的语言清单一致；新增语言必须同步这里）。 */
const I18N_DICT_KEYS = new Set(['zh', 'en', 'ja', 'zh_Hant'])

/**
 * 判定「这个值就是一份多语言 dict」。
 *
 * 用于把后台的裸 JSON 文本域换成四语 Tab 编辑器（站点设置的 hero.cta_text /
 * donate.title / donate.description 就属于这一类）：它们被当通用 JSON 渲染时，
 * 提示写着「数组格式」（实际是对象），且只有库里已有的语言键能编辑——
 * 只存了 zh/en 的字段从此再也补不进 ja/zh_Hant。
 *
 * 口径必须保守：普通对象（非数组）、键非空、键全在四语名单内、值全是字符串 / null。
 * 站点设置里其余的数组与对象（donate.methods / donate.sponsors 等）键是
 * name/image/note，不会被误判成多语言字段。
 */
export const isI18nDict = (v: unknown): v is Record<string, string | null> => {
  if (v == null || typeof v !== 'object' || Array.isArray(v)) return false
  const entries = Object.entries(v as Record<string, unknown>)
  if (entries.length === 0) return false
  return entries.every(([k, val]) => I18N_DICT_KEYS.has(k) && (val == null || typeof val === 'string'))
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

/**
 * 内容型 slug（文章/分类/标签/独立页/系列）的校验正则，镜像后端
 * `backend/schemas/_slug.py::CONTENT_SLUG_PATTERN`（小写字母/数字/下划线/CJK/连字符）。
 * 改任何一侧必须同步另一侧。插件/主题 manifest 的 slug 仍是更严的 ASCII kebab-case，
 * 不复用本常量。
 */
export const CONTENT_SLUG_PATTERN = /^[a-z0-9_\u4e00-\u9fff-]+$/
