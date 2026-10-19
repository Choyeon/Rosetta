/**
 * 不可索引页的**服务端** robots 闸门（与 `composables/useSeo.ts` 的 NOINDEX_ROBOTS 同口径）。
 *
 * 为什么需要服务端注入：`/login`、`/admin/**` 这些精准反选的 ssr:false 路径，
 * 页面里的 `useNoindexPage()` / `useSeo({ noindex: true })` 只在客户端 hydration
 * 之后才往 `<head>` 写 meta，原始 HTML 是一份 15 KB 的空壳、**一行 robots 都没有**。
 * 而 robots.txt 恰好把这些路径从 Disallow 移出了——移出的理由就是"页面自带 noindex，
 * 允许抓取才能读到那行 meta"。对不执行 JS 的抓取器（部分搜索引擎的初次发现、AI 爬虫、
 * 链接预览 bot）这句承诺并不成立，它们看到的就是一个可索引的空壳页。
 *
 * 名单口径：**凡是声明了 noindex 的页面都必须出现在这里**，SSR 页（/settings、/oobe）
 * 命中后会被插件的"已有 robots 就跳过"分支放过，不会产出两条规范。
 * 漂移由 `tests/unit/noindexShellMeta.spec.ts` 拦住：它递归扫 `pages/`，
 * 把每个写了 noindex 的路由反查回这份名单。
 */

import { matchesPathRoot, stripLocalePathPrefix } from '../../lib/rosetta-themes'

/** 需要服务端补 noindex 的路径前缀（裸路径 + 子路径都算命中）。 */
export const NOINDEX_SHELL_PREFIXES: readonly string[] = [
  '/login',
  '/register',
  '/forgot-password',
  '/search',
  '/account',
  '/settings',
  '/oobe',
  '/admin'
]

/**
 * 这个请求路径的服务端 HTML 是否必须带 noindex？
 *
 * 只匹配"裸路径或带 `/` 的子路径"，避免 `/login-x` 这类同前缀的公开页被误伤。
 * prefix_except_default 的 /en/login、/ja/admin/… 同样是 SPA 空壳，判定前先剥前缀
 * （清单唯一来源是 lib/rosetta-themes，历史上 server 侧各存一份副本）。
 */
export function needsNoindexShell(pathname: string): boolean {
  const stripped = stripLocalePathPrefix(pathname.split('?')[0] ?? '')
  return NOINDEX_SHELL_PREFIXES.some(prefix => matchesPathRoot(stripped, prefix))
}
