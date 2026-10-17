/**
 * SSR HTML 响应的 `Cache-Control` 归一（把 Nitro 的实际输出补回 AGENTS §2.3 承诺的口径）。
 *
 * 为什么要归一：routeRules 里写的是
 *   `public, max-age=0, s-maxage=<T>, stale-while-revalidate=86400`
 * 但 Nitro 的 swr 缓存处理器在响应阶段把它**整条覆写**成
 *   `s-maxage=<T>, stale-while-revalidate`
 * ——少了 `public, max-age=0`。`s-maxage` 只约束共享缓存（CDN），浏览器私有缓存
 * 因此拿不到显式新鲜期，退化成**启发式新鲜期**（(Date − Last-Modified) 的 10%）。
 * 实测后果：后台改完站点设置、分组保存已经清掉 Nitro 页面缓存，curl 同一 URL 立刻拿到新值，
 * 但回访访客的 Chrome 直接用磁盘里的旧 HTML（`performance.getEntriesByType('navigation')[0].transferSize === 0`），
 * 而 `useSite` 的分组数据是 SSR 时烘进 `useState('site:state')` payload 的，
 * 客户端看到 `loaded=true` 就不会再拉 `/api/settings/public` → 表现就是"设置了不生效"。
 *
 * 只做一件事：给带 `s-maxage` 的响应补 `max-age=0`（浏览器必须回源校验），
 * 共享缓存的 TTL 与 stale-while-revalidate 原样保留，不改任何缓存策略的松紧。
 * 其余响应（`no-store` 的后台/登录页、`/_nuxt/**` 强缓存静态资源）一律返回 null 不动。
 */

const S_MAXAGE_RE = /\bs-maxage=(\d+)/
const MAX_AGE_RE = /\bmax-age=/
// Nitro 会输出裸的 `stale-while-revalidate`（丢掉秒值），而 HTTP 要求它带 delta-seconds，
// 裸形式浏览器/中间代理会整条忽略（连 max-age=0 一起丢）→ 必须补回秒值。
// 补多少不能瞎猜：按本页自己的 s-maxage 回填。公开页默认口径是 86400（AGENTS §2.3），
// 只有 s-maxage 短的高频实时页（/posts/hot · /guestbook）声明的是 600，
// 给它们也补 86400 等于把"60 秒热榜"的窗口撑成一整天。
// 新增带其它 swr 窗口的公开页时，在这里按 s-maxage 登记一条。
const BARE_SWR_RE = /\bstale-while-revalidate\b(?!=)/
const SWR_BY_SMAXAGE: Readonly<Record<string, string>> = { '60': '600' } as const
const DEFAULT_SWR = '86400'

/** 已合规（同时有 max-age 与 s-maxage）或不属于本页口径 → null 表示不改写。 */
export function normalizeHtmlCacheControl(raw: string | null | undefined): string | null {
  if (!raw) return null
  const sMaxage = S_MAXAGE_RE.exec(raw)?.[1]
  if (!sMaxage) return null
  if (MAX_AGE_RE.test(raw)) return null
  const restored = raw
    .trim()
    .replace(/,\s*/g, ', ')
    .replace(BARE_SWR_RE, `stale-while-revalidate=${SWR_BY_SMAXAGE[sMaxage] ?? DEFAULT_SWR}`)
    .replace(/^public,\s*/, '')
  return `public, max-age=0, ${restored}`
}
