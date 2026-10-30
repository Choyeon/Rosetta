/**
 * 顶级真实路由的 slug 清单（单源，两个消费方）。
 *
 * `/page/<slug>` 是旧 WordPress 风格链接的兼容口，命中这些 slug 时那条 URL 想访问的
 * 其实是内建页面：
 *  - `server/middleware/06-page-alias.ts` 在 SSR 层直接 301（爬虫与首屏都拿真 301）；
 *  - `pages/page/[slug].vue` 保留同一份清单做客户端兜底（中间件被绕过时仍能纠偏）。
 *
 * 之所以不能只靠客户端跳：绕过 JS 的抓取器看到的是 200 + `canonical → /<slug>` 的
 * 重复内容，而正文来自库里那条同名独立页记录——与 canonical 指向的页面内容并不相同。
 *
 * 清单必须与后端 `_TOP_LEVEL_ROUTE_SLUGS`（`backend/api/blog.py`，sitemap 用它判定
 * 哪些独立页记录没有可提交的规范地址）逐条一致，只允许少 `page` 一项——那是兼容口的根，
 * 跳过去等于原地打转。契约见 `tests/unit/pageAliasTopLevelRoutes.spec.ts`。
 */
export const TOP_LEVEL_ROUTE_SLUGS: readonly string[] = [
  'about',
  'guestbook',
  'gallery',
  'archive',
  'friends',
  'activity',
  'login',
  'register',
  'forgot-password',
  'oobe',
  'posts',
  'categories',
  'tags',
  'series',
  'authors',
  'sponsor',
  'search',
  'settings',
  'account',
  'admin'
]
