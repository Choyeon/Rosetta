/**
 * i18n prefix_except_default 下"URL 的语言变体"口径契约。
 *
 * 实测踩过的坑：canonical / hreflang / JSON-LD 的 URL 最初走 @nuxtjs/i18n 的
 * localePath(path, locale)。它按**路由名**解析传入字符串，详情页的
 * `/posts/{中文 slug}` 在 SSR 期产出过非字符串，asAbsolute 于是在
 * `path.startsWith` 上抛 TypeError —— 而这段跑在 useHead 的求值路径上，
 * 结果是**每一篇文章详情页整页 500**（旧构建因 siteUrl 为空串提前返回，
 * 把这个坑藏住了，配上 NUXT_PUBLIC_SITE_URL 才暴露）。
 *
 * 本仓 i18n 没有 per-locale 自定义路径，策略的全部含义就是
 * "默认语言裸路径 + 其余挂 /code 前缀"，所以 URL 派生改成纯字符串算术。
 * 这里同时钉住：不得再退回 localePath，且所有产出 URL 的地方共用同一个 helper。
 */

import { readdirSync, readFileSync } from 'node:fs'
import { resolve } from 'node:path'
import { describe, expect, it } from 'vitest'
import {
  applyLocalePrefix,
  DEFAULT_LOCALE_CODE,
  HREFLANG_MAP,
  OG_LOCALE_MAP,
  stripLocalePrefix
} from '../../composables/useSeo'
import { LOCALE_PATH_PREFIX_VARIANTS } from '../../lib/rosetta-themes'

const ROOT = resolve(__dirname, '..', '..')

describe('applyLocalePrefix / stripLocalePrefix', () => {
  it('默认语言裸路径，其它三语挂前缀', () => {
    expect(applyLocalePrefix('/posts/hello', DEFAULT_LOCALE_CODE)).toBe('/posts/hello')
    expect(applyLocalePrefix('/posts/hello', 'en')).toBe('/en/posts/hello')
    expect(applyLocalePrefix('/posts/hello', 'ja')).toBe('/ja/posts/hello')
    expect(applyLocalePrefix('/posts/hello', 'zh_Hant')).toBe('/zh_Hant/posts/hello')
  })

  it('首页前缀不带尾斜杠（/en 而不是 /en/）', () => {
    expect(applyLocalePrefix('/', 'en')).toBe('/en')
    expect(applyLocalePrefix('/', DEFAULT_LOCALE_CODE)).toBe('/')
  })

  it('入参已带语言前缀时先剥再挂，切换语言不会叠前缀', () => {
    expect(applyLocalePrefix('/en/posts/hello', 'ja')).toBe('/ja/posts/hello')
    expect(stripLocalePrefix('/zh_Hant/archive/2026/03')).toBe('/archive/2026/03')
    expect(stripLocalePrefix('/en')).toBe('/')
    // 不能被误伤：/encyclopedia 不是语言前缀
    expect(stripLocalePrefix('/encyclopedia')).toBe('/encyclopedia')
  })

  it('查询串与锚点留在末尾，不被前缀插进去', () => {
    expect(applyLocalePrefix('/posts?page=2', 'en')).toBe('/en/posts?page=2')
    expect(applyLocalePrefix('/posts/hello#comments', 'ja')).toBe('/ja/posts/hello#comments')
  })

  it('外链、协议相对 URL 与页面内锚点不参与语言前缀', () => {
    // 导航项 / 页脚链接 / 首页 CTA 的 to 都可能来自后台配置，
    // 给外链挂前缀会产出 /enhttps://example.com 这种死链。
    expect(applyLocalePrefix('https://example.com/friend', 'en')).toBe('https://example.com/friend')
    expect(applyLocalePrefix('//example.com/friend', 'en')).toBe('//example.com/friend')
    expect(applyLocalePrefix('#toc', 'ja')).toBe('#toc')
    expect(applyLocalePrefix('', 'en')).toBe('')
  })

  it('hreflang / og:locale 两张表覆盖全部四语（新增语言必须同步）', () => {
    const codes = Object.keys(HREFLANG_MAP)
    expect(codes).toEqual(Object.keys(OG_LOCALE_MAP))
    expect(codes).toContain(DEFAULT_LOCALE_CODE)
    expect(HREFLANG_MAP.zh_Hant).toBe('zh-Hant')
    expect(OG_LOCALE_MAP.zh_Hant).toBe('zh_TW')
  })
})

