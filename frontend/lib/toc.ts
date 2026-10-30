/**
 * 文章目录的锚点单源（SSR 与客户端同一份纯函数）。
 *
 * 此前 `extractTOC`（composables/useReadingUX.ts）只在 `onMounted` 之后读真实 DOM 才给标题
 * 补 `id`：服务端吐出的 `<h2>` 一个 id 都没有，于是
 *  - 抓取器与禁 JS 读者拿到的 HTML 里没有任何章节锚点，外部分享的 `#小节` 链接落空；
 *  - 窄屏没有目录（aside 是 `hidden lg:block`），手机读者只能一路滚；
 *  - 目录项在首屏后才出现，本可直出的内容被推迟到 hydrate。
 * 现在由本模块在渲染字符串阶段（SSR 与客户端完全同一输入）就写好 id，并把同一份清单交给页面。
 *
 * 两条必须与 `extractTOC` 共用的口径：
 * 1. 只处理 h1–h4（`extractTOC` 的查询集就是这四个；更深层级两边都不进目录也不发 id）。
 * 2. id 推导与去重规则见 `slugifyHeading`，`extractTOC` 直接复用它 —— 两端各写一份必然漂移，
 *    表现是服务端 id 与客户端 scroll-spy 重算出的 id 不同、高亮永远不亮。
 */

export interface TocHeading {
  id: string
  text: string
  level: number
}

/** 标题层级上限（与 extractTOC 的 `h1, h2, h3, h4` 查询集一致）。 */
const MAX_ANCHOR_LEVEL = 4

const ENTITY_MAP: Record<string, string> = {
  amp: '&',
  lt: '<',
  gt: '>',
  quot: '"',
  apos: '\'',
  nbsp: ' '
}

const decodeEntities = (src: string): string =>
  src.replace(/&(#x[0-9a-fA-F]+|#[0-9]+|[a-zA-Z]+);/g, (whole, body: string) => {
    if (body.startsWith('#x') || body.startsWith('#X')) {
      const code = Number.parseInt(body.slice(2), 16)
      return Number.isFinite(code) && code > 0 ? String.fromCodePoint(code) : whole
    }
    if (body.startsWith('#')) {
      const code = Number.parseInt(body.slice(1), 10)
      return Number.isFinite(code) && code > 0 ? String.fromCodePoint(code) : whole
    }
    return ENTITY_MAP[body.toLowerCase()] ?? whole
  })

/**
 * 标题文本 → 锚点 id。规则与历史 `useReadingUX.slugify` 逐字一致（含 `-2`、`-3` 去重编号），
 * 因为客户端 scroll-spy 会用同一函数重算未带 id 的标题；两边不一致＝目录高亮错位。
 */
export const slugifyHeading = (text: string, existing: Set<string>): string => {
  let base = text
    .toLowerCase()
    .trim()
    .replace(/[\s]+/g, '-')
    .replace(/[^\p{Letter}\p{Number}-]/gu, '')
    // `用 pnpm & 构建` 去掉 `&` 后会留下连续连字符；压平后锚点更像 slug，也更短
    .replace(/-{2,}/g, '-')
    .replace(/^-+|-+$/g, '')
  if (!base) base = 'section'
  let id = base
  let i = 1
  while (existing.has(id)) id = `${base}-${++i}`
  existing.add(id)
  return id
}

/** 从一段（已净化的）HTML 里剥出标题纯文本：去掉内联标签与常见实体，压平空白。 */
const headingTextOf = (inner: string): string =>
  decodeEntities(inner.replace(/<[^>]*>/g, '')).replace(/\s+/g, ' ').trim()

/**
 * 给渲染后的 HTML 中每个 h1–h4 补 `id`，同时产出目录清单（只收 ≤ maxLevel 的层级）。
 *
 * 返回新字符串而不就地改写：调用方把它直接交给 `v-html`，SSR 与 hydrate 两端输入相同 ⇒ 输出相同。
 * 只匹配**开标签**并插入属性，标题内部的 `<code>` / `<a>` 等一律不动；正文里的代码块已被转义成
 * `&lt;h2&gt;`，不会被误命中。
 */
export const annotateHeadings = (
  html: string,
  maxLevel = MAX_ANCHOR_LEVEL
): { html: string, items: TocHeading[] } => {
  if (!html) return { html, items: [] }
  const items: TocHeading[] = []
  const used = new Set<string>()
  const depth = Number.isFinite(maxLevel) ? Math.min(Math.max(Math.trunc(maxLevel), 1), MAX_ANCHOR_LEVEL) : MAX_ANCHOR_LEVEL

  const next = html.replace(
    /<h([1-4])(\s[^>]*)?>([\s\S]*?)<\/h\1>/g,
    (whole, levelText: string, attrs: string | undefined, inner: string) => {
      const level = Number(levelText)
      const text = headingTextOf(inner)
      // 已经带 id 的标题（插件注入的短代码等）保留原值，但仍登记进 used 防重
      const existingId = attrs ? /\bid="([^"]*)"/.exec(attrs)?.[1] : undefined
      if (existingId) {
        used.add(existingId)
        if (level <= depth) items.push({ id: existingId, text, level })
        return whole
      }
      const id = slugifyHeading(text, used)
      if (level <= depth) items.push({ id, text, level })
      return `<h${level}${attrs ?? ''} id="${id}">${inner}</h${level}>`
    }
  )

  return { html: next, items }
}
