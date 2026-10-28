/**
 * 首页轮播按钮链接的唯一闸门（`pages/index.vue` 的主/次 CTA 都走这里）。
 *
 * 为什么不是"必须 http(s)"的严格档：后台这两个框写的是**站内路径**
 * （`/posts`、`/series/xxx`），语言前缀由 `localeHref` 自动补；按严格档会把
 * 正常配置全部拒掉。
 *
 * 为什么渲染侧还要挡一层：`cta_url` / `cta_secondary_url` 最终成为访客页面上
 * `<a href>` 的一部分，而写入口不止后台表单一个（导入 ZIP 直接写 ORM、直接打接口），
 * 所以库里可能躺着 `javascript:` 这类伪协议。渲染侧再判一次才算真挡住。
 *
 * 判前先去空白与控制字符，是因为浏览器解析 URL 时会自己剥掉 `\t` `\n` `\r` 与空格：
 * `javas\tcript:alert(1)` 对人是"怪串"、对点击就是执行。只在**判定**时归一，
 * 返回值仍是原串（正常站内路径里的空格属于原样透传的边界，不归一成链接值）。
 */

const UNSAFE_SCHEME_RE = /^(javascript|vbscript|data|file):/i

/** 空值或伪协议一律回落到 `fallback`，其余原样交给 `localeHref`（外链要透传）。 */
export function safeHeroHref(raw: string | null | undefined, fallback: string): string {
  const value = typeof raw === 'string' ? raw.trim() : ''
  if (!value) return fallback
  // 命中控制字符正是本闸门的目的（浏览器会剥掉它们），不是把脏数据放进 href。
  // eslint-disable-next-line no-control-regex
  const probe = value.replace(/[\s\u0000-\u001f]/g, '')
  if (UNSAFE_SCHEME_RE.test(probe)) return fallback
  return value
}
