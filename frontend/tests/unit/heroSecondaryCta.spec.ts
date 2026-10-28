/**
 * 切片 #27：首页轮播「次按钮」两端接通（`cta_secondary_text` / `cta_secondary_url`）。
 *
 * 这两列早在 `hero_slides` 里、`HeroSlide*` schema 三处都声明、匿名口 `GET /api/hero/slides`
 * 也把它们投给每个访客，但后台没有输入口、首页把第二个按钮硬编码成「查看全部 → /posts」。
 * 本文件钉的是"接通"这件事的四个必要条件，缺一即回到"配了不生效"：
 *   ① `safeHeroHref` 把伪协议挡在 href 之前（写入口不止后台表单一个：导入 ZIP 直接写 ORM）；
 *   ② `pages/index.vue` 的类型里有这两项，且第二个按钮真的读它们；
 *   ③ 后台表单能填、编辑时能回填（不回填＝每次 PUT 把已配置的次按钮抹成空）、能提交；
 *   ④ 留空必须回落成今天的观感，而不是多出一个空白按钮。
 *
 * 断言读源文本而不是跑组件：这些是"接线"口径，组件级 mock 反而测不出硬编码被留在原地。
 */
import { describe, expect, it } from 'vitest'
import { readFileSync } from 'node:fs'
import { resolve } from 'node:path'
import { safeHeroHref } from '../../lib/hero-cta'

const cwd = process.cwd()
const page = readFileSync(resolve(cwd, 'pages/index.vue'), 'utf8')
const admin = readFileSync(resolve(cwd, 'pages/admin/content/hero.vue'), 'utf8')

/** hero 文案段：从两个 CTA 所在的容器到该容器闭合（用次按钮那一条定位）。 */
const ctaBlock = page.slice(
  page.indexOf('<div class="mt-7 sm:mt-8 flex flex-wrap items-center gap-3">'),
  page.indexOf('data-editorial-section="pinned"')
)

describe('safeHeroHref：轮播 href 的唯一闸门', () => {
  it('站内路径原样放行（这两个框填的就是站内路径，语言前缀由 localeHref 补）', () => {
    expect(safeHeroHref('/series/python', '/posts')).toBe('/series/python')
    expect(safeHeroHref('/posts/hello?tab=1#top', '/posts')).toBe('/posts/hello?tab=1#top')
  })

  it('外链放行（后台配置的按钮完全可能跳站外）', () => {
    expect(safeHeroHref('https://example.com/a', '/posts')).toBe('https://example.com/a')
  })

  it('伪协议一律回落到缺省，绝不成为 <a href>', () => {
    for (const bad of [
      'javascript:alert(document.cookie)',
      '  javascript:alert(1)',
      'JaVaScRiPt:alert(1)',
      'data:text/html,<script>alert(1)</script>',
      'vbscript:msgbox(1)',
      'file:///etc/passwd',
      // 浏览器解析 URL 时会剥掉 \t \n \r 与空格：这三条点击时就是可执行协议。
      'javas\tcript:alert(1)',
      'java\nscript:alert(1)',
      'j a v a s c r i p t:alert(1)'
    ]) {
      expect(safeHeroHref(bad, '/posts'), bad).toBe('/posts')
    }
  })

  it('实体写法不需要闸门（Vue 转义 &，浏览器永远解不出协议）', () => {
    // `&colon;` 只有在属性值被 HTML 解析器解码后才是 `:`，而 SSR/`setAttribute`
    // 都会把 `&` 写成 `&amp;`，落地就是普通的相对路径。把它当伪协议拒掉是错的口径，
    // 会连带误伤运营者填写的合法链接里出现的 `&`（查询串 `?a=1&b=2`）。
    expect(safeHeroHref('JaVaScRiPt&colon;alert(1)', '/posts')).toBe('JaVaScRiPt&colon;alert(1)')
    expect(safeHeroHref('/posts?a=1&b=2', '/fallback')).toBe('/posts?a=1&b=2')
  })

  it('空值（null / undefined / 空串 / 纯空格）回落缺省 —— 首页据此保持历史观感', () => {
    expect(safeHeroHref('', '/posts')).toBe('/posts')
    expect(safeHeroHref('   ', '/posts')).toBe('/posts')
    expect(safeHeroHref(null, '/posts')).toBe('/posts')
    expect(safeHeroHref(undefined, '/posts')).toBe('/posts')
  })
})

