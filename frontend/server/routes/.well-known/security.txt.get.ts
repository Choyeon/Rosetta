/**
 * /.well-known/security.txt — RFC 9116 安全漏洞披露渠道（Nitro BFF 纯文本）。
 *
 * 路径形态：文件放在 server/routes/.well-known/ 下。nitropack 的 scanDir 调
 * globby 时显式带 `dot: true`（dist/core/index.mjs），点目录会被正常收录，
 * 所以真实路由路径就是 /.well-known/security.txt —— RFC 9116 规定的唯一位置，
 * 不再另开 /security.txt + middleware 改写 req.url 的别名面。
 *
 * 口径：
 * · Contact 只用**站内真实可达的沟通入口**（关于页，其次留言板）。这里不写邮箱：
 *   设置里没有"收安全报告"的收件箱键，`email.from_address` 是 SMTP 发信账号，
 *   把它公开等于把发信地址挂在垃圾邮件采集面上；而编一个不存在的 monitoring@
 *   地址比不写更糟（安全研究者会真的发过去）。
 * · Expires 取"生成时刻 + 1 年"的 RFC3339：这份文件跟着站点配置走，站长换域名或
 *   关掉沟通入口时它会自然重建；留一个写死的过去日期等于宣告"这行没人维护"。
 * · Preferred-Languages 与 i18n 固定四语一致（AGENTS.md §13.2 禁止新增语言）。
 * · URL 只认 SITE_URL 配置（resolvePublicSiteOrigin），绝不从请求 Host 推导——
 *   本响应带 s-maxage，一次 Host 伪造会被缓存固化给所有访客（同一红线见
 *   robots.txt.get.ts）。
 * · CSP / 安全头由 nginx 层统一叠加，本文件无需动作。
 */

const EXPIRES_YEARS = 1

export default defineEventHandler((event) => {
  const origin = resolvePublicSiteOrigin(useRuntimeConfig(event))
  const absolute = (path: string) => `${origin}${path}`

  const expires = new Date(Date.now() + EXPIRES_YEARS * 365 * 24 * 3600 * 1000)
    .toISOString()
    .replace(/\.\d{3}Z$/, 'Z')

  const lines: string[] = [
    '# RFC 9116 — 安全漏洞披露与联系渠道',
    '',
    `Contact: ${absolute('/about')}`,
    `Contact: ${absolute('/guestbook')}`,
    `Acknowledgments: ${absolute('/about')}`,
    'Preferred-Languages: zh, en, ja, zh-Hant'
  ]
  if (origin) {
    lines.push(`Canonical: ${absolute('/.well-known/security.txt')}`)
  }
  lines.push(`Expires: ${expires}`)

  setHeader(event, 'content-type', 'text/plain; charset=utf-8')
  // 与 robots.txt 同档：小时级足够，安全研究者不会因为一小时延迟错过窗口
  setHeader(event, 'cache-control', 'public, max-age=0, s-maxage=3600, stale-while-revalidate=86400')
  return `${lines.join('\n')}\n`
})
