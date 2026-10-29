/**
 * SPA 空壳页的**服务端**标题补写（与 `noindex-shell.ts` 同族，同一条 render:html 链路）。
 *
 * 为什么需要：`/login` `/register` `/forgot-password` `/search` `/account` `/admin`
 * 是精准反选的 ssr:false 路径，Nitro 只吐一份构建期空壳，`<title>` 来自
 * `nuxt.config.ts` 的 `app.head.title`（编译期常量 'Rosetta'）。站点名与
 * 「SEO · 页面默认标题」存在数据库里，构建期拿不到 —— 于是这六条路径的标签页标题
 * 永远与后台设置无关（curl 实测复现）。真实用户看到的前缀是 `· 站点名` 后缀形式，
 * 这里产出同一条字符串规则，保证服务端补写与客户端 titleTemplate 收敛到同一个值。
 *
 * 路径名单口径：与 §2.2 的 ssr:false 反选表一致（`/oobe` 已改 SSR，不在列），
 * 并且同样先剥 `prefix_except_default` 的语言前缀，否则 `/en/login` 整批漏掉。
 */

import { matchesPathRoot, stripLocalePathPrefix } from '../../lib/rosetta-themes'
import { brandFloorTitle } from '../../lib/utils'

/** 需要服务端补标题的 SPA 壳路径前缀（裸路径 + 子路径都算命中）。 */
export const SPA_SHELL_PREFIXES: readonly string[] = [
  '/login',
  '/register',
  '/forgot-password',
  '/search',
  '/account',
  '/admin'
]

export function isSpaShellPath(pathname: string): boolean {
  const stripped = stripLocalePathPrefix((pathname || '').split('?')[0] ?? '')
  return SPA_SHELL_PREFIXES.some(prefix => matchesPathRoot(stripped, prefix))
}

/**
 * 标题单源拼接：与 app.vue 的 titleTemplate 无标题分支、
 * site-title.global.ts 的 buildTitle 空标题分支同口径（共用 lib/utils::brandFloorTitle）。
 */
export function buildShellTitle(siteName: string, subtitle: string): string {
  return brandFloorTitle(siteName, subtitle)
}

/** `<title>` 是文本节点：只有 & < > 三个字符需要转义（引号在标签内无意义）。 */
function escapeTitleText(s: string): string {
  return s.replace(/&/g, '&amp;').replace(/</g, '&lt;').replace(/>/g, '&gt;')
}

const TITLE_RE = /<title(?:\s[^>]*)?>[\s\S]*?<\/title>/i

/**
 * 把壳里的 `<title>` 换成品牌标题。
 * 无 `<title>` / 无新标题 / 内容已经一致 → 原样返回（幂等，可被两道钩子双跑）。
 */
export function rewriteShellTitle(html: string, title: string): string {
  if (!html || !title) return html
  const next = `<title>${escapeTitleText(title)}</title>`
  if (!TITLE_RE.test(html)) return html
  return html.replace(TITLE_RE, next)
}
