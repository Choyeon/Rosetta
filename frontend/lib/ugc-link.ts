/**
 * 用户自填链接（评论者 / 留言者的「网站」）的渲染口径单源。
 *
 * 两条都不是"显然"的：
 * 1. 写口的 http(s) 严格档挡不住绕开 schema 的入口（导入工具、直连 SQL、早期脏行），
 *    库里躺着 `javascript:` 时把它当 href 就是给每条访客评论挂一条可执行链接，
 *    所以非 http(s) 在渲染侧一律降级成"没有链接"。后端 `comment_service` / `guestbook_service`
 *    读侧也各有一道同口径过滤，这里是最后一道，不因为上游有就省。
 * 2. `//host` 这种协议相对写法在 http 站点上会被浏览器补成当前协议，看起来无害，
 *    但它不是"绝对 URL"，写口的 `_require_absolute_url` 也不收；渲染侧一并拒掉，
 *    界面与库里的判定标准才不会分叉成两套。
 *
 * 展示文本刻意只剥协议头（不截主机名、不去尾部斜杠），与留言板既有观感保持一致。
 */

const SAFE_URL_RE = /^https?:\/\//i

/** 可以进 `href` 的值；空串表示这一行不渲染 `<a>`。 */
export function safeUgcHref(raw?: string | null): string {
  const value = (raw ?? '').trim()
  return SAFE_URL_RE.test(value) ? value : ''
}

/** 链接里显示的文字：去掉协议头，其余原样。 */
export function ugcLinkLabel(href: string): string {
  return href.replace(/^https?:\/\//i, '')
}