describe('首页消费侧', () => {
  it('HeroSlideApi 里带着这两项——接口没声明就等于读不到', () => {
    expect(page).toMatch(/cta_secondary_text\?:\s*string \| Record<string, string> \| null/)
    expect(page).toMatch(/cta_secondary_url\?:\s*string \| null/)
  })

  it('两个按钮的 href 都过闸门（只守次按钮＝主按钮仍是同一条注入面）', () => {
    expect(page).toMatch(/const heroCtaUrl = computed\(\(\) => safeHeroHref\(heroSlide\.value\?\.cta_url, _heroCtaUrl\.value\)\)/)
    expect(page).toMatch(/const heroSecondaryCtaUrl = computed\(\(\) => safeHeroHref\(heroSlide\.value\?\.cta_secondary_url, '\/posts'\)\)/)
    expect(page).toMatch(/import \{ safeHeroHref \} from '~~\/lib\/hero-cta'/)
  })

  it('次按钮文案走 pickSlideText（这一列和 title/cta_text 同族，存的是多语言 JSON）', () => {
    expect(page).toMatch(/pickSlideText\(heroSlide\.value\?\.cta_secondary_text\)/)
  })

  it('硬编码的 /posts 与 t(\'home.viewAll\') 已改成缺省值，不再是模板里的常量', () => {
    expect(ctaBlock).not.toMatch(/localeHref\('\/posts'\)/)
    expect(ctaBlock).toMatch(/:to="localeHref\(heroSecondaryCtaUrl\)"/)
    expect(ctaBlock).toMatch(/\{\{ heroSecondaryCtaText \}\}/)
  })

  it('缺省回落仍成立：幻灯片没配时用 t(\'home.viewAll\') 与 /posts', () => {
    expect(page).toMatch(/cta_secondary_text\)[^)]*\|\|\s*t\('home\.viewAll'\)/)
    expect(page).toMatch(/safeHeroHref\(heroSlide\.value\?\.cta_secondary_url, '\/posts'\)/)
  })

  it('布局契约没被这次改动破坏：两个 CTA 的点击高度仍是 2 × min-h-11', () => {
    const hits = ctaBlock.match(/min-h-11 items-center justify-center/g) ?? []
    expect(hits.length).toBe(2)
  })
})

describe('后台写入口', () => {
  it('表单状态里两项都在，且类型与其它项一起声明', () => {
    expect(admin).toMatch(/cta_secondary_text: I18nDict/)
    expect(admin).toMatch(/cta_secondary_url: string/)
  })

  it('新建与编辑两条路径都填值：不回填就会把已配置的次按钮抹成空', () => {
    expect(admin).toMatch(/form\.cta_secondary_text = \{ \.\.\.EMPTY_I18N_DICT \}/)
    expect(admin).toMatch(/form\.cta_secondary_url = ''/)
    expect(admin).toMatch(/form\.cta_secondary_text = toDict\(slide\.cta_secondary_text\)/)
    expect(admin).toMatch(/form\.cta_secondary_url = slide\.cta_secondary_url \?\? ''/)
  })

  it('提交时文案走 fromDict（四语全空必须提交 null），链接走 trim() || null', () => {
    expect(admin).toMatch(/cta_secondary_text: fromDict\(form\.cta_secondary_text\)/)
    expect(admin).toMatch(/cta_secondary_url: form\.cta_secondary_url\.trim\(\) \|\| null/)
  })

  it('模板里两个控件都渲染出来（有真实 id，可被 e2e 与人工都找到）', () => {
    expect(admin).toMatch(/v-model="form\.cta_secondary_text"/)
    expect(admin).toMatch(/id="hero-form-secondary-cta"/)
    expect(admin).toMatch(/v-model="form\.cta_secondary_url"/)
  })
})
