/**
 * 曾经"只进库不进页面"的开关消费点契约。
 *
 * 表现过的 bug：后台设置页有输入框/开关，保存后 GET /api/settings/<group> 里值是对的，
 * 前台却永远不读它——用户判定为"设置不生效"，而代码里既没有报错也没有兜底，
 * 只能靠 grep 全仓才发现。这里钉住每一项，防止再次退化成死字段：
 * - hero.bg_image / hero.bg_gradient → pages/index.vue 的 hero section 背景
 * - hero.enable                      → pages/index.vue 整段 hero 的 v-if
 * - footer.show_back_to_top          → layouts/default.vue 的回到顶部按钮
 * - footer.show_social_links         → components/AppFooter.vue 的 socialLinks 计算属性
 * - footer.police_icp_number         → components/AppFooter.vue 两套页脚的备案行
 * - features.enable_share_buttons    → pages/posts/[slug].vue 的分享条
 * - enable_bing_wallpaper            → pages/login.vue + pages/register.vue 的壁纸拉取与切壁纸控件
 */

import { describe, it, expect } from 'vitest'
import { readFileSync } from 'node:fs'
import { resolve } from 'node:path'

const homePage = readFileSync(resolve(process.cwd(), 'pages/index.vue'), 'utf8')
const loginPage = readFileSync(resolve(process.cwd(), 'pages/login.vue'), 'utf8')
const registerPage = readFileSync(resolve(process.cwd(), 'pages/register.vue'), 'utf8')
const defaultLayout = readFileSync(resolve(process.cwd(), 'layouts/default.vue'), 'utf8')
const postPage = readFileSync(resolve(process.cwd(), 'pages/posts/[slug].vue'), 'utf8')
const footerComp = readFileSync(resolve(process.cwd(), 'components/AppFooter.vue'), 'utf8')

describe('站点设置开关必须有真实消费点', () => {
  it('首页 hero 背景读取 hero.bg_image 与 hero.bg_gradient', () => {
    expect(homePage).toContain('site.hero.value.bg_image')
    expect(homePage).toContain('site.hero.value.bg_gradient')
    expect(homePage, '自配背景必须能压过轮播图，否则配了等于没配')
      .toMatch(/heroBgImage\.value\s*\|\|\s*heroSlideMedia\.value/)
    expect(homePage, '写进 style 的 URL 必须先过白名单正则').toMatch(/HERO_BG_URL_RE\.test/)
  })

  it('首页横幅内容源是 /hero/slides，不再请求 Bing 每日壁纸', () => {
    expect(homePage).toContain('useAPI<HeroSlideApi[]>(\'/hero/slides\'')
    expect(homePage, '首页引入 useBingWallpaper 会把首屏绑到站外图片（壁纸只服务登录/注册页）')
      .not.toContain('useBingWallpaper')
    expect(homePage, '轮播必须有真实切换面，否则只有第一张能用')
      .toMatch(/function selectHeroSlide/)
  })

  it('登录/注册页尊重 enable_bing_wallpaper 开关', () => {
    for (const [name, src] of [['login.vue', loginPage], ['register.vue', registerPage]] as const) {
      expect(src, `${name} 必须从 /api/config 的 publicConfig 读这一项`)
        .toContain('publicConfig?.enable_bing_wallpaper')
      expect(src, `${name} 关开关后不得再打壁纸请求（否则站外图片仍然出现在登录页）`)
        .toMatch(/!isMinimalAuth\.value && bingWallpaperEnabled\.value/)
      expect(src, `${name} 的切壁纸控件要一起隐藏，不留没有内容的可点外壳`)
        .toMatch(/v-if="bingWallpaperEnabled"[\s\S]{0,200}pointer-events-auto/)
    }
  })

  it('页脚「回到顶部」读取 footer.show_back_to_top', () => {
    expect(defaultLayout).toContain('site.footer.value.show_back_to_top')
    expect(defaultLayout).toMatch(/aria-label="t\('a11y\.backToTop'\)"/)
  })

  it('文章分享条读取 features.enable_share_buttons', () => {
    expect(postPage).toContain('site.features.value.enable_share_buttons')
    expect(postPage, '分享地址必须走 canonical 同款前缀算法，不能拼 window.location')
      .toContain('applyLocalePrefix(seoPostPath.value')
    expect(postPage).toMatch(/rel="noopener noreferrer"/)
    expect(postPage, 'Clipboard API 在 http 下会 reject，必须有 textarea 兜底，否则按钮形同虚设')
      .toContain('document.execCommand')
  })

  it('首页「启用 Hero」读取 hero.enable', () => {
    expect(homePage).toContain('site.hero.value.enable !== false')
    expect(homePage, '关掉开关必须整段不渲染，而不是留个 visibility:hidden 的假开关')
      .toMatch(/<section\s+v-if="heroEnabled"/)
    expect(homePage, 'hero 不渲染时不该再请求每日壁纸').toContain('heroEnabled.value')
  })

  it('页脚社交链接读取 footer.show_social_links', () => {
    expect(footerComp).toContain('site.footer.value.show_social_links === false')
  })

  it('页脚渲染 footer.police_icp_number（公安备案号）', () => {
    expect(footerComp).toContain('f.police_icp_number')
    expect(footerComp, '两套页脚骨架都要显示备案号').toMatch(/siteConfig\.police_icp_number/)
  })
})