describe('URL 派生的单源约束（静态）', () => {
  const seo = readFileSync(resolve(ROOT, 'composables/useSeo.ts'), 'utf-8')

  it('SEO 侧不再依赖 localePath（详情页 500 的成因）', () => {
    expect(seo).not.toContain('useLocalePath')
    expect(seo).toContain('applyLocalePrefix(')
  })

  it('canonical / hreflang 缺省 url 时按当前路径派生，且只保留分页参数', () => {
    expect(seo).toContain('CANONICAL_QUERY_KEYS')
    // 视图变体参数（search/category/sort）不得进 canonical
    expect(seo).not.toMatch(/CANONICAL_QUERY_KEYS = \[[^\]]*search/)
  })

  it('站点根在生产不接受请求 Host 推导（缓存投毒面）', () => {
    expect(seo).toContain('LOOPBACK_HOST_RE')
    expect(seo).not.toContain('x-forwarded-host')
  })

  it('详情页不再另写一份 canonical', () => {
    const page = readFileSync(resolve(ROOT, 'pages/posts/[slug].vue'), 'utf-8')
    expect(page).not.toContain('useRequestURL')
    expect(page).toContain('article:publisher')
    expect(page).toContain('article:tag')
  })

  it('robots.txt 只挡机器面，语言前缀四份都要写', () => {
    const switcher = readFileSync(resolve(ROOT, 'components/LocaleSwitcher.vue'), 'utf-8')
    expect(switcher).not.toContain('useSwitchLocalePath')
    expect(switcher).toContain('applyLocalePrefix')

    const robots = readFileSync(resolve(ROOT, 'server/routes/robots.txt.get.ts'), 'utf-8')
    // 前缀清单已收口到 lib/rosetta-themes 单源，本文件不再写死 `zh_Hant` 字面量。
    // 口径改为"确实按单源做交叉积"，四份形态由单源那条断言保证。
    expect(robots).toContain('LOCALE_PATH_PREFIX_VARIANTS')
    expect(robots).toMatch(/privatePaths[\s\S]*\.flatMap\([\s\S]*prefix/)
    expect(robots).toContain('/admin/')
    expect([...LOCALE_PATH_PREFIX_VARIANTS]).toEqual(['', '/en', '/ja', '/zh_Hant'])
    // /login /register /account /search /oobe 必须由 Disallow 挪到页面 meta：
    // 抓不到就读不到 noindex，Google 会按已发现的链接生成"无摘要索引条目"。
    for (const moved of ['/login', '/register', '/account', '/search', '/oobe']) {
      expect(robots, `robots.txt 仍挡着 ${moved}，页面自带 noindex 就永远读不到`)
        .not.toContain(`'${moved}'`)
    }
  })

  it('不可索引页各自带 noindex 闸门（Disallow 不等于 noindex）', () => {
    const seo = readFileSync(resolve(ROOT, 'composables/useSeo.ts'), 'utf-8')
    expect(seo).toContain('export function useNoindexPage')
    expect(seo).toContain('noindex, follow')
    for (const page of [
      'pages/login.vue',
      'pages/register.vue',
      'pages/forgot-password.vue',
      'pages/account/index.vue',
      'pages/account/settings.vue',
      'pages/oobe.vue'
    ]) {
      expect(readFileSync(resolve(ROOT, page), 'utf-8'), `${page} 缺 noindex 闸门`)
        .toContain('useNoindexPage()')
    }
  })

  it('canonical 全站单源：首页与列表页不得再手写第二份', () => {
    for (const page of ['pages/index.vue', 'pages/posts/index.vue']) {
      const src = readFileSync(resolve(ROOT, page), 'utf-8')
      // 请求 Host 派生的 origin 会被 swr 缓存固化成所有访客看到的规范地址
      expect(src, `${page} 仍在用 useRequestURL 拼 SEO 地址`).not.toContain('useRequestURL')
      expect(src, `${page} 自己发了一条 canonical`).not.toContain(`rel: 'canonical'`)
    }
  })

  it('语言真相只有 URL 前缀：不接受 Accept-Language 重定向', () => {
    // detectBrowserLanguage(redirectOn: root) 会让 Googlebot（Accept-Language: en）
    // 在 GET / 上跳到 /en，中文首页与它的自指 canonical 就对不上了。
    const config = readFileSync(resolve(ROOT, 'nuxt.config.ts'), 'utf-8')
    // 只断言"配置项不存在"，不断言源码里没这个单词——上面那段口径注释本身就写着
    // redirectOn，用 toContain 会把解释性的话当成配置。
    expect(config).toContain('detectBrowserLanguage: false')
    expect(config).not.toMatch(/^\s*redirectOn\s*:/m)

    // 兜底中间件同口径：裸 `/` 是默认语言首页（也是 x-default），不改写。
    const middleware = readFileSync(
      resolve(ROOT, 'middleware/locale-prefix.global.client.ts'), 'utf-8'
    )
    expect(middleware).toContain(`to.path === '/'`)

    // 页脚切换器必须和顶栏一样换 URL，只 setLocale 会让内容与地址栏的语言互相判逆。
    const footer = readFileSync(resolve(ROOT, 'components/AppFooter.vue'), 'utf-8')
    expect(footer).toContain('applyLocalePrefix(route.fullPath')
  })

  it('useSeo 解响应式入参必须认原型链上的 value getter', () => {
    // Vue 3.5 的 computed() 是 class 实例，value 在原型上。hasOwnProperty 看不到它，
    // 于是把整个 ComputedRef 当字符串返回 → applyLocalePrefix 在 .startsWith 上抛
    // TypeError，跑在 useHead 求值路径上 = 整页 500（实测线上 /独立页 口）。
    const src = readFileSync(resolve(ROOT, 'composables/useSeo.ts'), 'utf-8')
    expect(src).toMatch(/'value' in asObj/)
    expect(src).not.toMatch(/hasOwnProperty\.call\(\s*asObj/)
  })

  it('路径归属判定一律先剥语言前缀（后台外壳不能只认裸 /admin）', () => {
    // 后台是可带前缀访问的（/en/admin/...）：admin-menu 的键、主题视觉排除名单、
    // 侧栏高亮比的都是默认语言形态。谁直接用 raw route.path 做归属判定，
    // 英文界面下就表现为面包屑退化成 URL 末段、菜单不高亮。
    for (const file of ['components/admin/AdminHeader.vue', 'components/admin/AdminSidebar.vue']) {
      const src = readFileSync(resolve(ROOT, file), 'utf-8')
      expect(src, `${file} 没走共享的剥前缀 helper`).toContain('stripLocalePathPrefix(')
      // 各写一套正则 = 下一轮加语言时漏改一处；口径唯一清单在 lib/rosetta-themes.ts
      expect(src, `${file} 自己拼了语言前缀正则`).not.toContain('en|ja|zh_Hant')
    }
    expect(readFileSync(resolve(ROOT, 'components/admin/AdminHeader.vue'), 'utf-8'))
      .not.toMatch(/findMenu(?:Item|Group)\(route\.path\)/)

    const lib = readFileSync(resolve(ROOT, 'lib/rosetta-themes.ts'), 'utf-8')
    expect(lib).toContain('export function isThemeVisualExcluded')
    expect(lib).toContain('stripLocalePathPrefix(path)')
  })

  it('全仓不再出现第二份语言前缀清单（唯一真源 lib/rosetta-themes）', () => {
    // 历史形态：`/^\/(?:en|ja|zh_Hant)(?=\/|$)/` 与 `['/en', '/ja', '/zh_Hant']`
    // 在 4 个中间件、2 个插件、nuxt.config、3 个 Nitro 文件里各写一份。
    // 加一种语言时漏改任一处都是静默失效，且没有任何运行时错误可查。
    const scanDirs = ['middleware', 'plugins', 'composables', 'server', 'components', 'lib']
    const offenders: string[] = []
    const walk = (dir: string): void => {
      for (const entry of readdirSync(resolve(ROOT, dir), { withFileTypes: true })) {
        const rel = `${dir}/${entry.name}`
        if (entry.isDirectory()) {
          walk(rel)
          continue
        }
        if (!/\.(ts|vue)$/.test(entry.name)) continue
        const src = readFileSync(resolve(ROOT, rel), 'utf-8')
        if (/en\|ja\|zh_Hant/.test(src) || /'\/en',\s*'\/ja'/.test(src)) offenders.push(rel)
      }
    }
    for (const dir of scanDirs) walk(dir)
    const config = readFileSync(resolve(ROOT, 'nuxt.config.ts'), 'utf-8')
    if (/'\/en',\s*'\/ja'/.test(config)) offenders.push('nuxt.config.ts')
    expect(offenders, `这些文件自己拼了语言前缀清单：${offenders.join(', ')}`).toEqual([])
  })
})

describe('<html lang> 只有一个 BCP-47 口径（SEO 报告 P1-2）', () => {
  it('映射值全部是 BCP-47：不带下划线，也不退回裸 locale code', () => {
    for (const [code, lang] of Object.entries(HREFLANG_MAP)) {
      expect(lang, `HREFLANG_MAP.${code} 不能带下划线`).not.toContain('_')
      // BCP-47：语言子 tag 2–3 位小写，其后接地区（2 位大写）或文字（4 位首字母大写），
      // 可连续挂多个（zh-Hant / zh-Hant-TW 形态都算合法）。
      expect(lang, `HREFLANG_MAP.${code} 形态`).toMatch(/^[a-z]{2,3}(-[A-Z]{2}|-[A-Z][a-z]{3})*$/)
    }
    expect(HREFLANG_MAP[DEFAULT_LOCALE_CODE]).toBe('zh-CN')
    expect(HREFLANG_MAP.zh_Hant).toBe('zh-Hant')
  })

  it('三处写 html lang 的地方全部查同一张表（app.vue 全局头 / useSeo 页级头 / nuxt.config 兜底）', () => {
    const app = readFileSync(resolve(ROOT, 'app.vue'), 'utf-8')
    const seo = readFileSync(resolve(ROOT, 'composables/useSeo.ts'), 'utf-8')
    const config = readFileSync(resolve(ROOT, 'nuxt.config.ts'), 'utf-8')
    // app.vue 曾直接吐 locale.value，于是没调 useSeo 的口（error.vue / oobe / SPA 空壳）
    // 输出 lang="zh_Hant"：下划线形态被解析器降级，还和同页 hreflang="zh-Hant" 自相矛盾。
    expect(app).toMatch(/lang: \(\) => HREFLANG_MAP\[locale\.value\]/)
    expect(app).not.toMatch(/lang: \(\) => locale\.value/)
    expect(seo).toMatch(/const htmlLang = HREFLANG_MAP\[locale\.value\]/)
    expect(seo).toMatch(/htmlAttrs: \{ lang: htmlLang \}/)
    expect(config).toContain(`'lang': '${HREFLANG_MAP[DEFAULT_LOCALE_CODE]}'`)
  })
})
