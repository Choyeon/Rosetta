/**
 * 文章「来源 / 原文出处」的展示口径单源。
 *
 * 两条都不是"显然"的：
 * 1. `原创` 是后端 `Post.source` 列的默认值（NOT NULL + Field(default)），
 *    每篇文章都在 meta 行声明一遍等于噪声，所以默认值不展示。
 * 2. `source_url` 除了文章编辑口，还会由导入工具直接写 ORM 落库（绕过 schema 的
 *    http(s) 严格档）。库里躺着 `javascript:` / `data:` 时，把它当 href 就是
 *    在每篇转载文章下方挂一条可执行链接，所以非 http(s) 一律降级成"没有链接"。
 */

export const DEFAULT_POST_SOURCE = '原创'

const SAFE_URL_RE = /^https?:\/\//i

export interface PostSourceView {
  /** meta 行要不要出现来源这一项 */
  visible: boolean
  /** 展示文本：来源本身；来源是默认值时回落成出处链接的主机名 */
  text: string
  /** 出站链接；空串表示只展示文本，不渲染 `<a>` */
  href: string
}

function hostOf(url: string): string {
  if (!url) return ''
  try {
    return new URL(url).hostname.replace(/^www\./, '')
  } catch {
    return url
  }
}

export function resolvePostSource(
  source?: string | null,
  sourceUrl?: string | null
): PostSourceView {
  const rawSource = (source ?? '').trim()
  const rawUrl = (sourceUrl ?? '').trim()
  const href = SAFE_URL_RE.test(rawUrl) ? rawUrl : ''
  const isDefault = rawSource === '' || rawSource === DEFAULT_POST_SOURCE
  if (isDefault && !href) return { visible: false, text: '', href: '' }
  return { visible: true, text: isDefault ? hostOf(href) : rawSource, href }
}
