/**
 * 关于页四个分区的 SSR 直出（批次 #129）。
 *
 * /about 的回退模式此前整块包在 `ClientOnly` + reka `Tabs` 里：reka 的 TabsRoot 在 SSR
 * 产物里渲染成空注释节点，所以 `#fallback` 手工复刻了「TabsList + 默认 bio 面板」。线上
 * 实测爬虫读到的 HTML 里只有一条假 `role="tablist"` 和 bio 三段正文——「技能 / 联系方式 /
 * 订阅」三个分区（包括联系方式那批真实外链）对抓取器根本不存在，也无法深链。
 * 这批守卫钉住四件事：
 *   ① 分区正文必须在 SSR 直出的模板里，而不是任何客户端专属容器内；
 *   ② 导航是真实 `<a href="#id">`，id 与 `aboutSections` 集合相等（漏一个 = 点了不跳）；
 *   ③ 订阅区两个出口是 `<a href="/rss.xml">` / `<a href="/sitemap.xml">`，不是
 *      `Button @click`（点击才跳转的链接爬虫看不见）；
 *   ④ 分区文案键四语齐全——导航项由 `aboutSections` 驱动，缺一个 locale 就渲染裸 key。
 */

import { readFileSync } from 'node:fs'
import { resolve } from 'node:path'
import { describe, expect, it } from 'vitest'

const ROOT = resolve(__dirname, '..', '..')
const src = readFileSync(resolve(ROOT, 'pages/about.vue'), 'utf-8').replace(/\r\n/g, '\n')
const LOCALES = ['zh', 'en', 'ja', 'zh_Hant'] as const
const localeOf = (code: string) =>
  JSON.parse(readFileSync(resolve(ROOT, `i18n/locales/${code}.json`), 'utf-8')) as Record<
    string,
    Record<string, unknown>
  >

const SECTIONS = ['bio', 'skills', 'contact', 'rss'] as const

// 只在 <template> 段里断言：SSR 直出的证据就是 markup 本身，脚本段说什么都没用
const template = src.slice(0, src.indexOf('</template>'))

describe('关于页分区：SSR 直出', () => {
  it('整块不再包在 ClientOnly 里，也不再有 reka Tabs 与手工复刻的假 tablist', () => {
    expect(template).not.toContain('<ClientOnly')
    expect(template).not.toMatch(/<Tabs[\s/>]/)
    expect(template).not.toMatch(/TabsContent|TabsTrigger|TabsList/)
    expect(template).not.toContain('role="tablist"')
    expect(template).not.toContain('<template #fallback>')
    expect(src).not.toMatch(/from '~~\/components\/ui\/tabs'/)
  })

  it('四个分区各自是带 id 的 <section>，并带 scroll-mt 让锚点落位不被吸顶导航盖住', () => {
    for (const id of SECTIONS) {
      expect(
        template,
        `缺少 <section id="${id}">`
      ).toMatch(new RegExp(`<section\\s+id="${id}"\\s+class="scroll-mt-\\d+`))
    }
    // 每个分区一条 h2：文档大纲里四个分区都是真标题，爬虫按标题而非按 tab 标签理解结构
    const h2Count = (template.match(/<h2\b/g) ?? []).length
    expect(h2Count).toBeGreaterThanOrEqual(SECTIONS.length)
  })

  it('导航是真实 <a href="#id">，且条目集合与 section 的 id 集合相等', () => {
    expect(template).toContain('v-for="section in aboutSections"')
    expect(template).toContain(':href="`#${section.id}`"')
    const ids = [...src.matchAll(/\{ id: '(\w+)', labelKey: 'about\.\w+'/g)].map(m => m[1] ?? '')
    expect(ids.sort()).toEqual([...SECTIONS].sort())
    for (const id of SECTIONS) {
      expect(template, `分区 ${id} 没有对应的 <section id>`).toContain(`id="${id}"`)
    }
  })

  it('每个分区都在 SSR markup 里带出自己的正文，而不是只有默认那一个', () => {
    for (const key of ['about.bioP1', 'about.bioP2', 'about.bioP3', 'about.motto']) {
      expect(template, `bio 正文缺 ${key}`).toContain(`t('${key}')`)
    }
    expect(template).toMatch(/t\('about\.techStackDesc'\)/)
    expect(template).toContain('v-for="contact in contacts"')
    expect(template).toMatch(/t\('about\.rssFeed'\)/)
    expect(template).toMatch(/t\('about\.sitemap'\)/)
    expect(template).toMatch(/t\('about\.rssHint'\)/)
  })

  it('订阅区两个出口是爬虫读得到的 <a href>，不再依赖点击才跳转', () => {
    expect(template).toContain('href="/rss.xml"')
    expect(template).toContain('href="/sitemap.xml"')
    expect(template).not.toMatch(/@click="navigateTo\('\/rss\.xml'/)
    expect(template).not.toMatch(/@click="navigateTo\('\/sitemap\.xml'/)
  })

  it('分区文案键在四语 locale 里都存在（导航项按 labelKey 取值，缺键就渲染裸 key）', () => {
    const labelKeys = [...src.matchAll(/labelKey: '(about\.\w+)'/g)].map(m => m[1] ?? '')
    expect(labelKeys).toHaveLength(SECTIONS.length)
    for (const code of LOCALES) {
      const about = localeOf(code).about as Record<string, unknown>
      for (const key of labelKeys) {
        const leaf = key.split('.')[1]
        expect(about[leaf], `${code} 缺少 ${key}`).toBeTruthy()
      }
    }
  })
})
