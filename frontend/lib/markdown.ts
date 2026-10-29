/**
 * Markdown 正文预处理（SSR 与客户端同一份纯函数，无 DOM 依赖）。
 *
 * 存在的理由：页面模板已单独渲染 `<h1>`（页面/文章标题），而正文 Markdown 的首行
 * 常常又写一遍 `# 标题` —— 这是 WordPress 迁移与作者习惯的常态。直接转换会让同一个
 * 文档出现两个一级标题：线上 `/page/about` 实测 `<h1` 计数为 2（站点其余页面均钉在 1）。
 *
 * 只剥「首行且文本与标题匹配」的那一行，正文中间真正的一级标题保持原样。
 */

/** 首行 H1（允许 0–3 个前导空格、闭合 # 与行尾结束）；不跨行匹配。 */
const LEADING_H1 = /^\s{0,3}#\s+(.+?)\s*#*\s*(?:\r?\n|$)/

/**
 * 剥掉与标题重复的首行 H1，返回用于渲染的 Markdown。
 *
 * 匹配规则（与 pages/posts/[slug].vue 的历史行为一致）：完全相等，或任一方包含另一方。
 * 标题为空时不剥——加载中 / 404 态标题是空串，此时「比较」没有意义，剥掉只会扔正文。
 */
export function stripDuplicateTitleHeading(markdown: string, title: string | null | undefined): string {
  if (!markdown) return markdown
  const matched = LEADING_H1.exec(markdown)
  if (!matched) return markdown
  const headingText = (matched[1] ?? '').trim()
  const wanted = (title ?? '').trim()
  if (!headingText || !wanted) return markdown
  if (headingText === wanted || headingText.includes(wanted) || wanted.includes(headingText)) {
    return markdown.slice((matched[0] ?? '').length).replace(/^\s+/, '')
  }
  return markdown
}