/**
 * 「一个行为只有一个开关」契约。
 *
 * 反例（都真实存在过，都不报错）：
 * - features.enable_comments 只管前台评论区、comments.enable 只管后端写口，
 *   于是关掉前者接口照写、关掉后者表单照渲染；
 * - seo.default_title 排在 `basic.subtitle || …` 之后，而 basic.subtitle 有写死的
 *   英文兜底、永远非空 → 后台那个"页面默认标题"输入框填了也永远不会被读到；
 * - footer.text 写成 `f.slogan || f.text` 的第一个候选的备胎，而 useSite 用同一条
 *   副标题同时播种 slogan 与 text → text 永远取不到值。
 */
describe('同一行为不得有两个开关', () => {
  const useSite = readFileSync(resolve(process.cwd(), 'composables/useSite.ts'), 'utf8')
  const settingsPage = readFileSync(resolve(process.cwd(), 'pages/admin/system/settings.vue'), 'utf8')

  it('评论区读取的是 comments.enable（后端写口闸门的同一项）', () => {
    expect(postPage).toContain('site.comments.value.enable')
    expect(postPage, 'features.enable_comments 是第二个开关，已删除').not.toContain('features.value.enable_comments')
    expect(useSite).toMatch(/enable: flag\('enable', true\)/)
  })

  it('features 组与后台设置页都不再有 enable_comments', () => {
    expect(useSite, 'useSite 的 features 投影不能再暴露 enable_comments').not.toContain('enable_comments:')
    expect(settingsPage).not.toContain('enable_comments')
  })

  it('seo.default_title 排在兜底链最前，填了就能改浏览器标题', () => {
    expect(useSite).toMatch(/seo\.value\.default_title \|\| basic\.value\.subtitle/)
    expect(useSite, '反过来的顺序等于永久遮蔽（basic.subtitle 有写死兜底）')
      .not.toMatch(/basic\.value\.subtitle \|\| seo\.value\.default_title/)
    // 光有优先级还不够：这一项只活在"本页无标题"分支里，那条分支曾被 nuxt.config 的
    // 构建期占位永久占掉。占位识别与壳页服务端补写的契约见 spaShellTitle.spec.ts。
    expect(readFileSync(resolve(process.cwd(), 'app.vue'), 'utf8'))
      .toContain('SPA_SHELL_TITLE_PLACEHOLDER')
  })

  it('footer.text 有独立渲染位，不再与 slogan 抢同一行', () => {
    expect(footerComp, '标语行只读 slogan').toMatch(/const footerSlogan = f\.slogan \|\| readStr/)
    expect(footerComp).toMatch(/const poweredByText = f\.text/)
    expect(footerComp, '两套页脚都要用上覆写文案').toMatch(/poweredByLine/)
    expect(useSite, 'text 的兜底必须是空串，否则内置四语文案永远被副标题顶掉')
      .toMatch(/text: '',/)
  })

  it('reading.posts_per_page 三处默认值同一口径（表单显示数 = 前台渲染数）', () => {
    // /settings/public 下发的是「后端默认值 + DB 存值」合并后的整组，所以后端默认值
    // 就是未保存过分组的站点实际渲染的每页条数；useSite 的兜底 9 只在接口失败时生效。
    // 两边一个 12 一个 9 时，后台显示的数与实际版式对不上，而设置页本地默认表再给第三个数。
    const backendDefaults = readFileSync(
      resolve(process.cwd(), '../backend/api/settings_groups.py'),
      'utf8'
    )
    const readingBlock = backendDefaults.split('def _default_reading')[1] ?? ''
    expect(readingBlock).toMatch(/"posts_per_page": 9,/)
    expect(useSite, 'useSite 的兜底必须与后端默认值一致').toMatch(/posts_per_page: pos\('posts_per_page', 9\)/)
    expect(settingsPage, '设置页本地默认表也必须同一数').toMatch(/reading: \{ posts_per_page: 9,/)
  })
})

/**
 * 设置页的字段名表与本地默认表，必须覆盖后端 _default_* 的每一把键。
 *
 * 表现过的 bug：features.enable_captcha 加了后端默认值、加了前台消费点，唯独没加设置页
 * 中文标签——`GROUP_LABELS[key] ?? key` 的兜底把"漏登记"变成一个静默的裸 snake_case
 * 字段名，谁都不会报错。同一张表漏登记键还会让"未保存过该分组"的站点在前端拿到
 * undefined，把确实是 false 的开关判成"没有值"，显示与真值不符。
 * 两边各漏一次都只是几行 diff，靠肉眼看设置页永远看不出来，所以按后端真源清点。
 */
describe('设置页字段清单必须覆盖后端每一把设置键', () => {
  const clean = (s: string) => s.replace(/\r\n/g, '\n')
  const backendSource = clean(
    readFileSync(resolve(process.cwd(), '../backend/api/settings_groups.py'), 'utf8')
  )
  const page = clean(readFileSync(resolve(process.cwd(), 'pages/admin/system/settings.vue'), 'utf8'))

  const groups: Record<string, string[]> = {}
  const defStarts = [...backendSource.matchAll(/^def /gm)].map(m => m.index)
  const pick = (matches: Iterable<RegExpExecArray>) =>
    [...matches].flatMap(m => (m[1] ? [m[1]] : []))
  for (const m of backendSource.matchAll(/^def _default_(\w+)\(\) -> dict:/gm)) {
    const name = m[1]
    if (!name) continue
    const end = defStarts.find(i => i > m.index) ?? backendSource.indexOf('_GROUP_DEFAULTS')
    const body = backendSource.slice(m.index, end)
    groups[name] = pick(body.matchAll(/^ {8}"([a-z_0-9]+)":/gm))
  }
  const backendKeys = new Set(Object.values(groups).flat())

  /** 有专用编辑器承载、不进通用 schema 的键（收款码图集、打赏名单）。 */
  const EDITOR_ONLY_KEYS = new Set(['methods', 'sponsors'])

  it('后端设置键清单非空（解析失效必须报错，不能静默通过）', () => {
    expect(Object.keys(groups).length, '_default_* 解析不到分组，守卫本身失效了').toBeGreaterThan(10)
    expect(backendKeys.size).toBeGreaterThan(70)
  })

  it('每把设置键都有中文标签，否则后台渲染成裸 snake_case 字段名', () => {
    const labelBlock = page.match(/ {2}const label = \{\n([\s\S]*?)\n {2}\}\[key\]/)
    const labelTable = labelBlock?.[1]
    if (!labelTable) throw new Error('settings.vue 字段名表结构已变，请同步本守卫的解析口径')
    const labels = new Set(pick(labelTable.matchAll(/\b([a-z_0-9]+): '/g)))
    const missing = [...backendKeys].filter(k => !labels.has(k) && !EDITOR_ONLY_KEYS.has(k))
    expect(missing, `这些键在设置页没有中文名：${missing.join(', ')}`).toEqual([])
    const orphans = [...labels].filter(k => !backendKeys.has(k))
    expect(orphans, `后端已不存在这些键，标签是改名后留下的死条目：${orphans.join(', ')}`).toEqual([])
  })

  it('设置页本地默认表与后端逐分组键集合相等', () => {
    const fn = page.match(/function getDefaultsFor[\s\S]*?\n}/)
    const fnSource = fn?.[0]
    if (!fnSource) throw new Error('getDefaultsFor 结构已变，请同步本守卫的解析口径')
    const table: Record<string, Set<string>> = {}
    for (const m of fnSource.matchAll(/^ {4}(\w+): \{(.*)\},?$/gm)) {
      const group = m[1]
      const inline = m[2]
      if (!group || !inline) continue
      table[group] = new Set(pick(inline.matchAll(/\b([a-z_0-9]+):/g)))
    }
    for (const [group, keys] of Object.entries(groups)) {
      const local = table[group]
      expect(local, `设置页默认表缺少 ${group} 分组`).toBeDefined()
      const holder = local as Set<string>
      const missing = keys.filter(k => !holder.has(k))
      const extra = [...holder].filter(k => !keys.includes(k))
      expect(missing, `${group} 漏了 ${missing.join(' / ')}：未保存过分组时前端读不到值，开关显示与真值不符`).toEqual([])
      expect(extra, `${group} 有后端不存在的 ${extra.join(' / ')}`).toEqual([])
    }
  })

  /**
   * 数值键的区间：输入框的 min/max 与后端 PATCH 闸门必须是同一组数。
   *
   * 表现过的口径：输入框写着 min:1 max:50，保存路径却把整组原样 PATCH 出去——浏览器不会
   * 替一次 fetch 做校验，于是填 500 会"保存成功"，再让五个列表页全部 422（列表接口的
   * page_size 上限是 200）。区间真源是 `backend/api/settings_groups.py::_NUMERIC_BOUNDS`，
   * 这里反向解析它而不是抄第二份清单（抄的那份会跟着一起漂移）。
   */
  it('数值设置键的区间：后端闸门与输入框 min/max 逐键相等', () => {
    const boundBlock = backendSource.match(/^_NUMERIC_BOUNDS: dict[^=]*= \{\n([\s\S]*?)\n\}/m)
    const boundBody = boundBlock?.[1]
    if (!boundBody) throw new Error('_NUMERIC_BOUNDS 结构已变，请同步本守卫的解析口径')
    const remote: Record<string, { min: number, max: number }> = {}
    for (const m of boundBody.matchAll(/"([a-z_]+\.[a-z_0-9]+)": \(([-0-9.]+), ([-0-9.]+)\)/g)) {
      const dotted = m[1]
      const lo = m[2]
      const hi = m[3]
      if (!dotted || !lo || !hi) continue
      const [, key] = dotted.split('.')
      if (!key) continue
      if (remote[key]) throw new Error(`${key} 在后端出现在两个分组，本守卫按扁平键名对账会判错`)
      remote[key] = { min: Number(lo), max: Number(hi) }
    }
    expect(Object.keys(remote).length, '_NUMERIC_BOUNDS 解析不出条目，守卫本身失效了').toBeGreaterThan(8)

    // `}>` 而不是 `}`：注解是 Record<string, { min?: number, ... }>，漏掉泛型的闭合尖括号
    // 会让这块永远匹配不上，守卫就变成"结构已变"的假红（实测踩过一次）。
    const metaBlock = page.match(/const meta: Record<string, \{[^}]*\}> = \{([\s\S]*?)\n {4}\}/)
    const metaBody = metaBlock?.[1]
    if (!metaBody) throw new Error('settings.vue 数值区间表结构已变，请同步本守卫的解析口径')
    const local: Record<string, { min: number, max: number }> = {}
    for (const m of metaBody.matchAll(/([a-z_0-9]+): \{([^}]*)\}/g)) {
      const name = m[1]
      const entry = m[2]
      if (!name || !entry) continue
      local[name] = {
        min: Number(entry.match(/min: ([-0-9.]+)/)?.[1]),
        max: Number(entry.match(/max: ([-0-9.]+)/)?.[1])
      }
    }

    expect(Object.keys(local).sort(), '数值区间表必须等于后端数值键清单').toEqual(Object.keys(remote).sort())
    for (const [key, bounds] of Object.entries(remote)) {
      expect(local[key]?.min, `${key} 的 min 与后端闸门不一致`).toBe(bounds.min)
      expect(local[key]?.max, `${key} 的 max 与后端闸门不一致`).toBe(bounds.max)
    }
  })
})
