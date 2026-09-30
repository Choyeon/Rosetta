/**
 * 文章编辑器的纯逻辑（字数统计 + slug 生成口径），刻意脱离 .vue 以便单测。
 *
 * 这里的估算**只用于给作者即时反馈**；列表与详情展示的 `reading_time` 由后端计算并
 * 持久化（列表接口 defer(content) 就是为了不加载正文），前端不去复算它，免得两处口径打架。
 */

/** 中文按字读、西文按词读，二者混排时分别计数再折算。 */
const CJK_RE = /[\u3400-\u4dbf\u4e00-\u9fff\uf900-\ufaff\u3040-\u30ff\uac00-\ud7af]/gu
const LATIN_WORD_RE = /[A-Za-z0-9]+(?:['’-][A-Za-z0-9]+)*/g

export interface ContentStats {
  /** 折算后的"字数"：中文字符数 + 西文词数 */
  words: number
  /** 预估阅读分钟数，最少 1 分钟（与后端 reading_time 的兜底一致） */
  minutes: number
}

/** Markdown 正文里的标记字符不该算进字数：标题井号、强调符号、链接语法、代码块。 */
function stripMarkdown(markdown: string): string {
  return markdown
    .replace(/```[\s\S]*?```/g, ' ')
    .replace(/`[^`]*`/g, ' ')
    .replace(/!?\[([^\]]*)\]\([^)]*\)/g, '$1')
    .replace(/^\s{0,3}#{1,6}\s+/gm, '')
    .replace(/^\s{0,3}>\s?/gm, '')
    .replace(/^\s{0,3}[-*+]\s+/gm, '')
    .replace(/[*_~]/g, '')
}

/**
 * 统计正文规模。空/纯空白返回 0 字、1 分钟——"0 分钟"出现在界面上像是坏了。
 */
export function estimateContentStats(markdown: string | null | undefined, wpm = 300): ContentStats {
  const text = stripMarkdown(markdown ?? '')
  const cjk = text.match(CJK_RE)?.length ?? 0
  const latin = text.match(LATIN_WORD_RE)?.length ?? 0
  const words = cjk + latin
  return { words, minutes: words === 0 ? 1 : Math.max(1, Math.round(words / wpm)) }
}

/**
 * 从多语言标题里挑一个用于生成 slug 的源语言。
 *
 * 后端 `PostBase.title` 是 i18n dict，项目约定 zh 为主语言；但作者完全可能先写英文标题，
 * 只盯 zh 会让 slug 一直是空的（然后被"请输入 slug"卡住）。
 */
export function slugSourceTitle(title: Record<string, string> | null | undefined): string {
  if (!title) return ''
  for (const key of ['zh', 'zh_Hant', 'en', 'ja']) {
    const value = title[key]
    if (typeof value === 'string' && value.trim()) return value.trim()
  }
  // 兜底：dict 里带了约定之外的语言键时，取第一个非空的
  for (const value of Object.values(title)) {
    if (typeof value === 'string' && value.trim()) return value.trim()
  }
  return ''
}

/**
 * 定时发布时间的前端校验。返回 null 表示通过。
 *
 * 后端会把"不晚于现在"的定时文章直接降级成立即发布（`new_status = "published"`），
 * 作者以为排好了、实际已经发出去了——这个偏差必须在提交前拦住。
 */
export function scheduledAtError(
  status: string,
  scheduledAt: string | null | undefined
): string | null {
  if (status !== 'scheduled') return null
  if (!scheduledAt) return '请选择定时发布时间'
  const at = new Date(scheduledAt).getTime()
  if (Number.isNaN(at)) return '定时发布时间格式不正确'
  if (at <= Date.now()) return '定时发布时间必须晚于当前时间'
  return null
}
